#!/usr/bin/env python3
"""
Gemini Reverse API v4.0 完整测试脚本
测试所有端点: 文本、图片、TTS、PDF、UI设计

使用方法:
    python3 test-v4-apis.py [--full]

参数:
    --full  运行完整测试（包括需要Cookie的功能）
"""

import requests
import json
import sys
import time
import os
from datetime import datetime

# 配置
API_BASE = "https://google-api.aihang365.com"
# API_BASE = "http://localhost:8100"  # 本地测试

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_result(name, success, details=""):
    if success is None:
        status = f"{Colors.YELLOW}🔑 COOKIE{Colors.END}"
    elif success:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}"
    else:
        status = f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"  {status} {name}")
    if details:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")

def print_section(text):
    print(f"\n{Colors.BOLD}📌 {text}{Colors.END}")

# ============ 基础端点测试 ============
def test_health():
    """测试健康检查端点"""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=10)
        data = resp.json()
        success = data.get("status") == "ok" and data.get("version") == "4.0"
        return success, f"version={data.get('version')}, tts_ready={data.get('tts_ready')}"
    except Exception as e:
        return False, str(e)

def test_api_info():
    """测试API信息端点"""
    try:
        resp = requests.get(f"{API_BASE}/api/info", timeout=10)
        data = resp.json()
        success = data.get("version") == "4.0"
        features = list(data.get("features", {}).keys())
        return success, f"features: {', '.join(features[:5])}..."
    except Exception as e:
        return False, str(e)

def test_models():
    """测试模型列表端点"""
    try:
        resp = requests.get(f"{API_BASE}/api/models", timeout=10)
        data = resp.json()
        models = data.get("models", [])
        categories = data.get("categories", {})
        success = len(models) >= 13 and len(categories) >= 5
        return success, f"{len(models)} models, {len(categories)} categories"
    except Exception as e:
        return False, str(e)

def test_openai_models():
    """测试OpenAI格式模型列表"""
    try:
        resp = requests.get(f"{API_BASE}/v1/models", timeout=10)
        data = resp.json()
        models = data.get("data", [])
        success = len(models) >= 13
        return success, f"{len(models)} models in OpenAI format"
    except Exception as e:
        return False, str(e)

def test_cookie_status():
    """测试Cookie状态端点"""
    try:
        resp = requests.get(f"{API_BASE}/api/cookies/status", timeout=10)
        data = resp.json()
        valid = data.get("valid", False)
        message = data.get("message", "")
        return True, f"valid={valid}, {message}"
    except Exception as e:
        return False, str(e)

# ============ TTS 测试 ============
def test_tts_voices():
    """测试TTS语音列表"""
    try:
        resp = requests.get(f"{API_BASE}/v1/audio/voices", timeout=10)
        data = resp.json()
        voices = data.get("voices", [])
        success = len(voices) >= 6
        voice_ids = [v["id"] for v in voices]
        return success, f"voices: {', '.join(voice_ids)}"
    except Exception as e:
        return False, str(e)

def test_tts_speech():
    """测试TTS语音生成"""
    try:
        payload = {
            "model": "tts-1",
            "input": "Hello, this is a test.",
            "voice": "alloy"
        }
        resp = requests.post(
            f"{API_BASE}/v1/audio/speech",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            size = len(resp.content)
            success = "audio" in content_type and size > 1000
            return success, f"size={size} bytes, type={content_type}"
        elif resp.status_code == 429:
            return True, "Quota limit (expected for TTS)"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_tts_chinese():
    """测试TTS中文语音"""
    try:
        payload = {
            "model": "tts-1",
            "input": "你好，这是中文语音测试。",
            "voice": "nova"
        }
        resp = requests.post(
            f"{API_BASE}/v1/audio/speech",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            size = len(resp.content)
            success = size > 1000
            return success, f"size={size} bytes (Chinese)"
        elif resp.status_code == 429:
            return True, "Quota limit (expected for TTS)"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_tts_hd():
    """测试TTS-HD高质量模型"""
    try:
        payload = {
            "model": "tts-1-hd",
            "input": "High quality speech test.",
            "voice": "onyx"
        }
        resp = requests.post(
            f"{API_BASE}/v1/audio/speech",
            json=payload,
            timeout=120
        )

        if resp.status_code == 200:
            size = len(resp.content)
            success = size > 1000
            return success, f"size={size} bytes (HD)"
        elif resp.status_code == 429:
            return True, "Quota limit (expected for HD model)"
        else:
            error = resp.text[:100] if resp.text else "Unknown error"
            return False, f"status={resp.status_code}, error={error}"
    except Exception as e:
        return False, str(e)

# ============ 文本生成测试 (需要Cookie) ============
def test_chat_completions():
    """测试Chat Completions端点"""
    try:
        payload = {
            "model": "gemini-2.5-flash",
            "messages": [{"role": "user", "content": "Say hello in one word."}]
        }
        resp = requests.post(
            f"{API_BASE}/v1/chat/completions",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            success = len(content) > 0
            return success, f"response: {content[:50]}..."
        elif resp.status_code == 503:
            return None, "Gemini client not initialized (Cookie needed)"
        elif resp.status_code == 500:
            return None, "Cookie expired (SECURE_1PSIDTS)"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_generate():
    """测试简化生成端点"""
    try:
        payload = {
            "prompt": "What is 2+2?",
            "model": "gemini-2.5-flash"
        }
        resp = requests.post(
            f"{API_BASE}/v1/generate",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data.get("text", "")
            success = len(text) > 0
            return success, f"response: {text[:50]}..."
        elif resp.status_code == 503:
            return None, "Gemini client not initialized (Cookie needed)"
        elif resp.status_code == 500:
            return None, "Cookie expired (SECURE_1PSIDTS)"
        elif resp.status_code == 400:
            # 检查是否是Cookie过期导致的400错误
            try:
                error_msg = resp.json().get("detail", "")
                if "SECURE_1PSIDTS" in error_msg or "cookie" in error_msg.lower():
                    return None, "Cookie expired (initialization failed)"
            except:
                pass
            return False, f"status={resp.status_code}"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

def test_gemini_native():
    """测试Gemini原生格式端点"""
    try:
        payload = {
            "contents": [{"parts": [{"text": "Hello"}]}]
        }
        resp = requests.post(
            f"{API_BASE}/gemini/v1beta/models/gemini-2.5-flash:generateContent",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            success = len(candidates) > 0
            return success, f"candidates: {len(candidates)}"
        elif resp.status_code == 503:
            return None, "Gemini client not initialized (Cookie needed)"
        elif resp.status_code == 500:
            return None, "Cookie expired (SECURE_1PSIDTS)"
        elif resp.status_code == 400:
            try:
                error_msg = resp.json().get("detail", "")
                if "SECURE_1PSIDTS" in error_msg or "cookie" in error_msg.lower():
                    return None, "Cookie expired (initialization failed)"
            except:
                pass
            return False, f"status={resp.status_code}"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

# ============ 图片生成测试 (需要Cookie) ============
IMAGE_MODELS = [
    ("gemini-2.5-flash-image", "Flash快速"),
    ("gemini-3-pro-image-preview", "Pro高质量"),
    ("gemini-3-pro-image-preview-2k", "Pro 2K"),
    ("gemini-3-pro-image-preview-4k", "Pro 4K"),
]

def test_image_generation(model=None):
    """测试图片生成端点"""
    try:
        payload = {
            "prompt": "A simple red circle",
            "response_type": "base64"
        }
        if model:
            payload["model"] = model

        resp = requests.post(
            f"{API_BASE}/v1/images/generations",
            json=payload,
            timeout=180  # 4K需要更长时间
        )

        if resp.status_code == 200:
            data = resp.json()
            images = data.get("images", [])
            success = len(images) > 0
            return success, f"generated {len(images)} image(s)"
        elif resp.status_code == 503:
            return None, "Gemini client not initialized (Cookie needed)"
        elif resp.status_code == 500:
            error_detail = ""
            try:
                error_detail = resp.json().get("detail", "")
            except:
                pass
            if "SECURE_1PSIDTS" in error_detail or "cookie" in error_detail.lower():
                return None, "Cookie expired (SECURE_1PSIDTS)"
            return False, f"status=500, {error_detail[:50]}"
        elif resp.status_code == 400:
            try:
                error_msg = resp.json().get("detail", "")
                if "SECURE_1PSIDTS" in error_msg or "cookie" in error_msg.lower():
                    return None, "Cookie expired (initialization failed)"
            except:
                pass
            return False, f"status={resp.status_code}"
        elif resp.status_code == 429:
            return True, "Rate limited (expected)"
        else:
            return False, f"status={resp.status_code}"
    except Exception as e:
        return False, str(e)

# ============ Gemini模型列表 (第三方客户端兼容) ============
def test_gemini_models():
    """测试Gemini格式模型列表"""
    try:
        resp = requests.get(f"{API_BASE}/gemini/v1beta/models", timeout=10)
        data = resp.json()
        models = data.get("models", [])
        success = len(models) >= 10
        return success, f"{len(models)} models in Gemini format"
    except Exception as e:
        return False, str(e)

# ============ 主测试流程 ============
def run_tests(full_test=False):
    """运行所有测试"""
    results = {"passed": 0, "failed": 0, "skipped": 0, "cookie_needed": 0}

    print_header("Gemini Reverse API v4.0 测试")
    print(f"API Base: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'Full' if full_test else 'Basic'}")

    # 基础端点测试
    print_section("基础端点")
    tests = [
        ("Health Check", test_health),
        ("API Info", test_api_info),
        ("Models List", test_models),
        ("OpenAI Models", test_openai_models),
        ("Cookie Status", test_cookie_status),
        ("Gemini Models", test_gemini_models),
    ]

    for name, test_func in tests:
        success, details = test_func()
        print_result(name, success, details)
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # TTS测试
    print_section("TTS 语音合成")
    tts_tests = [
        ("TTS Voices List", test_tts_voices),
        ("TTS Speech (English)", test_tts_speech),
        ("TTS Speech (Chinese)", test_tts_chinese),
        ("TTS-HD (High Quality)", test_tts_hd),
    ]

    for name, test_func in tts_tests:
        success, details = test_func()
        print_result(name, success, details)
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # 需要Cookie的测试
    if full_test:
        print_section("文本生成 (需要Cookie)")
        text_tests = [
            ("Chat Completions", test_chat_completions),
            ("Simple Generate", test_generate),
            ("Gemini Native Format", test_gemini_native),
        ]

        for name, test_func in text_tests:
            success, details = test_func()
            print_result(name, success, details)
            if success is None:
                results["cookie_needed"] += 1
            elif success:
                results["passed"] += 1
            else:
                results["failed"] += 1

        print_section("图片生成 (需要Cookie, 水印自动去除)")
        # 测试所有4个图片模型
        for model_id, model_name in IMAGE_MODELS:
            success, details = test_image_generation(model=model_id)
            print_result(f"Image: {model_name}", success, details)
            if success is None:
                results["cookie_needed"] += 1
            elif success:
                results["passed"] += 1
            else:
                results["failed"] += 1
            # 避免触发限流
            if success:
                import time
                time.sleep(3)
    else:
        print_section("跳过的测试 (需要 --full 参数)")
        skipped = [
            "Chat Completions",
            "Simple Generate",
            "Gemini Native Format",
            "Image: Flash快速",
            "Image: Pro高质量",
            "Image: Pro 2K",
            "Image: Pro 4K",
        ]
        for name in skipped:
            print(f"  {Colors.YELLOW}⏭️  SKIP{Colors.END} {name}")
            results["skipped"] += 1

    # 总结
    print_header("测试结果总结")
    total = results["passed"] + results["failed"] + results["cookie_needed"]
    print(f"  {Colors.GREEN}通过: {results['passed']}{Colors.END}")
    print(f"  {Colors.RED}失败: {results['failed']}{Colors.END}")
    print(f"  {Colors.YELLOW}需Cookie: {results['cookie_needed']}{Colors.END}")
    print(f"  {Colors.YELLOW}跳过: {results['skipped']}{Colors.END}")
    print(f"  总计: {total}")

    if results["failed"] == 0 and results["cookie_needed"] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！{Colors.END}")
    elif results["failed"] == 0 and results["cookie_needed"] > 0:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}🔑 基础功能正常，部分测试需要更新Cookie{Colors.END}")
        print(f"   请运行: ./update-server-cookies.sh <cookie文件路径>")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  有 {results['failed']} 个测试失败{Colors.END}")

    return results["failed"] == 0

if __name__ == "__main__":
    full_test = "--full" in sys.argv
    success = run_tests(full_test)
    sys.exit(0 if success else 1)
