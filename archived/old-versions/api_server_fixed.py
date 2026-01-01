from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gemini_webapi import GeminiClient
import os
import asyncio
import re
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

app = FastAPI(title="Gemini Reverse API")

WEB_DIR = Path(__file__).parent / "web"

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


def create_image_prompt(user_prompt: str) -> str:
    return f"""Generate an actual image (not a description).
Create a visual representation of: {user_prompt}

IMPORTANT: You must generate an image, not text. Output only the image."""


def generate_image_filename(prompt: str, index: int = 0) -> str:
    """根据prompt生成有意义的文件名，便于grep搜索"""
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
    """上传图片到R2并返回公共URL"""
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
    image: Optional[str] = None  # 参考图base64，用于图片编辑

class ImageGenerateResponse(BaseModel):
    images: List[str]
    model: str = "gemini-2.5-flash"

# 支持的模型列表
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

@app.on_event("startup")
async def startup_event():
    print("正在初始化Gemini客户端...")
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

@app.on_event("shutdown")
async def shutdown_event():
    if gemini_client:
        await gemini_client.close()

@app.get("/health")
async def health():
    return {"status": "ok", "client_ready": gemini_client is not None}

@app.get("/")
async def root():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/api/info")
async def api_info():
    return {
        "service": "Gemini Reverse API",
        "version": "2.1",
        "endpoints": {
            "openai": "/v1/chat/completions",
            "gemini": "/gemini/v1beta/models/{model}:generateContent",
            "claude": "/v1/messages",
            "simple": "/v1/generate",
            "images": "/v1/generate-images",
            "cookie_config": "/api/cookies"
        },
        "image_generation": {
            "response_type": ["base64", "url"],
            "default": "base64",
            "note": "type=url时上传到R2返回公共URL"
        }
    }

@app.get("/api/models")
async def get_models():
    """获取支持的模型列表"""
    all_models = SUPPORTED_MODELS["text"] + SUPPORTED_MODELS["image"]
    return {
        "models": all_models,
        "categories": SUPPORTED_MODELS,
        "default": "gemini-2.5-flash"
    }

@app.get("/v1/models")
async def get_models_openai():
    """OpenAI兼容的模型列表"""
    all_models = SUPPORTED_MODELS["text"] + SUPPORTED_MODELS["image"]
    return {
        "object": "list",
        "data": [{"id": m["id"], "object": "model", "owned_by": "google"} for m in all_models]
    }

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

@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        response = await gemini_client.generate_content(request.prompt)
        return GenerateResponse(text=response.text, model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/generate-images", response_model=ImageGenerateResponse)
async def generate_images(request: ImageGenerateRequest):
    """图片生成接口 - 支持base64/url返回格式，支持参考图编辑"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        import base64 as b64
        import httpx
        from gemini_webapi.constants import Model
        from PIL import Image as PILImage
        import io

        # 如果有参考图，使用图片编辑模式
        if request.image:
            # 解析base64图片
            image_data = request.image
            if image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            image_bytes = b64.b64decode(image_data)

            # 转为PIL Image
            pil_image = PILImage.open(io.BytesIO(image_bytes))

            # 使用generate_content传入图片和提示词
            response = await gemini_client.generate_content(
                request.prompt,
                image=pil_image,
                model=Model.G_2_5_FLASH
            )
        else:
            # 纯文字生图模式
            enhanced_prompt = create_image_prompt(request.prompt)
            response = await gemini_client.generate_content(
                enhanced_prompt,
                model=Model.G_2_5_FLASH
            )

        image_data_list = []
        if response.images:
            for idx, img in enumerate(response.images):
                if hasattr(img, 'url') and img.url:
                    cookies = getattr(img, 'cookies', {}) or {}
                    download_url = img.url
                    if '=s' not in download_url:
                        download_url = f"{img.url}=s4096"

                    async with httpx.AsyncClient(follow_redirects=True, cookies=cookies, timeout=60.0) as http_client:
                        resp = await http_client.get(download_url)
                        if resp.status_code == 200:
                            image_bytes = resp.content

                            if request.response_type == "url":
                                filename = generate_image_filename(request.prompt, idx)
                                try:
                                    url = await upload_to_r2(image_bytes, filename)
                                    image_data_list.append(url)
                                    print(f"✅ 图片已上传: {filename}")
                                except Exception as e:
                                    print(f"❌ R2上传失败: {e}, 回退到base64")
                                    image_base64 = b64.b64encode(image_bytes).decode('utf-8')
                                    image_data_list.append(f"data:image/png;base64,{image_base64}")
                            else:
                                content_type = resp.headers.get('content-type', 'image/png')
                                if 'jpeg' in content_type or 'jpg' in content_type:
                                    mime_type = 'image/jpeg'
                                elif 'webp' in content_type:
                                    mime_type = 'image/webp'
                                else:
                                    mime_type = 'image/png'
                                image_base64 = b64.b64encode(image_bytes).decode('utf-8')
                                image_data_list.append(f"data:{mime_type};base64,{image_base64}")
                        else:
                            print(f"下载图片失败: {resp.status_code}, URL: {img.url[:100]}")

        if not image_data_list:
            raise HTTPException(status_code=400, detail=f"未能生成图片。模型响应: {response.text[:200] if response.text else '无响应'}")

        return ImageGenerateResponse(images=image_data_list)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/images/generations", response_model=ImageGenerateResponse)
async def images_generations(request: ImageGenerateRequest):
    """OpenAI兼容的图片生成接口（别名）"""
    return await generate_images(request)

@app.post("/v1/images/edit", response_model=ImageGenerateResponse)
@app.post("/v1/images/edits", response_model=ImageGenerateResponse)
async def images_edit(request: ImageGenerateRequest):
    """图片编辑接口 - 基于参考图生成新图片"""
    if not request.image:
        raise HTTPException(status_code=400, detail="图片编辑需要提供image参数(base64)")
    return await generate_images(request)

@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        messages = request.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="messages为空")
        prompt = messages[-1].get("content", "")
        response = await gemini_client.generate_content(prompt)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gemini/v1beta/models/{model}:generateContent")
async def gemini_generate_content(model: str, request: GeminiRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        if not request.contents:
            raise HTTPException(status_code=400, detail="contents为空")
        last_content = request.contents[-1]
        prompt = ""
        for part in last_content.parts:
            if "text" in part:
                prompt += part["text"]
        response = await gemini_client.generate_content(prompt)
        return {
            "candidates": [{
                "content": {
                    "parts": [{"text": response.text}],
                    "role": "model"
                },
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1beta/models/{model}:generateContent")
@app.post("/v1/models/{model}:generateContent")
async def nexusai_gemini_generate_content(model: str, request: GeminiRequest):
    return await gemini_generate_content(model, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
