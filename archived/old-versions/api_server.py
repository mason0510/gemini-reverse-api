from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from gemini_webapi import GeminiClient
import os
import asyncio
import time
import random
import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime
from dotenv import load_dotenv
from model_rate_limiter import ModelRateLimiter

# 加载.env文件
load_dotenv()

app = FastAPI(title="Gemini Reverse API")

# 静态文件目录
WEB_DIR = Path(__file__).parent / "web"

# Cookie存储（内存中，生产环境应使用持久化存储）
cookie_store = {
    "__Secure-1PSID": os.getenv("SECURE_1PSID"),
    "__Secure-1PSIDCC": os.getenv("SECURE_1PSIDCC"),
    "__Secure-1PSIDTS": os.getenv("SECURE_1PSIDTS")
}

gemini_client = None
model_limiter = None  # Redis限流器

# ========== API Key多平台配置 ==========
API_KEY_PROVIDERS = {
    "default": os.getenv("GOOGLE_AI_API_KEY"),
    "backup": os.getenv("GOOGLE_AI_API_KEY_BACKUP"),
    "platform2": os.getenv("GOOGLE_AI_API_KEY_PLATFORM2"),
    "platform3": os.getenv("GOOGLE_AI_API_KEY_PLATFORM3"),
}

def get_api_key(provider: str = "default") -> str:
    """
    获取指定平台的 API Key

    Args:
        provider: 平台名称 (default/backup/platform2/platform3)

    Returns:
        API Key字符串

    Raises:
        HTTPException: 如果指定的provider不存在或API Key未配置
    """
    if provider not in API_KEY_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}. Available: {list(API_KEY_PROVIDERS.keys())}"
        )

    api_key = API_KEY_PROVIDERS[provider]
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"API Key for provider '{provider}' not configured in .env file"
        )

    return api_key

# ========== Bark通知配置 ==========
BARK_KEY = os.getenv("BARK_KEY", "")  # Bark设备Key
BARK_SERVER = os.getenv("BARK_SERVER", "https://api.day.app")  # Bark服务器地址
ENABLE_BARK_NOTIFICATION = os.getenv("ENABLE_BARK_NOTIFICATION", "true").lower() == "true"

# 记录上次发送Bark通知的时间（避免重复发送）
last_bark_notification = {"cookie_expired": 0}
BARK_COOLDOWN = 3600  # 通知冷却时间（秒），1小时内不重复发送

async def send_bark_notification(title: str, message: str, level: str = "timeSensitive"):
    """
    发送Bark通知

    Args:
        title: 通知标题
        message: 通知内容
        level: 通知级别（passive/active/timeSensitive/critical）
    """
    if not ENABLE_BARK_NOTIFICATION or not BARK_KEY:
        return False

    try:
        # URL编码
        from urllib.parse import quote
        url = f"{BARK_SERVER}/{BARK_KEY}/{quote(title)}/{quote(message)}?level={level}&sound=alarm&group=gemini-api"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                print(f"📱 Bark通知已发送: {title}")
                return True
            else:
                print(f"⚠️ Bark通知发送失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Bark通知异常: {e}")
        return False

async def notify_cookie_expired():
    """通知Cookie已过期（带冷却时间）"""
    now = time.time()
    if now - last_bark_notification["cookie_expired"] < BARK_COOLDOWN:
        return  # 冷却期内，不重复发送

    await send_bark_notification(
        "⚠️ Gemini API Cookie过期",
        f"文本和图片生成功能不可用\n"
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"服务器: 82.29.54.80:8100\n"
        f"需要更新Cookie",
        level="timeSensitive"
    )
    last_bark_notification["cookie_expired"] = now

# ========== 频率限制配置 ==========
# 每小时最大请求数（模拟正常用户使用）
MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", 60))  # 默认60次/小时
# 请求延迟范围（秒）
MIN_DELAY = float(os.getenv("MIN_DELAY", 1.0))  # 最小延迟1秒
MAX_DELAY = float(os.getenv("MAX_DELAY", 3.0))  # 最大延迟3秒

# 并发请求限制
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 5))  # 最大同时请求数
current_requests = 0
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# 请求大小限制
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", 10 * 1024 * 1024))  # 10MB

# 存储每个IP的请求时间戳（使用deque自动滑动窗口）
request_tracker = defaultdict(lambda: deque(maxlen=MAX_REQUESTS_PER_HOUR))

# 浏览器 User-Agent 列表（模拟真实用户）- 更新到最新版本
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# Referer 列表（模拟来自Gemini官方页面）
REFERERS = [
    "https://gemini.google.com/app",
    "https://aistudio.google.com/app/prompts/new_chat",
    "https://makersuite.google.com/",
]

# Accept-Language 列表（模拟不同地区用户）
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-TW,zh;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en;q=0.8",
]

def get_random_user_agent():
    """随机选择一个User-Agent"""
    return random.choice(USER_AGENTS)

def get_random_referer():
    """随机选择一个Referer"""
    return random.choice(REFERERS)

def get_random_accept_language():
    """随机选择一个Accept-Language"""
    return random.choice(ACCEPT_LANGUAGES)

async def check_rate_limit(client_ip: str) -> bool:
    """
    检查请求频率限制
    返回True表示允许请求，False表示超过限制
    """
    now = time.time()
    timestamps = request_tracker[client_ip]

    # 清理1小时前的记录
    while timestamps and now - timestamps[0] > 3600:
        timestamps.popleft()

    # 检查是否超过限制
    if len(timestamps) >= MAX_REQUESTS_PER_HOUR:
        return False

    # 记录当前请求时间
    timestamps.append(now)
    return True

async def apply_random_delay():
    """应用随机延迟（模拟人类操作）"""
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    await asyncio.sleep(delay)

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.5-flash"  # gemini-2.5-flash, gemini-2.5-pro, gemini-3.0-pro

# 模型映射表
MODEL_MAP = {
    # 文本模型
    "gemini-2.5-flash": "G_2_5_FLASH",
    "gemini-2.5-pro": "G_2_5_PRO",
    "gemini-3.0-pro": "G_3_0_PRO",
    "gemini-3-pro-preview": "G_3_0_PRO",
    "gemini-3-flash-preview": "G_3_FLASH",  # 新增 Gemini 3 Flash 预览版
    "flash": "G_2_5_FLASH",
    "pro": "G_2_5_PRO",
    "pro3": "G_3_0_PRO",
    # 图片模型 (Imagen)
    "gemini-2.5-flash-image": "IMAGEN_3_FAST",
    "gemini-3-pro-image-preview": "IMAGEN_3",
    "gemini-3-pro-image-preview-4k": "G_3_0_PRO",  # 4K高清图片生成
    "gemini-3-pro-image-preview-2k": "G_3_0_PRO",  # 2K图片生成
}

class GenerateResponse(BaseModel):
    text: str
    model: str

class ImageGenerateRequest(BaseModel):
    prompt: str
    count: int = 1
    model: str = "gemini-2.5-flash"  # 图片生成也支持模型选择

class ImageGenerateResponse(BaseModel):
    images: List[str]  # base64编码的图片
    model: str = "gemini-2.5-flash"

class ImageEditRequest(BaseModel):
    """图片编辑请求格式（通过添加参考图作为上下文实现）"""
    prompt: str  # 编辑提示词
    image: str  # base64编码的参考图片（data:image/png;base64,... 或纯base64）
    mask: Optional[str] = None  # base64编码的蒙版图片（可选）
    model: str = "gemini-3-pro-image-preview"  # 默认使用Imagen 3
    n: int = 1  # 生成数量
    size: str = "1024x1024"
    response_format: str = "b64_json"

class GeminiImageEditRequest(BaseModel):
    """Gemini原生图片编辑格式（Google AI SDK兼容）"""
    contents: List[Dict[str, Any]]  # Gemini格式的contents
    generationConfig: Optional[Dict[str, Any]] = None
    model: str = "gemini-3-pro-image-preview"

class GeminiContent(BaseModel):
    role: str = "user"
    parts: List[Dict[str, Any]]

class GeminiRequest(BaseModel):
    contents: List[GeminiContent]
    generationConfig: Optional[Dict[str, Any]] = None

class CookieRequest(BaseModel):
    cookies: Dict[str, str]

async def init_gemini_client():
    """初始化或重新初始化Gemini客户端（带完整请求头模拟）"""
    global gemini_client

    if gemini_client:
        try:
            await gemini_client.close()
        except:
            pass

    # 创建客户端（直接传递cookies）
    gemini_client = GeminiClient()
    gemini_client.cookies = {
        "__Secure-1PSID": cookie_store.get("__Secure-1PSID"),
        "__Secure-1PSIDCC": cookie_store.get("__Secure-1PSIDCC"),
        "__Secure-1PSIDTS": cookie_store.get("__Secure-1PSIDTS")
    }

    # 设置完整的请求头（模拟真实浏览器）
    user_agent = get_random_user_agent()
    referer = get_random_referer()
    accept_language = get_random_accept_language()

    if hasattr(gemini_client, 'session') and gemini_client.session:
        gemini_client.session.headers.update({
            'User-Agent': user_agent,
            'Referer': referer,
            'Accept-Language': accept_language,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    print(f"🌐 使用 User-Agent: {user_agent[:50]}...")
    print(f"🔗 使用 Referer: {referer}")
    print(f"🌍 使用 Accept-Language: {accept_language}")

    # 不在这里调用init()，让库在第一次请求时自动调用
    # 这样避免启动时Cookie验证失败导致每次请求都重新验证
    # await gemini_client.init()
    return True

@app.on_event("startup")
async def startup_event():
    global model_limiter

    print("正在初始化Gemini客户端...")

    # 检查是否有Cookie配置
    if cookie_store.get("__Secure-1PSID"):
        try:
            await init_gemini_client()
            print("✅ Gemini客户端初始化成功!")
        except Exception as e:
            print(f"⚠️ Gemini客户端初始化失败: {e}")
            print("请通过Web界面配置有效的Cookie")
    else:
        print("⚠️ 未配置Cookie，请通过Web界面配置")

    # 初始化Redis限流器
    try:
        model_limiter = ModelRateLimiter(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=os.getenv("REDIS_PASSWORD")
        )
        if model_limiter.health_check():
            print("✅ Redis限流器初始化成功!")
        else:
            print("⚠️ Redis连接失败，限流功能将不可用")
            model_limiter = None
    except Exception as e:
        print(f"⚠️ Redis限流器初始化失败: {e}")
        model_limiter = None

@app.on_event("shutdown")
async def shutdown_event():
    if gemini_client:
        await gemini_client.close()

@app.get("/health")
async def health():
    return {"status": "ok", "client_ready": gemini_client is not None}

@app.get("/")
async def root():
    """返回Web配置页面"""
    return FileResponse(WEB_DIR / "index.html")

@app.get("/api/info")
async def api_info():
    return {
        "service": "Gemini Reverse API",
        "version": "1.0",
        "endpoints": {
            "openai": "/v1/chat/completions",
            "gemini": "/gemini/v1beta/models/{model}:generateContent",
            "simple": "/v1/generate",
            "cookie_config": "/api/cookies"
        }
    }

# ============ Cookie管理API ============

@app.get("/api/cookies/status")
async def get_cookie_status():
    """获取Cookie状态"""
    has_cookie = bool(cookie_store.get("__Secure-1PSID"))
    client_ready = gemini_client is not None

    if not has_cookie:
        return {"valid": False, "message": "未配置Cookie"}

    if not client_ready:
        return {"valid": False, "message": "Cookie已配置但客户端未初始化"}

    return {"valid": True, "message": "Cookie有效，客户端已就绪"}

@app.post("/api/cookies")
async def save_cookies(request: CookieRequest):
    """保存Cookie并重新初始化客户端"""
    global cookie_store

    cookies = request.cookies

    # 支持多种键名格式
    psid = cookies.get("__Secure-1PSID") or cookies.get("SECURE_1PSID") or cookies.get("1PSID")
    psidcc = cookies.get("__Secure-1PSIDCC") or cookies.get("SECURE_1PSIDCC") or cookies.get("1PSIDCC")
    psidts = cookies.get("__Secure-1PSIDTS") or cookies.get("SECURE_1PSIDTS") or cookies.get("1PSIDTS")

    if not psid:
        raise HTTPException(status_code=400, detail="__Secure-1PSID 是必填项")

    # 更新Cookie存储
    cookie_store["__Secure-1PSID"] = psid
    cookie_store["__Secure-1PSIDCC"] = psidcc
    cookie_store["__Secure-1PSIDTS"] = psidts

    # 重新初始化客户端
    try:
        await init_gemini_client()
        return {"success": True, "message": "Cookie保存成功，客户端已重新初始化"}
    except Exception as e:
        return {"success": False, "message": f"Cookie已保存，但初始化失败: {str(e)}"}

# ============ 生成API ============

def get_model_enum(model_name: str):
    """获取模型枚举"""
    from gemini_webapi.constants import Model
    model_key = MODEL_MAP.get(model_name, "G_2_5_FLASH")
    return getattr(Model, model_key, Model.G_2_5_FLASH)

@app.get("/api/providers")
async def list_providers():
    """
    获取所有可用的 API Key 提供商

    Returns:
        {
            "providers": [
                {"name": "default", "configured": true, "description": "主 API Key"},
                {"name": "backup", "configured": false, "description": "备用 API Key"},
                ...
            ]
        }
    """
    providers_info = []
    provider_descriptions = {
        "default": "主 API Key",
        "backup": "备用 API Key",
        "platform2": "平台2 API Key",
        "platform3": "平台3 API Key",
    }

    for name, key in API_KEY_PROVIDERS.items():
        providers_info.append({
            "name": name,
            "configured": bool(key),
            "description": provider_descriptions.get(name, f"{name} API Key")
        })

    return {
        "providers": providers_info,
        "default_provider": "default"
    }

@app.get("/api/models")
async def list_models():
    """获取支持的模型列表"""
    return {
        "models": [
            {"id": "gemini-2.5-flash", "name": "快速", "description": "快速回答，适合日常使用"},
            {"id": "gemini-2.5-pro", "name": "Pro", "description": "擅长处理高阶数学和代码问题"},
            {"id": "gemini-3.0-pro", "name": "Pro 3.0", "description": "最新Pro模型，更强的推理能力"},
        ],
        "default": "gemini-2.5-flash"
    }

@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, req: Request):
    """简单的文本生成接口（带频率限制和延迟）"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 随机延迟（模拟人类操作）
    await apply_random_delay()

    try:
        model_enum = get_model_enum(request.model)
        response = await gemini_client.generate_content(request.prompt, model=model_enum)
        return GenerateResponse(text=response.text, model=request.model)
    except Exception as e:
        error_msg = str(e)
        # 检查是否为Cookie过期错误
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        raise HTTPException(status_code=500, detail=error_msg)

class OpenAIImageRequest(BaseModel):
    """OpenAI 图片生成请求格式"""
    prompt: str
    model: str = "gemini-2.5-flash"
    n: int = 1  # 生成数量
    size: str = "1024x1024"  # 图片尺寸（目前忽略，Gemini自动决定）
    response_format: str = "b64_json"  # "url" 或 "b64_json"

class ImageEditRequest(BaseModel):
    """图片编辑请求格式（Gemini原生支持）"""
    prompt: str  # 编辑提示词
    image: str  # base64编码的原始图片
    mask: Optional[str] = None  # base64编码的蒙版图片（可选，黑色=保留，白色=编辑）
    model: str = "gemini-3-pro-image-preview"  # 图片编辑模型
    n: int = 1  # 生成数量
    size: str = "1024x1024"
    response_format: str = "b64_json"


@app.post("/v1/images/generations")
async def openai_image_generations(request: OpenAIImageRequest, req: Request):
    """OpenAI 兼容的图片生成接口（带频率限制和延迟）"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查（每小时60次）
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 模型级别限流检查（同一模型5秒间隔）
    if model_limiter:
        allowed, wait_time = model_limiter.check_and_update(request.model, client_ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"模型 {request.model} 调用过于频繁，请等待 {wait_time:.1f} 秒后重试"
            )

    # 随机延迟（模拟人类操作）
    await apply_random_delay()

    try:
        import base64
        import httpx
        import time

        # 处理提示词：强制生成图片
        prompt = request.prompt

        # 根据模型确定图片尺寸
        image_size = "2048"  # 默认2K
        if "4k" in request.model.lower():
            image_size = "4096"  # 4K高清
        elif "2k" in request.model.lower():
            image_size = "2048"  # 2K

        # 强化提示词，明确要求生成图片而不是文本描述
        # 添加明确的图片生成指令，防止模型返回文本
        enhanced_prompt = f"""Generate an actual image (not a description). Create a visual representation of: {prompt}

IMPORTANT: You must generate an image, not text. Do not describe how to create the image, just create it directly."""

        # 使用用户选择的模型
        model_enum = get_model_enum(request.model)
        response = await gemini_client.generate_content(enhanced_prompt, model=model_enum)

        # 从response.images获取生成的图片
        image_data_list = []
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    img_cookies = getattr(img, 'cookies', None) or {}
                    # 根据模型动态设置图片尺寸
                    img_url = img.url + f'=s{image_size}' if '=' not in img.url else img.url

                    async with httpx.AsyncClient(follow_redirects=True, cookies=img_cookies) as http_client:
                        resp = await http_client.get(img_url, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            image_data_list.append(image_base64)

        if not image_data_list:
            raise HTTPException(
                status_code=400,
                detail=f"未能生成图片。模型响应: {response.text[:200] if response.text else '无响应'}"
            )

        # 返回 OpenAI 格式
        data = []
        for b64_img in image_data_list[:request.n]:
            if request.response_format == "b64_json":
                data.append({"b64_json": b64_img})
            else:
                # URL 格式暂不支持，返回 base64
                data.append({"b64_json": b64_img})

        return {
            "created": int(time.time()),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # 检查是否为Cookie过期错误
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/v1/generate-images", response_model=ImageGenerateResponse)
async def generate_images(request: ImageGenerateRequest):
    """图片生成接口 - 通过generate_content获取图片"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        import base64
        import httpx
        from gemini_webapi.constants import Model

        # 处理提示词：强制生成图片
        original_prompt = request.prompt

        # 强化提示词，明确要求生成图片而不是文本描述
        # 添加明确的图片生成指令，防止模型返回文本
        prompt = f"""Generate an actual image (not a description). Create a visual representation of: {original_prompt}

IMPORTANT: You must generate an image, not text. Do not describe how to create the image, just create it directly."""

        # 使用用户选择的模型
        model_enum = get_model_enum(request.model)
        response = await gemini_client.generate_content(prompt, model=model_enum)

        # 从response.images获取生成的图片
        image_data_list = []
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    # GeneratedImage需要带cookies下载，并加上size参数获取完整图片
                    img_cookies = getattr(img, 'cookies', None) or {}
                    # 加上=s2048获取高清图片（关键！否则返回403）
                    img_url = img.url + '=s2048' if '=' not in img.url else img.url

                    async with httpx.AsyncClient(follow_redirects=True, cookies=img_cookies) as http_client:
                        resp = await http_client.get(img_url, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                            # 检测图片类型
                            content_type = resp.headers.get('content-type', 'image/png')
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                mime_type = 'image/jpeg'
                            elif 'webp' in content_type:
                                mime_type = 'image/webp'
                            else:
                                mime_type = 'image/png'
                            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            image_data_list.append(f"data:{mime_type};base64,{image_base64}")
                        else:
                            print(f"下载图片失败: {resp.status_code}, URL: {img_url[:100]}")

        if not image_data_list:
            # 没有图片生成，返回文本说明
            raise HTTPException(status_code=400, detail=f"未能生成图片。模型响应: {response.text[:200] if response.text else '无响应'}")

        return ImageGenerateResponse(images=image_data_list)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def _edit_image_handler(request: ImageEditRequest, req: Request):
    """
    图片编辑核心处理函数

    支持两种格式：
    1. Cookie方式（gemini_webapi）
    2. API Key方式（google.generativeai）
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 随机延迟（模拟人类操作）
    await apply_random_delay()

    try:
        import base64
        import httpx
        import re
        from gemini_webapi.constants import Model

        # 提取base64数据（去除data:image/...;base64,前缀）
        def extract_base64(data: str) -> str:
            if data.startswith('data:'):
                # 格式: data:image/png;base64,xxxxx
                match = re.match(r'data:image/[^;]+;base64,(.+)', data)
                if match:
                    return match.group(1)
            return data

        image_base64 = extract_base64(request.image)
        mask_base64 = extract_base64(request.mask) if request.mask else None

        # 构建编辑提示词
        # 如果提示词是中文且没有明确的编辑指令，添加前缀
        prompt = request.prompt
        if any('\u4e00' <= c <= '\u9fff' for c in prompt):
            if not any(keyword in prompt.lower() for keyword in ['edit', 'modify', 'change', 'create', '编辑', '修改', '改成']):
                prompt = f"Edit this image: {prompt}"

        # 使用Gemini API的原生files参数
        # gemini_webapi.generate_content支持files参数传递图片
        model_enum = get_model_enum(request.model)

        # 将base64图片保存为临时文件
        import tempfile
        temp_files = []
        try:
            # 保存参考图
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as f:
                f.write(base64.b64decode(image_base64))
                temp_files.append(f.name)

            # 如果有蒙版，也保存
            if mask_base64:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as f:
                    f.write(base64.b64decode(mask_base64))
                    temp_files.append(f.name)

            # 调用generate_content，使用files参数传递图片
            response = await gemini_client.generate_content(
                prompt=prompt,
                files=temp_files,
                model=model_enum
            )
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

        # 从response.images获取编辑后的图片
        image_data_list = []
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    img_cookies = getattr(img, 'cookies', None) or {}
                    img_url = img.url + '=s2048' if '=' not in img.url else img.url

                    async with httpx.AsyncClient(follow_redirects=True, cookies=img_cookies) as http_client:
                        resp = await http_client.get(img_url, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                            content_type = resp.headers.get('content-type', 'image/png')
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                mime_type = 'image/jpeg'
                            elif 'webp' in content_type:
                                mime_type = 'image/webp'
                            else:
                                mime_type = 'image/png'
                            edited_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            image_data_list.append(f"data:{mime_type};base64,{edited_image_base64}")
                        else:
                            print(f"下载编辑后的图片失败: {resp.status_code}, URL: {img_url[:100]}")

        if not image_data_list:
            raise HTTPException(status_code=400, detail=f"未能生成编辑后的图片。模型响应: {response.text[:200] if response.text else '无响应'}")

        # 返回OpenAI兼容格式
        return {
            "created": int(time.time()),
            "data": [{"url": img} for img in image_data_list]
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # 检测Cookie错误并发送Bark通知
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/v1/images/edit")
async def edit_image(request: ImageEditRequest, req: Request):
    """图片编辑接口（自定义格式）"""
    return await _edit_image_handler(request, req)

@app.post("/v1/images/edits")
async def edit_image_openai(request: ImageEditRequest, req: Request):
    """图片编辑接口（OpenAI兼容格式）"""
    return await _edit_image_handler(request, req)

@app.post("/gemini/v1beta/models/{model}:editImage")
async def edit_image_gemini_native(model: str, request: GeminiImageEditRequest, req: Request):
    """
    Gemini原生格式的图片编辑接口
    兼容Google AI SDK的调用方式

    示例请求体：
    {
        "contents": [{
            "parts": [
                {"text": "编辑提示词"},
                {"inlineData": {"mimeType": "image/png", "data": "base64..."}}
            ]
        }],
        "generationConfig": {...}
    }
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 随机延迟
    await apply_random_delay()

    try:
        import base64
        import httpx
        import tempfile
        from gemini_webapi.constants import Model

        # 从contents中提取文本和图片
        text_prompt = ""
        image_parts = []

        for content in request.contents:
            for part in content.get("parts", []):
                if "text" in part:
                    text_prompt = part["text"]
                elif "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    image_parts.append(image_data)

        if not text_prompt or not image_parts:
            raise HTTPException(status_code=400, detail="请求必须包含文本提示词和至少一张图片")

        # 保存图片为临时文件
        temp_files = []
        try:
            for img_data in image_parts:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False) as f:
                    f.write(base64.b64decode(img_data))
                    temp_files.append(f.name)

            # 使用gemini_client调用
            model_enum = get_model_enum(request.model or model)
            response = await gemini_client.generate_content(
                prompt=text_prompt,
                files=temp_files,
                model=model_enum
            )
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

        # 下载生成的图片
        image_data_list = []
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    img_cookies = getattr(img, 'cookies', None) or {}
                    img_url = img.url + '=s2048' if '=' not in img.url else img.url

                    async with httpx.AsyncClient(follow_redirects=True, cookies=img_cookies) as http_client:
                        resp = await http_client.get(img_url, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                            edited_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            image_data_list.append(edited_image_base64)

        if not image_data_list:
            raise HTTPException(status_code=400, detail=f"未能生成编辑后的图片")

        # 返回Gemini原生格式
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": img_data
                                }
                            } for img_data in image_data_list
                        ]
                    }
                }
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/v1/chat/completions")
async def chat_completions(request: dict, req: Request):
    """OpenAI兼容格式 - 支持多轮对话历史（带频率限制和延迟）"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 随机延迟（模拟人类操作）
    await apply_random_delay()

    try:
        messages = request.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="messages为空")

        # 获取模型参数
        model_name = request.get("model", "gemini-2.5-flash")
        model_enum = get_model_enum(model_name)

        # 构建完整的对话历史
        # 将 OpenAI 格式的 messages 转换为单一 prompt
        conversation_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                conversation_parts.append(f"System: {content}")
            elif role == "user":
                conversation_parts.append(f"User: {content}")
            elif role == "assistant":
                conversation_parts.append(f"Assistant: {content}")

        # 如果只有一条消息，直接使用内容
        if len(messages) == 1:
            prompt = messages[0].get("content", "")
        else:
            # 多轮对话，拼接为带角色标记的对话历史
            prompt = "\n\n".join(conversation_parts) + "\n\nAssistant:"

        response = await gemini_client.generate_content(prompt, model=model_enum)

        import time
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response.text.split()),
                "total_tokens": len(prompt.split()) + len(response.text.split())
            }
        }
    except Exception as e:
        error_msg = str(e)
        # 检查是否为Cookie过期错误
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/gemini/v1beta/models/{model}:generateContent")
async def gemini_generate_content(model: str, request: GeminiRequest, req: Request):
    """Gemini原生格式接口 - 支持文本和图片生成（带频率限制和延迟）"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")

    # 频率限制检查
    client_ip = req.client.host
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，每小时最多 {MAX_REQUESTS_PER_HOUR} 次请求"
        )

    # 随机延迟（模拟人类操作）
    await apply_random_delay()

    try:
        import base64
        import httpx

        # 提取消息内容，支持多轮对话
        if not request.contents:
            raise HTTPException(status_code=400, detail="contents为空")

        # 构建完整对话历史
        conversation_parts = []
        for content in request.contents:
            role = content.role
            text_parts = []
            for part in content.parts:
                if "text" in part:
                    text_parts.append(part["text"])
            if text_parts:
                role_label = "User" if role == "user" else "Assistant"
                conversation_parts.append(f"{role_label}: {' '.join(text_parts)}")

        # 单条消息直接使用，多条拼接
        if len(request.contents) == 1:
            prompt = ""
            for part in request.contents[0].parts:
                if "text" in part:
                    prompt += part["text"]
        else:
            prompt = "\n\n".join(conversation_parts) + "\n\nAssistant:"

        # 获取模型
        model_enum = get_model_enum(model)
        response = await gemini_client.generate_content(prompt, model=model_enum)

        # 构建返回的 parts
        parts = []

        # 添加文本部分
        if response.text:
            parts.append({"text": response.text})

        # 添加图片部分（如果有）
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    img_cookies = getattr(img, 'cookies', None) or {}
                    img_url = img.url + '=s2048' if '=' not in img.url else img.url

                    async with httpx.AsyncClient(follow_redirects=True, cookies=img_cookies) as http_client:
                        resp = await http_client.get(img_url, timeout=30.0)
                        if resp.status_code == 200:
                            image_bytes = resp.content
                            content_type = resp.headers.get('content-type', 'image/png')
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                mime_type = 'image/jpeg'
                            elif 'webp' in content_type:
                                mime_type = 'image/webp'
                            else:
                                mime_type = 'image/png'
                            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            parts.append({
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": image_base64
                                }
                            })

        # 返回Gemini原生格式
        return {
            "candidates": [{
                "content": {
                    "parts": parts,
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0
            }],
            "usageMetadata": {
                "promptTokenCount": len(prompt.split()),
                "candidatesTokenCount": len(response.text.split()) if response.text else 0,
                "totalTokenCount": len(prompt.split()) + (len(response.text.split()) if response.text else 0)
            },
            "modelVersion": model
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # 检查是否为Cookie过期错误
        if "Failed to initialize client" in error_msg or "Cookies invalid" in error_msg or "SECURE_1PSIDTS" in error_msg:
            asyncio.create_task(notify_cookie_expired())
        raise HTTPException(status_code=500, detail=error_msg)

# ===== TTS (Text-to-Speech) 音频生成 =====

class TTSRequest(BaseModel):
    """OpenAI 兼容的 TTS 请求格式"""
    model: str  # tts-1 或 tts-1-hd（映射到 Gemini TTS）
    input: str  # 要转换的文本
    voice: Optional[str] = "alloy"  # 音色（暂不支持）
    response_format: Optional[str] = "mp3"  # 音频格式
    speed: Optional[float] = 1.0  # 语速（暂不支持）
    provider: Optional[str] = "default"  # API Key 提供商 (default/backup/platform2/platform3)

@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """
    OpenAI 兼容的 TTS 接口

    支持多平台 API Key：
    - provider="default": 使用 GOOGLE_AI_API_KEY
    - provider="backup": 使用 GOOGLE_AI_API_KEY_BACKUP
    - provider="platform2": 使用 GOOGLE_AI_API_KEY_PLATFORM2
    - provider="platform3": 使用 GOOGLE_AI_API_KEY_PLATFORM3
    """
    try:
        # 获取指定平台的 API Key
        api_key = get_api_key(request.provider)

        # 导入 Google GenAI SDK
        try:
            from google import genai
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="google-genai SDK not installed. Run: pip install google-genai"
            )

        # 文本长度检查（推荐5000字符以内，约5分钟音频）
        if len(request.input) > 8000:
            raise HTTPException(
                status_code=400,
                detail=f"Text too long ({len(request.input)} chars). Recommended: < 5000 chars (5 min audio)"
            )

        # 初始化客户端
        client = genai.Client(api_key=api_key)

        # 映射模型名称（OpenAI → Gemini）
        # tts-1 → gemini-2.5-flash-preview-tts (快速)
        # tts-1-hd → gemini-2.5-pro-preview-tts (高质量)
        gemini_model = "gemini-2.5-flash-preview-tts"
        if request.model == "tts-1-hd":
            gemini_model = "gemini-2.5-pro-preview-tts"

        # 调用 Gemini TTS (使用最简单的配置)
        try:
            response = client.models.generate_content(
                model=gemini_model,
                contents=request.input,
                config={
                    'response_modalities': ['AUDIO']
                }
            )
        except Exception as e:
            error_msg = str(e)
            # 检查是否是模型不可用错误
            if 'model_not_found' in error_msg or '无可用渠道' in error_msg:
                raise HTTPException(
                    status_code=503,
                    detail="TTS功能暂时不可用。当前API Key不支持Gemini TTS模型,需要使用Google AI Studio官方API Key。"
                )
            raise

        # 提取音频数据
        if not response.candidates or not response.candidates[0].content:
            raise HTTPException(status_code=500, detail="No audio generated")

        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # 返回音频（PCM 格式）
        # 注意：Gemini 返回 PCM，如需 MP3 需要转换
        return Response(
            content=audio_data,
            media_type="audio/wav",  # PCM 24kHz 16bit
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8100))
    uvicorn.run(app, host="0.0.0.0", port=port)
