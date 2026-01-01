#!/usr/bin/env python3
"""
Provider所有模型测试脚本
验证4个可用模型：gemini-2.5-flash, gemini-3-flash-preview, gemini-flash-latest, gemma-3-27b-it
"""
import httpx
import os
from dotenv import load_dotenv
import time

# 加载环境变量
load_dotenv()

PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "http://82.29.54.80:13001/proxy/gemini-hk/v1beta")
PROVIDER_AUTH_TOKEN = os.getenv("PROVIDER_AUTH_TOKEN", "zxc6545398")

# 测试模型列表
MODELS = [
    ("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("gemini-3-flash-preview", "Gemini 3.0 Flash Preview"),
    ("gemini-flash-latest", "Gemini Flash Latest"),
    ("gemma-3-27b-it", "Gemma 3 27B IT"),
]

def test_model(model_id, model_name, prompt="你好，请用中文回答"):
    """测试单个模型"""
    try:
        url = f"{PROVIDER_BASE_URL}/models/{model_id}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {PROVIDER_AUTH_TOKEN}"
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        start_time = time.time()

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            elapsed = time.time() - start_time
            data = response.json()

            # 提取响应文本
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                token_count = data.get("usageMetadata", {}).get("totalTokenCount", 0)

                return {
                    "status": "success",
                    "text": text,
                    "tokens": token_count,
                    "elapsed": elapsed
                }
            else:
                return {
                    "status": "error",
                    "error": "响应格式异常"
                }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def main():
    print("=" * 70)
    print("🧪 Provider模式 - 全模型测试")
    print("=" * 70)
    print(f"Provider: {PROVIDER_BASE_URL}")
    print(f"测试模型数: {len(MODELS)}")
    print("=" * 70)

    results = []

    for model_id, model_name in MODELS:
        print(f"\n📝 测试模型: {model_name} ({model_id})")

        result = test_model(model_id, model_name)
        results.append((model_id, model_name, result))

        if result["status"] == "success":
            print(f"   ✅ 成功")
            print(f"   响应: {result['text'][:60]}...")
            print(f"   Token: {result['tokens']}")
            print(f"   耗时: {result['elapsed']:.2f}秒")
        else:
            print(f"   ❌ 失败: {result['error']}")

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)

    success_count = sum(1 for _, _, r in results if r["status"] == "success")
    fail_count = len(results) - success_count

    print(f"\n✅ 成功: {success_count}/{len(results)}")
    print(f"❌ 失败: {fail_count}/{len(results)}")

    if success_count > 0:
        print("\n可用模型列表:")
        for model_id, model_name, result in results:
            if result["status"] == "success":
                print(f"  • {model_name:30s} ({model_id})")
                print(f"    - Token: {result['tokens']:4d}  耗时: {result['elapsed']:.2f}秒")

    print("\n" + "=" * 70)

    return success_count, fail_count

if __name__ == "__main__":
    main()
