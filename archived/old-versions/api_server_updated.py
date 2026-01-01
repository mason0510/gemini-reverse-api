from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gemini_webapi import GeminiClient
import os
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

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

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.5-flash"

class GenerateResponse(BaseModel):
    text: str
    model: str

class ImageGenerateRequest(BaseModel):
    prompt: str
    count: int = 1

class ImageGenerateResponse(BaseModel):
    images: List[str]  # base64编码的图片
    model: str = "gemini-2.5-flash"

class GeminiContent(BaseModel):
    role: str = "user"
    parts: List[Dict[str, Any]]

class GeminiRequest(BaseModel):
    contents: List[GeminiContent]
    generationConfig: Optional[Dict[str, Any]] = None

class CookieRequest(BaseModel):
    cookies: Dict[str, str]

async def init_gemini_client():
    """初始化或重新初始化Gemini客户端"""
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

    # 注册 Claude 兼容路由
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
    """返回Web配置页面"""
    return FileResponse(WEB_DIR / "index.html")

@app.get("/api/info")
async def api_info():
    return {
        "service": "Gemini Reverse API",
        "version": "2.0",
        "endpoints": {
            "openai": "/v1/chat/completions",
            "gemini": "/gemini/v1beta/models/{model}:generateContent",
            "claude": "/v1/messages",
            "simple": "/v1/generate",
            "cookie_config": "/api/cookies"
        },
        "claude_code": {
            "description": "Claude Code CLI 兼容",
            "models": {
                "gemini-3-flash-preview-cc": "Haiku (小模型)",
                "gemini-3-pro-cc": "Sonnet/Opus (大模型)"
            },
            "config": {
                "ANTHROPIC_BASE_URL": "https://google-api.aihang365.com",
                "ANTHROPIC_API_KEY": "any-key",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gemini-3-flash-preview-cc",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "gemini-3-pro-cc",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "gemini-3-pro-cc"
            }
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

@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """简单的文本生成接口"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        response = await gemini_client.generate_content(request.prompt)
        return GenerateResponse(text=response.text, model=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/generate-images", response_model=ImageGenerateResponse)
async def generate_images(request: ImageGenerateRequest):
    """图片生成接口 - 通过generate_content获取图片"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        import base64
        import httpx
        from gemini_webapi.constants import Model

        # 使用支持图片生成的模型
        response = await gemini_client.generate_content(
            request.prompt,
            model=Model.G_2_5_FLASH
        )

        # 从response.images获取生成的图片
        image_data_list = []
        if response.images:
            for img in response.images:
                if hasattr(img, 'url') and img.url:
                    # GeneratedImage需要带cookies下载
                    cookies = getattr(img, 'cookies', None) or {}
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.get(
                            img.url,
                            cookies=cookies,
                            follow_redirects=True,
                            timeout=30.0
                        )
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
                            print(f"下载图片失败: {resp.status_code}, URL: {img.url[:100]}")

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

@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    """OpenAI兼容格式"""
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
                "message": {
                    "role": "assistant",
                    "content": response.text
                },
                "finish_reason": "stop"
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gemini/v1beta/models/{model}:generateContent")
async def gemini_generate_content(model: str, request: GeminiRequest):
    """Gemini原生格式接口"""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini客户端未初始化，请先配置Cookie")
    try:
        # 提取最后一条消息的文本
        if not request.contents:
            raise HTTPException(status_code=400, detail="contents为空")

        last_content = request.contents[-1]
        prompt = ""
        for part in last_content.parts:
            if "text" in part:
                prompt += part["text"]

        response = await gemini_client.generate_content(prompt)

        # 返回Gemini原生格式
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": response.text
                    }],
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

# ============ NexusAI Google Gemini 类型兼容路由 ============
@app.post("/v1beta/models/{model}:generateContent")
@app.post("/v1/models/{model}:generateContent")
async def nexusai_gemini_generate_content(model: str, request: GeminiRequest):
    """NexusAI Google Gemini类型兼容接口"""
    return await gemini_generate_content(model, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
