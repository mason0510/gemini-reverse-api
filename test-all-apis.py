#!/usr/bin/env python3
"""
Gemini Reverse API - 完整功能测试
功能: 测试所有API端点和模型
关键词: test, api, gemini, chat, image, tts
"""
import requests
import json
import base64
import datetime
import os

API_URL = "https://google-api.aihang365.com"
os.environ['NO_PROXY'] = '*'

TEXT_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-pro"]
IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]

results = {"pass": 0, "fail": 0}

def sep():
    print("-" * 60)

def test(name):
    print(f"\n📤 {name}")
    sep()

def ok(code):
    results["pass"] += 1
    print(f"✅ HTTP {code}")

def fail(code, msg=""):
    results["fail"] += 1
    print(f"❌ HTTP {code} {msg[:100]}")

print("🚀 Gemini Reverse API 测试")
print(f"地址: {API_URL}")
print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== 1. 健康检查 ====================
sep()
print("【1. 健康检查】")
sep()

test("GET /health")
try:
    r = requests.get(f"{API_URL}/health", timeout=5)
    ok(r.status_code) if r.status_code == 200 else fail(r.status_code)
    print(f"响应: {r.json()}")
except Exception as e:
    fail(0, str(e))

test("GET /api/cookies/status")
try:
    r = requests.get(f"{API_URL}/api/cookies/status", timeout=5)
    ok(r.status_code) if r.status_code == 200 else fail(r.status_code)
    d = r.json()
    print(f"有效: {d.get('valid')} | {d.get('message')}")
except Exception as e:
    fail(0, str(e))

# ==================== 2. 文本模型测试 ====================
sep()
print("【2. 文本生成模型】")
sep()

for model in TEXT_MODELS:
    test(f"POST /v1/chat/completions [{model}]")
    try:
        r = requests.post(
            f"{API_URL}/v1/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": "1+1=?"}]},
            timeout=60
        )
        if r.status_code == 200:
            ok(r.status_code)
            text = r.json()['choices'][0]['message']['content']
            print(f"回复: {text[:80]}...")
        else:
            fail(r.status_code, r.text)
    except Exception as e:
        fail(0, str(e))

# ==================== 3. 图片模型测试 ====================
sep()
print("【3. 图片生成模型】")
sep()

for model in IMAGE_MODELS:
    test(f"POST /v1/generate-images [{model}] (base64)")
    try:
        r = requests.post(
            f"{API_URL}/v1/generate-images",
            json={"prompt": "a red apple", "model": model, "count": 1},
            timeout=120
        )
        if r.status_code == 200:
            ok(r.status_code)
            imgs = r.json().get('images', [])
            if imgs:
                size = len(imgs[0])
                print(f"图片: {len(imgs)}张, {size//1024}KB (base64)")
            else:
                print("图片: 0张")
        else:
            fail(r.status_code, r.text)
    except Exception as e:
        fail(0, str(e))

test("POST /v1/generate-images (response_type=url)")
try:
    r = requests.post(
        f"{API_URL}/v1/generate-images",
        json={"prompt": "sunset over ocean", "count": 1, "response_type": "url"},
        timeout=120
    )
    if r.status_code == 200:
        ok(r.status_code)
        imgs = r.json().get('images', [])
        if imgs and imgs[0].startswith("https://"):
            print(f"R2 URL: {imgs[0][:60]}...")
        else:
            print("未返回URL")
    else:
        fail(r.status_code, r.text)
except Exception as e:
    fail(0, str(e))

# ==================== 4. API格式测试 ====================
sep()
print("【4. API格式兼容性】")
sep()

test("POST /v1/generate (简化格式)")
try:
    r = requests.post(
        f"{API_URL}/v1/generate",
        json={"prompt": "hello", "model": "gemini-2.5-flash"},
        timeout=30
    )
    ok(r.status_code) if r.status_code == 200 else fail(r.status_code, r.text)
    if r.status_code == 200:
        print(f"回复: {r.json().get('text', '')[:60]}...")
except Exception as e:
    fail(0, str(e))

test("POST /gemini/v1beta/models/...:generateContent (Gemini原生)")
try:
    r = requests.post(
        f"{API_URL}/gemini/v1beta/models/gemini-2.5-flash:generateContent",
        json={"contents": [{"role": "user", "parts": [{"text": "hi"}]}]},
        timeout=30
    )
    ok(r.status_code) if r.status_code == 200 else fail(r.status_code, r.text)
    if r.status_code == 200:
        text = r.json()['candidates'][0]['content']['parts'][0]['text']
        print(f"回复: {text[:60]}...")
except Exception as e:
    fail(0, str(e))

# ==================== 5. 测试总结 ====================
sep()
print("【测试总结】")
sep()

total = results["pass"] + results["fail"]
rate = results["pass"] / total * 100 if total > 0 else 0

print(f"""
通过: {results["pass"]}/{total} ({rate:.0f}%)
失败: {results["fail"]}/{total}

支持的模型:
  文本: {', '.join(TEXT_MODELS)}
  图片: {', '.join(IMAGE_MODELS)}

API端点:
  /v1/chat/completions     - OpenAI格式
  /v1/generate             - 简化格式
  /v1/generate-images      - 图片生成
  /gemini/v1beta/models/*  - Gemini原生
""")
sep()
print("测试完成!")
