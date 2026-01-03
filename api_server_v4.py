"""
Gemini Reverse API v4.2
功能: Provider优先 + Cookie备用 + 智能重试 + 动态延迟 + 去水印 + TTS语音 + PDF分析 + UI设计理解
关键词: gemini, api, provider, cookie, hybrid, retry, rate-limit, watermark-removal, tts, pdf, ui-design
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from gemini_webapi import GeminiClient
import os
import asyncio
import re
import hashlib
import sqlite3
import random
import time
import io
import wave
import base64 as b64
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid
from contextlib import asynccontextmanager
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 配置 ============
WEB_DIR = Path(__file__).parent / "web"
DB_PATH = Path(__file__).parent / "task_state.db"

# 并发配置
MAX_CONCURRENCY = 2  # 最大并发数
REQUEST_SEMAPHORE = None  # 全局信号量，启动时初始化

# 智能延迟配置
RATE_LIMIT_CONFIG = {
    "base_delay": 2.0,        # 基础延迟(秒)
    "max_delay": 60.0,        # 最大延迟(秒)
    "jitter_range": 1.0,      # 抖动范围(秒)
    "backoff_multiplier": 2,  # 退避倍数
    "rpm_limit": 60,          # 每分钟请求限制
}

# 重试配置
RETRY_CONFIG = {
    "max_attempts": 5,        # 最大重试次数
    "min_wait": 2,            # 最小等待(秒)
    "max_wait": 60,           # 最大等待(秒)
}

# Cookie持久化与告警
try:
    from cookie_persistence import cookie_persistence, bark_notifier
    COOKIE_PERSISTENCE_ENABLED = True
except ImportError:
    COOKIE_PERSISTENCE_ENABLED = False
    cookie_persistence = None
    bark_notifier = None
    logger.warning("Cookie持久化模块未加载")

# 初始化Cookie: 优先使用持久化的Cookie，其次使用环境变量
_persisted_cookies = cookie_persistence.load_cookies() if COOKIE_PERSISTENCE_ENABLED else None
cookie_store = _persisted_cookies or {
    "__Secure-1PSID": os.getenv("SECURE_1PSID"),
    "__Secure-1PSIDCC": os.getenv("SECURE_1PSIDCC"),
    "__Secure-1PSIDTS": os.getenv("SECURE_1PSIDTS")
}
if _persisted_cookies:
    logger.info("使用持久化Cookie启动")
else:
    logger.info("使用环境变量Cookie启动")

# Google AI API Key (用于TTS等官方API功能)
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")

# ============ Provider模式配置 (优先级更高) ============
PROVIDER_CONFIG = {
    "enabled": os.getenv("ENABLE_PROVIDER_MODE", "true").lower() == "true",
    "base_url": os.getenv("PROVIDER_BASE_URL", "http://82.29.54.80:13001/proxy/gemini-hk/v1beta"),
    "auth_token": os.getenv("PROVIDER_AUTH_TOKEN", "zxc6545398"),
    "default_model": os.getenv("PROVIDER_DEFAULT_MODEL", "gemini-3-flash-preview"),
    "timeout": int(os.getenv("PROVIDER_TIMEOUT", "10")),  # 快速失败，fallback到Cookie
}

# Provider模型映射
PROVIDER_MODEL_MAP = {
    # 文本模型
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gemini-3.0-pro": "gemini-3-pro-preview",
    "gemini-3-flash": "gemini-3-flash-preview",
    # 图片模型
    "gemini-2.5-flash-image": "gemini-2.5-flash-image",
    "gemini-3-pro-image-preview": "gemini-3-pro-image-preview",
}

# 图片模型列表 - 用于检测请求是否需要图片生成
IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3-pro-image-preview",
    "gemini-3-pro-image-preview-2k",
    "gemini-3-pro-image-preview-4k",
]

R2_CONFIG = {
    "endpoint": "https://79e5a95d36e6e4084ae15fcc4220b127.r2.cloudflarestorage.com",
    "access_key": "35f9ace41767c9ba5d4c60d804d0063a",
    "secret_key": "cfff46ae5a409785f5dd87e5fe47d95a3d5682c661887b91c375b4a23edda8cb",
    "bucket": "gemini",
    "public_url": "https://pub-87cd59069cf0444aad048f7bddec99af.r2.dev",
    "folder": "gemini-images"
}

gemini_client = None

# ============ 水印去除器 ============
watermark_remover = None

# ============ TTS 配置 ============
TTS_CONFIG = {
    "api_base": "https://generativelanguage.googleapis.com/v1beta",
    "models": {
        "tts-1": "gemini-2.5-flash-preview-tts",
        "tts-1-hd": "gemini-2.5-pro-preview-tts"
    },
    # OpenAI voice -> Gemini voice style mapping
    "voice_styles": {
        "alloy": "neutral, clear, professional",
        "echo": "warm, friendly, conversational",
        "fable": "expressive, storytelling, dramatic",
        "onyx": "deep, authoritative, commanding",
        "nova": "bright, energetic, youthful",
        "shimmer": "soft, gentle, soothing"
    },
    # Gemini prebuilt voices
    "prebuilt_voices": ["Kore", "Charon", "Kore", "Fenrir", "Aoede", "Puck"]
}

# ============ 自定义异常 ============
class GeminiAPIError(Exception):
    """Gemini API基础异常"""
    pass

class RateLimitError(GeminiAPIError):
    """429限流错误 - 可重试"""
    pass

class ServerError(GeminiAPIError):
    """5xx服务器错误 - 可重试"""
    pass

class ClientError(GeminiAPIError):
    """4xx客户端错误 - 不重试"""
    pass

# ============ 智能速率控制器 ============
class SmartRateLimiter:
    """带抖动的智能速率限制器"""

    def __init__(self, rpm_limit: int = 60):
        self.rpm_limit = rpm_limit
        self.request_times: List[float] = []
        self.consecutive_429s = 0
        self.current_delay = RATE_LIMIT_CONFIG["base_delay"]
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """获取请求许可，返回实际等待时间"""
        async with self._lock:
            now = time.time()
            self.request_times = [t for t in self.request_times if now - t < 60]
            if len(self.request_times) >= self.rpm_limit:
                oldest = self.request_times[0]
                wait_time = 60 - (now - oldest) + self._add_jitter()
                if wait_time > 0:
                    logger.info(f"RPM限制触发，等待 {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
            delay = self.current_delay + self._add_jitter()
            if delay > 0:
                await asyncio.sleep(delay)
            self.request_times.append(time.time())
            return delay

    def _add_jitter(self) -> float:
        return random.uniform(0, RATE_LIMIT_CONFIG["jitter_range"])

    def report_success(self):
        self.consecutive_429s = 0
        self.current_delay = max(
            RATE_LIMIT_CONFIG["base_delay"],
            self.current_delay * 0.9
        )

    def report_rate_limit(self):
        self.consecutive_429s += 1
        self.current_delay = min(
            RATE_LIMIT_CONFIG["max_delay"],
            self.current_delay * RATE_LIMIT_CONFIG["backoff_multiplier"]
        )
        logger.warning(f"429错误，延迟调整为 {self.current_delay:.1f}s")

    def get_stats(self) -> dict:
        return {
            "current_delay": round(self.current_delay, 2),
            "requests_last_minute": len(self.request_times),
            "consecutive_429s": self.consecutive_429s,
            "rpm_limit": self.rpm_limit
        }

rate_limiter = SmartRateLimiter(rpm_limit=RATE_LIMIT_CONFIG["rpm_limit"])

# ============ 断点续传：SQLite任务状态管理 ============
class TaskStateManager:
    """SQLite任务状态管理器"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        conn.commit()
        conn.close()

    def create_task(self, task_id: str, task_type: str, input_data: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO tasks (task_id, task_type, input_data) VALUES (?, ?, ?)",
                (task_id, task_type, input_data)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_task(self, task_id: str, status: str, output_data: str = None, error: str = None):
        conn = sqlite3.connect(self.db_path)
        if status == "completed":
            conn.execute(
                "UPDATE tasks SET status = ?, output_data = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (status, output_data, task_id)
            )
        elif status == "failed":
            conn.execute(
                "UPDATE tasks SET status = ?, error_message = ?, retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (status, error, task_id)
            )
        else:
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                (status, task_id)
            )
        conn.commit()
        conn.close()

    def get_pending_tasks(self, task_type: str = None, limit: int = 100) -> List[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if task_type:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('pending', 'processing') AND task_type = ? ORDER BY created_at LIMIT ?",
                (task_type, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('pending', 'processing') ORDER BY created_at LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return {
            "pending": stats.get("pending", 0),
            "processing": stats.get("processing", 0),
            "completed": stats.get("completed", 0),
            "failed": stats.get("failed", 0),
            "total": sum(stats.values())
        }

    def cleanup_old_tasks(self, days: int = 7):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM tasks WHERE status = 'completed' AND updated_at < datetime('now', ?)",
            (f'-{days} days',)
        )
        deleted = conn.total_changes
        conn.commit()
        conn.close()
        return deleted

task_manager = TaskStateManager(DB_PATH)

# ============ TTS 工具函数 ============
def convert_pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """将PCM音频转换为WAV格式"""
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return output.getvalue()

async def call_tts_api(text: str, model: str = "tts-1", voice: str = "alloy") -> bytes:
    """调用Gemini TTS API"""
    if not GOOGLE_AI_API_KEY:
        raise HTTPException(status_code=503, detail="未配置GOOGLE_AI_API_KEY，TTS功能不可用")

    gemini_model = TTS_CONFIG["models"].get(model, TTS_CONFIG["models"]["tts-1"])

    # 构建请求
    url = f"{TTS_CONFIG['api_base']}/models/{gemini_model}:generateContent?key={GOOGLE_AI_API_KEY}"

    # 使用 "Read aloud:" 前缀来强制TTS输出
    tts_prompt = f"Read aloud: {text}"

    payload = {
        "contents": [{"parts": [{"text": tts_prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"]
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            raise HTTPException(status_code=response.status_code, detail=f"TTS API错误: {error_msg}")

        data = response.json()

        # 提取音频数据
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "inlineData" in part:
                        inline_data = part["inlineData"]
                        audio_base64 = inline_data["data"]
                        mime_type = inline_data.get("mimeType", "audio/L16")

                        # 解码base64音频
                        pcm_data = b64.b64decode(audio_base64)

                        # 转换为WAV格式
                        wav_data = convert_pcm_to_wav(pcm_data)
                        return wav_data

        raise HTTPException(status_code=500, detail="TTS API未返回音频数据")

# ============ 工具函数 ============
def create_image_prompt(user_prompt: str) -> str:
    return f"""Generate an actual image (not a description).
Create a visual representation of: {user_prompt}

IMPORTANT: You must generate an image, not text. Output only the image."""


def generate_image_filename(prompt: str, index: int = 0) -> str:
    prompt_clean = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', prompt)
    words = prompt_clean.split()[:5]
    keywords = '_'.join(words)[:50]
    keywords = re.sub(r'_+', '_', keywords).strip('_')
    if not keywords:
        keywords = "image"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    short_hash = hashlib.md5(f"{prompt}{timestamp}{index}".encode()).hexdigest()[:6]
    return f"{timestamp}_{keywords}_{short_hash}.png"


async def upload_to_r2(image_bytes: bytes, filename: str) -> str:
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        's3',
        endpoint_url=R2_CONFIG["endpoint"],
        aws_access_key_id=R2_CONFIG["access_key"],
        aws_secret_access_key=R2_CONFIG["secret_key"],
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

    key = f"{R2_CONFIG['folder']}/{filename}"
    s3.put_object(
        Bucket=R2_CONFIG["bucket"],
        Key=key,
        Body=image_bytes,
        ContentType='image/png'
    )
    return f"{R2_CONFIG['public_url']}/{key}"


# ============ Provider API调用 ============
async def call_provider_api(prompt: str, model: str = None, image_mode: bool = False) -> dict:
    """调用Provider API (官方格式)"""
    if not PROVIDER_CONFIG["enabled"]:
        raise Exception("Provider模式未启用")

    model = model or PROVIDER_CONFIG["default_model"]
    provider_model = PROVIDER_MODEL_MAP.get(model, model)

    url = f"{PROVIDER_CONFIG['base_url']}/models/{provider_model}:generateContent"
    headers = {
        "Authorization": f"Bearer {PROVIDER_CONFIG['auth_token']}",
        "Content-Type": "application/json"
    }

    # 构建请求体
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    # 图片生成模式
    if image_mode:
        data["generationConfig"] = {"responseModalities": ["IMAGE", "TEXT"]}

    async with httpx.AsyncClient(timeout=PROVIDER_CONFIG["timeout"]) as client:
        response = await client.post(url, headers=headers, json=data)

        if response.status_code == 429:
            raise RateLimitError(f"Provider rate limit: {response.text}")
        elif response.status_code >= 500:
            raise ServerError(f"Provider server error: {response.text}")
        elif response.status_code != 200:
            raise ClientError(f"Provider error ({response.status_code}): {response.text}")

        return response.json()


# ============ 带重试的Gemini调用 (双模式) ============
@retry(
    retry=retry_if_exception_type((RateLimitError, ServerError)),
    wait=wait_exponential(
        multiplier=1,
        min=RETRY_CONFIG["min_wait"],
        max=RETRY_CONFIG["max_wait"]
    ),
    stop=stop_after_attempt(RETRY_CONFIG["max_attempts"]),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def call_gemini_with_retry(prompt: str, files: List[str] = None, model=None, image_mode: bool = False):
    """带智能重试的Gemini API调用 - Provider优先，Cookie备用"""
    global gemini_client, rate_limiter

    model_str = str(model) if model else "gemini-2.5-flash"

    # ========== 文本模型: Provider优先 ==========
    # 图片/视频模型只用Cookie，文本模型用Provider优先
    if PROVIDER_CONFIG["enabled"] and not files and not image_mode:
        try:
            logger.info(f"[Provider] 调用模型: {model_str}")
            result = await call_provider_api(prompt, model=model_str, image_mode=image_mode)

            # 解析Provider响应
            if "candidates" in result:
                candidates = result["candidates"]
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"]["parts"]
                    # 构造兼容的响应对象
                    class ProviderResponse:
                        def __init__(self, parts):
                            self.text = ""
                            self.images = []
                            for p in parts:
                                if "text" in p:
                                    self.text += p["text"]
                                if "inlineData" in p:
                                    self.images.append(p["inlineData"])
                    return ProviderResponse(parts)

            raise ClientError(f"Provider返回格式异常: {result}")

        except Exception as e:
            error_str = str(e).lower()
            # 429/500错误时fallback到Cookie模式
            if "429" in error_str or "500" in error_str or "503" in error_str:
                logger.warning(f"[Provider] 错误，尝试Cookie模式: {e}")
            else:
                # 其他错误也尝试fallback
                logger.warning(f"[Provider] 失败，fallback到Cookie: {e}")

    # ========== Cookie模式 (备用) ==========
    if not gemini_client:
        raise ClientError("Gemini客户端未初始化，且Provider模式不可用")

    async with REQUEST_SEMAPHORE:
        await rate_limiter.acquire()

        try:
            from gemini_webapi.constants import Model
            cookie_model = model or Model.G_2_5_FLASH

            logger.info(f"[Cookie] 调用模型: {cookie_model}")

            if files:
                response = await gemini_client.generate_content(prompt, files=files, model=cookie_model)
            else:
                response = await gemini_client.generate_content(prompt, model=cookie_model)

            rate_limiter.report_success()
            return response

        except Exception as e:
            error_str = str(e).lower()

            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                rate_limiter.report_rate_limit()
                raise RateLimitError(f"Rate limit: {e}")
            elif "500" in error_str or "503" in error_str or "server" in error_str:
                raise ServerError(f"Server error: {e}")
            else:
                raise ClientError(f"Client error: {e}")


# ============ Pydantic Models ============
class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.5-flash"

class GenerateResponse(BaseModel):
    text: str
    model: str

class ImageGenerateRequest(BaseModel):
    prompt: str
    count: int = 1
    response_type: str = "base64"
    image: Optional[str] = None

class ImageGenerateResponse(BaseModel):
    images: List[str]
    model: str = "gemini-2.5-flash"

class BatchImageRequest(BaseModel):
    prompts: List[str]
    response_type: str = "url"
    concurrency: int = 2

class BatchImageResponse(BaseModel):
    batch_id: str
    total: int
    status: str
    message: str

# TTS Models
class TTSRequest(BaseModel):
    model: str = "tts-1"
    input: str
    voice: str = "alloy"
    response_format: str = "wav"
    speed: float = 1.0

# PDF Analysis Models
class PDFAnalysisRequest(BaseModel):
    prompt: str = "Analyze this PDF document"
    detail_level: str = "medium"  # low, medium, high

class PDFAnalysisResponse(BaseModel):
    analysis: str
    pages: int
    model: str

# UI Design Models
class UIDesignRequest(BaseModel):
    prompt: str = "Analyze this UI design"
    output_format: str = "description"  # description, code, both
    code_framework: str = "react"  # react, vue, html

class UIDesignResponse(BaseModel):
    analysis: str
    code: Optional[str] = None
    model: str

SUPPORTED_MODELS = {
    "text": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "快速响应，适合日常使用"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "擅长高阶数学和代码"},
        {"id": "gemini-3.0-pro", "name": "Gemini 3.0 Pro", "description": "最新Pro模型，更强推理"}
    ],
    "image": [
        {"id": "gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image", "description": "快速图片生成"},
        {"id": "gemini-3-pro-image-preview", "name": "Gemini 3 Pro Image", "description": "高质量图片生成"},
        {"id": "gemini-3-pro-image-preview-2k", "name": "Gemini 3 Pro Image 2K", "description": "2048x2048高清"},
        {"id": "gemini-3-pro-image-preview-4k", "name": "Gemini 3 Pro Image 4K", "description": "4096x4096超高清"}
    ],
    "tts": [
        {"id": "tts-1", "name": "TTS-1", "description": "低延迟语音合成 (Gemini 2.5 Flash TTS)"},
        {"id": "tts-1-hd", "name": "TTS-1-HD", "description": "高质量语音合成 (Gemini 2.5 Pro TTS)"}
    ],
    "document": [
        {"id": "gemini-2.5-flash-pdf", "name": "PDF Analyzer", "description": "PDF文档分析"},
        {"id": "gemini-2.5-pro-pdf", "name": "PDF Analyzer Pro", "description": "深度PDF分析"}
    ],
    "design": [
        {"id": "gemini-2.5-flash-ui", "name": "UI Analyzer", "description": "UI设计分析"},
        {"id": "gemini-2.5-pro-ui", "name": "UI Analyzer Pro", "description": "深度UI分析+代码生成"}
    ]
}

class GeminiContent(BaseModel):
    role: str = "user"
    parts: List[Dict[str, Any]]

class GeminiRequest(BaseModel):
    contents: List[GeminiContent]
    generationConfig: Optional[Dict[str, Any]] = None

class CookieRequest(BaseModel):
    cookies: Dict[str, str]


# ============ 客户端初始化 ============
async def init_gemini_client():
    global gemini_client
    if gemini_client:
        try:
            await gemini_client.close()
        except:
            pass
    gemini_client = GeminiClient()
    gemini_client.cookies = {
        "__Secure-1PSID": cookie_store.get("__Secure-1PSID"),
        "__Secure-1PSIDCC": cookie_store.get("__Secure-1PSIDCC"),
        "__Secure-1PSIDTS": cookie_store.get("__Secure-1PSIDTS")
    }
    await gemini_client.init()
    return True


# ============ Cookie获取回调 ============
def get_current_cookies() -> dict:
    """获取当前gemini_client的Cookie（用于持久化）"""
    if gemini_client and hasattr(gemini_client, 'cookies'):
        return gemini_client.cookies
    return cookie_store


# ============ FastAPI App ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global REQUEST_SEMAPHORE, watermark_remover

    cookie_save_task = None

    print("=" * 50)
    print("Gemini Reverse API v4.1 启动中...")
    print("=" * 50)

    REQUEST_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

    if cookie_store.get("__Secure-1PSID"):
        try:
            await init_gemini_client()
            print("✅ Gemini客户端初始化成功!")

            # 启动Cookie自动保存任务
            if COOKIE_PERSISTENCE_ENABLED and cookie_persistence:
                cookie_save_task = asyncio.create_task(
                    cookie_persistence.start_auto_save(get_current_cookies)
                )
                print("✅ Cookie自动保存已启动!")

        except Exception as e:
            print(f"⚠️ Gemini客户端初始化失败: {e}")
            # 发送Bark通知
            if bark_notifier:
                asyncio.create_task(bark_notifier.notify_cookie_expired())
    else:
        print("⚠️ 未配置Cookie，请通过Web界面配置")

    # TTS状态
    if GOOGLE_AI_API_KEY:
        print(f"✅ TTS功能已启用 (API Key: {GOOGLE_AI_API_KEY[:15]}...)")
    else:
        print("⚠️ 未配置GOOGLE_AI_API_KEY，TTS功能不可用")

    try:
        from claude_compat import router as claude_router
        app.include_router(claude_router)
        print("✅ Claude API 兼容层已启用!")
    except Exception as e:
        print(f"⚠️ Claude 兼容层加载失败: {e}")

    print(f"✅ 并发限制: {MAX_CONCURRENCY}")
    print(f"✅ 断点续传数据库: {DB_PATH}")

    # Bark通知状态
    if bark_notifier and bark_notifier.enabled:
        print("✅ Bark通知已启用!")
    else:
        print("⚠️ Bark通知未配置")

    try:
        from watermark_remover import WatermarkRemover
        watermark_remover = WatermarkRemover()
        print("✅ 水印去除器初始化成功!")
    except Exception as e:
        print(f"⚠️ 水印去除器初始化失败: {e}")

    print("=" * 50)
    print("API 端点:")
    print("  文本: /v1/chat/completions, /v1/generate")
    print("  图片: /v1/images/generations, /v1/images/edit")
    print("  TTS:  /v1/audio/speech")
    print("  PDF:  /v1/documents/analyze")
    print("  UI:   /v1/design/analyze, /v1/design/to-code")
    print("=" * 50)

    yield

    # 关闭时保存最新Cookie
    if COOKIE_PERSISTENCE_ENABLED and cookie_persistence:
        cookies = get_current_cookies()
        if cookies:
            cookie_persistence.save_cookies(cookies)
            print("✅ Cookie已保存")
        if cookie_save_task:
            cookie_save_task.cancel()

    if gemini_client:
        await gemini_client.close()

app = FastAPI(title="Gemini Reverse API v4.2 (Hybrid)", lifespan=lifespan)


# ============ 基础 API 端点 ============
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "4.2",
        "mode": "hybrid",
        "provider": {
            "enabled": PROVIDER_CONFIG["enabled"],
            "model": PROVIDER_CONFIG["default_model"] if PROVIDER_CONFIG["enabled"] else None,
            "usage": "文本模型优先"
        },
        "cookie": {
            "ready": gemini_client is not None,
            "usage": "图片/视频模型 + Provider备用"
        },
        "tts_ready": bool(GOOGLE_AI_API_KEY),
        "watermark_removal": watermark_remover is not None,
        "cookie_persistence": COOKIE_PERSISTENCE_ENABLED,
        "bark_notification": bark_notifier.enabled if bark_notifier else False,
        "rate_limiter": rate_limiter.get_stats(),
        "task_stats": task_manager.get_stats(),
        "concurrency": {
            "max": MAX_CONCURRENCY,
            "available": REQUEST_SEMAPHORE._value if REQUEST_SEMAPHORE else 0
        }
    }

@app.get("/")
async def root():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/api/info")
async def api_info():
    return {
        "service": "Gemini Reverse API",
        "version": "4.2",
        "mode": "hybrid (Provider优先 + Cookie备用)",
        "architecture": {
            "text_models": "Provider API (官方格式) 优先，Cookie备用",
            "image_models": "Cookie模式 (gemini-webapi)",
            "video_models": "Cookie模式 (gemini-webapi)",
            "tts_models": "Google AI API Key"
        },
        "features": {
            "provider_mode": "文本模型使用Provider API优先",
            "cookie_fallback": "Provider失败时自动回退到Cookie",
            "retry": "指数退避重试 (最多5次)",
            "rate_limit": "智能速率控制 + 抖动",
            "checkpoint": "SQLite断点续传",
            "concurrency": f"支持{MAX_CONCURRENCY}并发",
            "watermark_removal": "反向Alpha混合去水印",
            "tts": "TTS语音合成 (需要API Key)",
            "pdf_analysis": "PDF文档分析",
            "ui_design": "UI设计理解与代码生成"
        },
        "endpoints": {
            "text": {
                "openai": "/v1/chat/completions",
                "gemini": "/gemini/v1beta/models/{model}:generateContent",
                "simple": "/v1/generate"
            },
            "image": {
                "generate": "/v1/images/generations",
                "edit": "/v1/images/edit",
                "batch": "/v1/batch/images"
            },
            "audio": {
                "speech": "/v1/audio/speech"
            },
            "document": {
                "analyze": "/v1/documents/analyze"
            },
            "design": {
                "analyze": "/v1/design/analyze",
                "to_code": "/v1/design/to-code"
            }
        }
    }

@app.get("/api/models")
async def get_models():
    all_models = (
        SUPPORTED_MODELS["text"] +
        SUPPORTED_MODELS["image"] +
        SUPPORTED_MODELS["tts"] +
        SUPPORTED_MODELS["document"] +
        SUPPORTED_MODELS["design"]
    )
    return {"models": all_models, "categories": SUPPORTED_MODELS, "default": "gemini-2.5-flash"}

@app.get("/v1/models")
async def get_models_openai():
    all_models = (
        SUPPORTED_MODELS["text"] +
        SUPPORTED_MODELS["image"] +
        SUPPORTED_MODELS["tts"] +
        SUPPORTED_MODELS["document"] +
        SUPPORTED_MODELS["design"]
    )
    return {"object": "list", "data": [{"id": m["id"], "object": "model", "owned_by": "google"} for m in all_models]}

@app.get("/api/cookies/status")
async def get_cookie_status():
    has_cookie = bool(cookie_store.get("__Secure-1PSID"))
    client_ready = gemini_client is not None
    if not has_cookie:
        return {"valid": False, "message": "未配置Cookie"}
    if not client_ready:
        return {"valid": False, "message": "Cookie已配置但客户端未初始化"}
    return {"valid": True, "message": "Cookie有效，客户端已就绪"}

@app.post("/api/cookies")
async def save_cookies(request: CookieRequest):
    global cookie_store
    cookies = request.cookies
    psid = cookies.get("__Secure-1PSID") or cookies.get("SECURE_1PSID") or cookies.get("1PSID")
    psidcc = cookies.get("__Secure-1PSIDCC") or cookies.get("SECURE_1PSIDCC") or cookies.get("1PSIDCC")
    psidts = cookies.get("__Secure-1PSIDTS") or cookies.get("SECURE_1PSIDTS") or cookies.get("1PSIDTS")
    if not psid:
        raise HTTPException(status_code=400, detail="__Secure-1PSID 是必填项")
    cookie_store["__Secure-1PSID"] = psid
    cookie_store["__Secure-1PSIDCC"] = psidcc
    cookie_store["__Secure-1PSIDTS"] = psidts
    try:
        await init_gemini_client()
        return {"success": True, "message": "Cookie保存成功，客户端已重新初始化"}
    except Exception as e:
        return {"success": False, "message": f"Cookie已保存，但初始化失败: {str(e)}"}


# ============ 文本生成 ============
@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    # v4.2: Provider模式不需要gemini_client
    if not gemini_client and not PROVIDER_CONFIG["enabled"]:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化且Provider未启用")
    try:
        response = await call_gemini_with_retry(request.prompt, model=request.model)
        return GenerateResponse(text=response.text, model=request.model)
    except RetryError as e:
        raise HTTPException(status_code=429, detail=f"重试{RETRY_CONFIG['max_attempts']}次后仍失败: {e}")
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 图片生成 ============
@app.post("/v1/generate-images", response_model=ImageGenerateResponse)
async def generate_images(request: ImageGenerateRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    try:
        temp_file = None

        if request.image:
            image_data = request.image
            if image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            image_bytes = b64.b64decode(image_data)

            temp_file = f"/tmp/ref_image_{uuid.uuid4().hex[:8]}.png"
            with open(temp_file, "wb") as f:
                f.write(image_bytes)

            enhanced_prompt = f"Based on the reference image provided, {request.prompt}. Generate a new image."
            response = await call_gemini_with_retry(enhanced_prompt, files=[temp_file], image_mode=True)
        else:
            enhanced_prompt = create_image_prompt(request.prompt)
            response = await call_gemini_with_retry(enhanced_prompt, image_mode=True)

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

        image_data_list = []
        if response.images:
            for idx, img in enumerate(response.images):
                if hasattr(img, "url") and img.url:
                    cookies = getattr(img, "cookies", {}) or {}
                    download_url = img.url
                    if "=s" not in download_url:
                        download_url = f"{img.url}=s4096"

                    async with httpx.AsyncClient(follow_redirects=True, cookies=cookies, timeout=60.0) as http_client:
                        resp = await http_client.get(download_url)
                        if resp.status_code == 200:
                            image_bytes = resp.content

                            # 去除水印
                            if watermark_remover:
                                from fastapi.concurrency import run_in_threadpool
                                try:
                                    image_bytes = await run_in_threadpool(
                                        watermark_remover.remove_from_bytes,
                                        image_bytes
                                    )
                                    logger.info(f"✅ 水印已去除: 图片{idx+1}")
                                except Exception as e:
                                    logger.warning(f"⚠️ 去水印失败，返回原图: {e}")

                            if request.response_type == "url":
                                filename = generate_image_filename(request.prompt, idx)
                                try:
                                    url = await upload_to_r2(image_bytes, filename)
                                    image_data_list.append(url)
                                    logger.info(f"✅ 图片已上传: {filename}")
                                except Exception as e:
                                    logger.error(f"❌ R2上传失败: {e}")
                                    image_base64 = b64.b64encode(image_bytes).decode("utf-8")
                                    image_data_list.append(f"data:image/png;base64,{image_base64}")
                            else:
                                content_type = resp.headers.get("content-type", "image/png")
                                mime_type = "image/png"
                                if "jpeg" in content_type or "jpg" in content_type:
                                    mime_type = "image/jpeg"
                                elif "webp" in content_type:
                                    mime_type = "image/webp"
                                image_base64 = b64.b64encode(image_bytes).decode("utf-8")
                                image_data_list.append(f"data:{mime_type};base64,{image_base64}")

        if not image_data_list:
            raise HTTPException(status_code=400, detail=f"未能生成图片: {response.text[:200] if response.text else '无响应'}")

        return ImageGenerateResponse(images=image_data_list)

    except RetryError as e:
        raise HTTPException(status_code=429, detail=f"重试失败: {e}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/images/generations", response_model=ImageGenerateResponse)
async def images_generations(request: ImageGenerateRequest):
    return await generate_images(request)

@app.post("/v1/images/edit", response_model=ImageGenerateResponse)
@app.post("/v1/images/edits", response_model=ImageGenerateResponse)
async def images_edit(request: ImageGenerateRequest):
    if not request.image:
        raise HTTPException(status_code=400, detail="图片编辑需要提供image参数(base64)")
    return await generate_images(request)


# ============ TTS 语音合成 ============
@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """
    OpenAI兼容的TTS接口

    支持的模型:
    - tts-1: 低延迟 (Gemini 2.5 Flash TTS)
    - tts-1-hd: 高质量 (Gemini 2.5 Pro TTS)

    支持的voice:
    - alloy, echo, fable, onyx, nova, shimmer
    """
    try:
        if not request.input or not request.input.strip():
            raise HTTPException(status_code=400, detail="input不能为空")

        logger.info(f"TTS请求: model={request.model}, voice={request.voice}, text_length={len(request.input)}")

        wav_data = await call_tts_api(
            text=request.input,
            model=request.model,
            voice=request.voice
        )

        logger.info(f"✅ TTS成功: 生成{len(wav_data)}字节音频")

        return Response(
            content=wav_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{uuid.uuid4().hex[:8]}.wav"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/audio/voices")
async def list_voices():
    """列出可用的TTS语音"""
    return {
        "voices": [
            {"id": "alloy", "name": "Alloy", "description": "中性、专业的语调"},
            {"id": "echo", "name": "Echo", "description": "温暖、友好的语调"},
            {"id": "fable", "name": "Fable", "description": "富有表现力的叙事风格"},
            {"id": "onyx", "name": "Onyx", "description": "深沉、权威的语调"},
            {"id": "nova", "name": "Nova", "description": "明亮、活力的语调"},
            {"id": "shimmer", "name": "Shimmer", "description": "柔和、温柔的语调"}
        ],
        "default": "alloy"
    }


# ============ PDF 文档分析 ============
@app.post("/v1/documents/analyze", response_model=PDFAnalysisResponse)
async def analyze_document(
    file: UploadFile = File(...),
    prompt: str = Form(default="请详细分析这个PDF文档的内容"),
    detail_level: str = Form(default="medium")
):
    """
    PDF文档分析接口

    参数:
    - file: PDF文件
    - prompt: 分析提示词
    - detail_level: 详细程度 (low/medium/high)
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    try:
        # 保存临时文件
        temp_path = f"/tmp/pdf_{uuid.uuid4().hex[:8]}.pdf"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # 构建分析提示
        detail_prompts = {
            "low": "简要概括文档的主要内容（100字以内）",
            "medium": "详细分析文档的结构、主要内容和关键信息",
            "high": "深度分析文档，包括：1)文档结构 2)详细内容摘要 3)关键数据提取 4)逻辑分析 5)潜在问题或建议"
        }

        analysis_prompt = f"""分析以下PDF文档。

{prompt}

分析要求: {detail_prompts.get(detail_level, detail_prompts['medium'])}

请用中文回答。"""

        response = await call_gemini_with_retry(analysis_prompt, files=[temp_path])

        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 估算页数（简单估算）
        estimated_pages = max(1, len(content) // 50000)

        return PDFAnalysisResponse(
            analysis=response.text,
            pages=estimated_pages,
            model="gemini-2.5-flash"
        )

    except RetryError as e:
        raise HTTPException(status_code=429, detail=f"重试失败: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF分析错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/documents/extract")
async def extract_document_data(
    file: UploadFile = File(...),
    extraction_type: str = Form(default="text"),
    format: str = Form(default="markdown")
):
    """
    PDF数据提取接口

    参数:
    - file: PDF文件
    - extraction_type: 提取类型 (text/tables/images/all)
    - format: 输出格式 (markdown/json/plain)
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    try:
        temp_path = f"/tmp/pdf_{uuid.uuid4().hex[:8]}.pdf"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        extraction_prompts = {
            "text": "提取文档中的所有文本内容，保持原有结构",
            "tables": "识别并提取文档中的所有表格，以Markdown表格格式输出",
            "images": "描述文档中的所有图片，包括图表、照片等",
            "all": "完整提取文档内容：1)所有文本 2)所有表格(Markdown格式) 3)所有图片描述"
        }

        format_instructions = {
            "markdown": "以Markdown格式输出",
            "json": "以JSON格式输出，使用适当的结构",
            "plain": "以纯文本格式输出"
        }

        prompt = f"""{extraction_prompts.get(extraction_type, extraction_prompts['text'])}

{format_instructions.get(format, format_instructions['markdown'])}"""

        response = await call_gemini_with_retry(prompt, files=[temp_path])

        if os.path.exists(temp_path):
            os.remove(temp_path)

        return {
            "extraction_type": extraction_type,
            "format": format,
            "content": response.text,
            "model": "gemini-2.5-flash"
        }

    except Exception as e:
        logger.error(f"PDF提取错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ UI 设计理解 ============
@app.post("/v1/design/analyze", response_model=UIDesignResponse)
async def analyze_ui_design(
    file: UploadFile = File(...),
    prompt: str = Form(default="分析这个UI设计"),
    output_format: str = Form(default="description")
):
    """
    UI设计分析接口

    参数:
    - file: UI设计图片 (PNG/JPG/WEBP)
    - prompt: 分析提示词
    - output_format: 输出格式 (description/components/both)
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    allowed_types = ['.png', '.jpg', '.jpeg', '.webp']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
        raise HTTPException(status_code=400, detail="只支持PNG/JPG/WEBP图片")

    try:
        temp_path = f"/tmp/ui_{uuid.uuid4().hex[:8]}{Path(file.filename).suffix}"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        format_prompts = {
            "description": "详细描述这个UI设计的视觉元素、布局、配色、交互模式",
            "components": "列出设计中的所有UI组件，包括按钮、输入框、卡片等，说明它们的样式和状态",
            "both": "1) 设计描述：视觉元素、布局、配色\n2) 组件列表：所有UI组件及其样式"
        }

        analysis_prompt = f"""分析这个UI设计图。

{prompt}

分析要求: {format_prompts.get(output_format, format_prompts['description'])}

请用中文详细描述。"""

        response = await call_gemini_with_retry(analysis_prompt, files=[temp_path])

        if os.path.exists(temp_path):
            os.remove(temp_path)

        return UIDesignResponse(
            analysis=response.text,
            code=None,
            model="gemini-2.5-flash"
        )

    except Exception as e:
        logger.error(f"UI分析错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/design/to-code")
async def ui_to_code(
    file: UploadFile = File(...),
    framework: str = Form(default="react"),
    style_library: str = Form(default="tailwind"),
    include_logic: bool = Form(default=False)
):
    """
    UI设计转代码接口

    参数:
    - file: UI设计图片
    - framework: 目标框架 (react/vue/html/svelte)
    - style_library: 样式库 (tailwind/css/styled-components)
    - include_logic: 是否包含交互逻辑
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    allowed_types = ['.png', '.jpg', '.jpeg', '.webp']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
        raise HTTPException(status_code=400, detail="只支持PNG/JPG/WEBP图片")

    try:
        temp_path = f"/tmp/ui_{uuid.uuid4().hex[:8]}{Path(file.filename).suffix}"
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        framework_templates = {
            "react": "React函数组件 (使用hooks)",
            "vue": "Vue 3组合式API组件",
            "html": "纯HTML + CSS",
            "svelte": "Svelte组件"
        }

        style_templates = {
            "tailwind": "Tailwind CSS类名",
            "css": "传统CSS样式",
            "styled-components": "styled-components (CSS-in-JS)"
        }

        logic_instruction = "包含基本的交互逻辑（点击、输入、状态管理）" if include_logic else "只生成静态UI结构，不需要交互逻辑"

        prompt = f"""将这个UI设计转换为代码。

技术栈:
- 框架: {framework_templates.get(framework, 'React')}
- 样式: {style_templates.get(style_library, 'Tailwind CSS')}

要求:
1. 尽可能还原设计稿的视觉效果
2. 使用语义化的HTML结构
3. 响应式设计（如适用）
4. {logic_instruction}
5. 代码需要可直接运行

请生成完整的组件代码。"""

        response = await call_gemini_with_retry(prompt, files=[temp_path])

        if os.path.exists(temp_path):
            os.remove(temp_path)

        return {
            "framework": framework,
            "style_library": style_library,
            "code": response.text,
            "model": "gemini-2.5-flash"
        }

    except Exception as e:
        logger.error(f"UI转代码错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 批量图片生成（并发+断点续传） ============
async def process_batch_image(task_id: str, prompt: str, response_type: str):
    """处理单个批量任务"""
    task_manager.update_task(task_id, "processing")

    try:
        enhanced_prompt = create_image_prompt(prompt)
        response = await call_gemini_with_retry(enhanced_prompt, image_mode=True)

        if response.images:
            img = response.images[0]
            if hasattr(img, "url") and img.url:
                cookies = getattr(img, "cookies", {}) or {}
                download_url = f"{img.url}=s4096" if "=s" not in img.url else img.url

                async with httpx.AsyncClient(follow_redirects=True, cookies=cookies, timeout=60.0) as client:
                    resp = await client.get(download_url)
                    if resp.status_code == 200:
                        if response_type == "url":
                            filename = generate_image_filename(prompt, 0)
                            url = await upload_to_r2(resp.content, filename)
                            task_manager.update_task(task_id, "completed", url)
                            return url
                        else:
                            b64_data = b64.b64encode(resp.content).decode()
                            task_manager.update_task(task_id, "completed", f"data:image/png;base64,{b64_data}")
                            return b64_data

        task_manager.update_task(task_id, "failed", error="No image generated")
        return None

    except Exception as e:
        task_manager.update_task(task_id, "failed", error=str(e))
        logger.error(f"Task {task_id} failed: {e}")
        return None


async def batch_worker(queue: asyncio.Queue, results: dict):
    """批量任务Worker"""
    while True:
        try:
            task = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            if queue.empty():
                break
            continue

        task_id, prompt, response_type = task

        existing = task_manager.get_task(task_id)
        if existing and existing["status"] == "completed":
            results[task_id] = existing["output_data"]
            queue.task_done()
            continue

        result = await process_batch_image(task_id, prompt, response_type)
        results[task_id] = result
        queue.task_done()


@app.post("/v1/batch/images", response_model=BatchImageResponse)
async def batch_generate_images(request: BatchImageRequest, background_tasks: BackgroundTasks):
    """批量图片生成（后台任务，支持断点续传）"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    concurrency = min(request.concurrency, MAX_CONCURRENCY)

    for i, prompt in enumerate(request.prompts):
        task_id = f"{batch_id}_task_{i}"
        task_manager.create_task(task_id, "batch_image", prompt)

    async def run_batch():
        queue = asyncio.Queue()
        results = {}

        for i, prompt in enumerate(request.prompts):
            task_id = f"{batch_id}_task_{i}"
            queue.put_nowait((task_id, prompt, request.response_type))

        workers = [asyncio.create_task(batch_worker(queue, results)) for _ in range(concurrency)]
        await asyncio.gather(*workers)
        logger.info(f"Batch {batch_id} completed: {len(results)} tasks")

    background_tasks.add_task(run_batch)

    return BatchImageResponse(
        batch_id=batch_id,
        total=len(request.prompts),
        status="processing",
        message=f"批量任务已创建，{concurrency}并发处理中"
    )


@app.get("/v1/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """获取批量任务状态"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT task_id, status, output_data, error_message FROM tasks WHERE task_id LIKE ?",
        (f"{batch_id}%",)
    )
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not tasks:
        raise HTTPException(status_code=404, detail="批次不存在")

    completed = [t for t in tasks if t["status"] == "completed"]
    failed = [t for t in tasks if t["status"] == "failed"]
    pending = [t for t in tasks if t["status"] in ("pending", "processing")]

    return {
        "batch_id": batch_id,
        "total": len(tasks),
        "completed": len(completed),
        "failed": len(failed),
        "pending": len(pending),
        "progress": f"{len(completed)}/{len(tasks)}",
        "status": "completed" if not pending else "processing",
        "results": [{"task_id": t["task_id"], "url": t["output_data"]} for t in completed],
        "errors": [{"task_id": t["task_id"], "error": t["error_message"]} for t in failed]
    }


# ============ Chat Completions ============
@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    # v4.2: Provider模式不需要gemini_client
    if not gemini_client and not PROVIDER_CONFIG["enabled"]:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化且Provider未启用")
    try:
        messages = request.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="messages为空")
        prompt = messages[-1].get("content", "")
        model = request.get("model", "gemini-2.5-flash")

        response = await call_gemini_with_retry(prompt, model=model)

        return {
            "id": "chatcmpl-gemini-reverse",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response.text},
                "finish_reason": "stop"
            }]
        }
    except RetryError as e:
        raise HTTPException(status_code=429, detail=f"重试失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Gemini Native Format ============
@app.post("/gemini/v1beta/models/{model}:generateContent")
async def gemini_generate_content(model: str, request: GeminiRequest):
    # v4.2: Provider模式不需要gemini_client
    if not gemini_client and not PROVIDER_CONFIG["enabled"]:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化且Provider未启用")
    try:
        if not request.contents:
            raise HTTPException(status_code=400, detail="contents为空")

        last_content = request.contents[-1]
        prompt = ""
        for part in last_content.parts:
            if "text" in part:
                prompt += part["text"]

        # 检测是否是图片模型
        is_image_model = model in IMAGE_MODELS

        if is_image_model:
            # 图片模型: 增强提示词并使用image_mode
            enhanced_prompt = create_image_prompt(prompt)
            response = await call_gemini_with_retry(enhanced_prompt, image_mode=True)

            # 处理图片响应
            parts = []
            if response.images:
                for img in response.images:
                    if hasattr(img, "url") and img.url:
                        cookies = getattr(img, "cookies", {}) or {}
                        download_url = img.url
                        if "=s" not in download_url:
                            download_url = f"{img.url}=s4096"

                        async with httpx.AsyncClient(follow_redirects=True, cookies=cookies, timeout=60.0) as http_client:
                            resp = await http_client.get(download_url)
                            if resp.status_code == 200:
                                image_bytes = resp.content

                                # 去除水印
                                if watermark_remover:
                                    from fastapi.concurrency import run_in_threadpool
                                    try:
                                        image_bytes = await run_in_threadpool(
                                            watermark_remover.remove_from_bytes,
                                            image_bytes
                                        )
                                        logger.info(f"✅ 水印已去除 (Gemini原生格式)")
                                    except Exception as e:
                                        logger.warning(f"⚠️ 去水印失败，返回原图: {e}")

                                # 编码为base64
                                content_type = resp.headers.get("content-type", "image/png")
                                mime_type = "image/png"
                                if "jpeg" in content_type or "jpg" in content_type:
                                    mime_type = "image/jpeg"
                                elif "webp" in content_type:
                                    mime_type = "image/webp"

                                image_base64 = b64.b64encode(image_bytes).decode("utf-8")
                                parts.append({
                                    "inlineData": {
                                        "mimeType": mime_type,
                                        "data": image_base64
                                    }
                                })

            # 如果也有文本，添加文本部分
            if response.text:
                parts.append({"text": response.text})

            if not parts:
                raise HTTPException(status_code=400, detail="未能生成图片")

            return {
                "candidates": [{
                    "content": {"parts": parts, "role": "model"},
                    "finishReason": "STOP",
                    "index": 0
                }],
                "usageMetadata": {
                    "promptTokenCount": len(prompt.split()),
                    "candidatesTokenCount": 1,
                    "totalTokenCount": len(prompt.split()) + 1
                },
                "modelVersion": model
            }
        else:
            # 文本模型: 原有逻辑
            response = await call_gemini_with_retry(prompt, model=model)

            return {
                "candidates": [{
                    "content": {"parts": [{"text": response.text}], "role": "model"},
                    "finishReason": "STOP",
                    "index": 0
                }],
                "usageMetadata": {
                    "promptTokenCount": len(prompt.split()),
                    "candidatesTokenCount": len(response.text.split()),
                    "totalTokenCount": len(prompt.split()) + len(response.text.split())
                },
                "modelVersion": model
            }
    except RetryError as e:
        raise HTTPException(status_code=429, detail=f"重试失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1beta/models/{model}:generateContent")
@app.post("/v1/models/{model}:generateContent")
async def nexusai_gemini_generate_content(model: str, request: GeminiRequest):
    return await gemini_generate_content(model, request)


# ============ Gemini 模型列表 (用于第三方客户端) ============
@app.get("/gemini/v1beta/models")
async def gemini_list_models():
    """Gemini原生格式的模型列表"""
    models = []
    for category in SUPPORTED_MODELS.values():
        for m in category:
            models.append({
                "name": f"models/{m['id']}",
                "displayName": m["name"],
                "description": m["description"],
                "inputTokenLimit": 1048576,
                "outputTokenLimit": 8192,
                "supportedGenerationMethods": ["generateContent", "streamGenerateContent"]
            })
    return {"models": models}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
