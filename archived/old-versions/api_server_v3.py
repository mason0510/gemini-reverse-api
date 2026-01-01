"""
Gemini Reverse API v3.1
功能: 智能重试 + 动态延迟 + 断点续传 + 并发支持 + 去水印
关键词: gemini, api, retry, checkpoint, concurrency, rate-limit, watermark-removal
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gemini_webapi import GeminiClient
import os
import asyncio
import re
import hashlib
import sqlite3
import random
import time
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

cookie_store = {
    "__Secure-1PSID": os.getenv("SECURE_1PSID"),
    "__Secure-1PSIDCC": os.getenv("SECURE_1PSIDCC"),
    "__Secure-1PSIDTS": os.getenv("SECURE_1PSIDTS")
}

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
# 在启动时初始化，避免热路径加载
watermark_remover = None

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

            # 清理1分钟前的记录
            self.request_times = [t for t in self.request_times if now - t < 60]

            # 检查是否达到RPM限制
            if len(self.request_times) >= self.rpm_limit:
                oldest = self.request_times[0]
                wait_time = 60 - (now - oldest) + self._add_jitter()
                if wait_time > 0:
                    logger.info(f"RPM限制触发，等待 {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)

            # 添加基础延迟+抖动
            delay = self.current_delay + self._add_jitter()
            if delay > 0:
                await asyncio.sleep(delay)

            self.request_times.append(time.time())
            return delay

    def _add_jitter(self) -> float:
        """添加随机抖动防止惊群效应"""
        return random.uniform(0, RATE_LIMIT_CONFIG["jitter_range"])

    def report_success(self):
        """报告请求成功，逐步降低延迟"""
        self.consecutive_429s = 0
        self.current_delay = max(
            RATE_LIMIT_CONFIG["base_delay"],
            self.current_delay * 0.9  # 成功后延迟降低10%
        )

    def report_rate_limit(self):
        """报告429错误，指数增加延迟"""
        self.consecutive_429s += 1
        self.current_delay = min(
            RATE_LIMIT_CONFIG["max_delay"],
            self.current_delay * RATE_LIMIT_CONFIG["backoff_multiplier"]
        )
        logger.warning(f"429错误，延迟调整为 {self.current_delay:.1f}s")

    def get_stats(self) -> dict:
        """获取限流器状态"""
        return {
            "current_delay": round(self.current_delay, 2),
            "requests_last_minute": len(self.request_times),
            "consecutive_429s": self.consecutive_429s,
            "rpm_limit": self.rpm_limit
        }

rate_limiter = SmartRateLimiter(rpm_limit=RATE_LIMIT_CONFIG["rpm_limit"])

# ============ 断点续传：SQLite任务状态管理 ============
class TaskStateManager:
    """SQLite任务状态管理器，支持断点续传"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        """)
        conn.commit()
        conn.close()

    def create_task(self, task_id: str, task_type: str, input_data: str) -> bool:
        """创建任务，如果已存在返回False"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO tasks (task_id, task_type, input_data) VALUES (?, ?, ?)",
                (task_id, task_type, input_data)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 任务已存在
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_task(self, task_id: str, status: str, output_data: str = None, error: str = None):
        """更新任务状态"""
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
        """获取待处理任务（断点续传）"""
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
        """获取任务统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count FROM tasks GROUP BY status
        """)
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
        """清理旧任务"""
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


# ============ 带重试的Gemini调用 ============
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
async def call_gemini_with_retry(prompt: str, files: List[str] = None, model=None):
    """带智能重试的Gemini API调用"""
    global gemini_client, rate_limiter

    if not gemini_client:
        raise ClientError("Gemini客户端未初始化")

    # 获取信号量（并发控制）
    async with REQUEST_SEMAPHORE:
        # 智能速率控制
        await rate_limiter.acquire()

        try:
            from gemini_webapi.constants import Model
            model = model or Model.G_2_5_FLASH

            if files:
                response = await gemini_client.generate_content(prompt, files=files, model=model)
            else:
                response = await gemini_client.generate_content(prompt, model=model)

            rate_limiter.report_success()
            return response

        except Exception as e:
            error_str = str(e).lower()

            # 429 限流错误 - 可重试
            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                rate_limiter.report_rate_limit()
                raise RateLimitError(f"Rate limit: {e}")

            # 5xx 服务器错误 - 可重试
            elif "500" in error_str or "503" in error_str or "server" in error_str:
                raise ServerError(f"Server error: {e}")

            # 其他错误 - 不重试
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
    """批量图片生成请求"""
    prompts: List[str]
    response_type: str = "url"
    concurrency: int = 2

class BatchImageResponse(BaseModel):
    """批量图片生成响应"""
    batch_id: str
    total: int
    status: str
    message: str

SUPPORTED_MODELS = {
    "text": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "快速响应，适合日常使用"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "擅长高阶数学和代码"},
        {"id": "gemini-3.0-pro", "name": "Gemini 3.0 Pro", "description": "最新Pro模型，更强推理"}
    ],
    "image": [
        {"id": "gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image", "description": "快速图片生成"},
        {"id": "gemini-3-pro-image-preview", "name": "Gemini 3 Pro Image", "description": "高质量图片生成，支持参考图编辑"}
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


# ============ FastAPI App ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global REQUEST_SEMAPHORE, watermark_remover

    # 启动时
    print("正在初始化Gemini客户端...")
    REQUEST_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

    if cookie_store.get("__Secure-1PSID"):
        try:
            await init_gemini_client()
            print("✅ Gemini客户端初始化成功!")
        except Exception as e:
            print(f"⚠️ Gemini客户端初始化失败: {e}")
    else:
        print("⚠️ 未配置Cookie，请通过Web界面配置")

    try:
        from claude_compat import router as claude_router
        app.include_router(claude_router)
        print("✅ Claude API 兼容层已启用!")
    except Exception as e:
        print(f"⚠️ Claude 兼容层加载失败: {e}")

    print(f"✅ 并发限制: {MAX_CONCURRENCY}")
    print(f"✅ 断点续传数据库: {DB_PATH}")

    # 初始化水印去除器
    try:
        from watermark_remover import WatermarkRemover
        watermark_remover = WatermarkRemover()
        print("✅ 水印去除器初始化成功!")
    except Exception as e:
        print(f"⚠️ 水印去除器初始化失败: {e}")

    yield

    # 关闭时
    if gemini_client:
        await gemini_client.close()

app = FastAPI(title="Gemini Reverse API v3.1", lifespan=lifespan)


# ============ API 端点 ============
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.1",
        "client_ready": gemini_client is not None,
        "watermark_removal": watermark_remover is not None,
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
        "version": "3.1",
        "features": {
            "retry": "指数退避重试 (最多5次)",
            "rate_limit": "智能速率控制 + 抖动",
            "checkpoint": "SQLite断点续传",
            "concurrency": f"支持{MAX_CONCURRENCY}并发",
            "watermark_removal": "反向Alpha混合去水印"
        },
        "endpoints": {
            "openai": "/v1/chat/completions",
            "gemini": "/gemini/v1beta/models/{model}:generateContent",
            "simple": "/v1/generate",
            "images": "/v1/generate-images",
            "image_edit": "/v1/images/edit",
            "batch_images": "/v1/batch/images",
            "batch_status": "/v1/batch/{batch_id}/status"
        }
    }

@app.get("/api/models")
async def get_models():
    all_models = SUPPORTED_MODELS["text"] + SUPPORTED_MODELS["image"]
    return {"models": all_models, "categories": SUPPORTED_MODELS, "default": "gemini-2.5-flash"}

@app.get("/v1/models")
async def get_models_openai():
    all_models = SUPPORTED_MODELS["text"] + SUPPORTED_MODELS["image"]
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
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")
    try:
        response = await call_gemini_with_retry(request.prompt)
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
        import base64 as b64
        import httpx

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
            response = await call_gemini_with_retry(enhanced_prompt, files=[temp_file])
        else:
            enhanced_prompt = create_image_prompt(request.prompt)
            response = await call_gemini_with_retry(enhanced_prompt)

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


# ============ 批量图片生成（并发+断点续传） ============
async def process_batch_image(task_id: str, prompt: str, response_type: str):
    """处理单个批量任务"""
    task_manager.update_task(task_id, "processing")

    try:
        enhanced_prompt = create_image_prompt(prompt)
        response = await call_gemini_with_retry(enhanced_prompt)

        if response.images:
            import base64 as b64
            import httpx

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

        # 检查是否已完成（断点续传）
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

    # 创建任务
    for i, prompt in enumerate(request.prompts):
        task_id = f"{batch_id}_task_{i}"
        task_manager.create_task(task_id, "batch_image", prompt)

    # 后台执行
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
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")
    try:
        messages = request.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="messages为空")
        prompt = messages[-1].get("content", "")

        response = await call_gemini_with_retry(prompt)

        return {
            "id": "chatcmpl-gemini-reverse",
            "object": "chat.completion",
            "model": request.get("model", "gemini-2.5-flash"),
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
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化")
    try:
        if not request.contents:
            raise HTTPException(status_code=400, detail="contents为空")

        last_content = request.contents[-1]
        prompt = ""
        for part in last_content.parts:
            if "text" in part:
                prompt += part["text"]

        response = await call_gemini_with_retry(prompt)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
