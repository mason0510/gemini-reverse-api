#!/usr/bin/env python3
"""
Provider模式测试脚本
测试直接使用Provider API（官方格式）而非Cookie方式
"""
import httpx
import os
from dotenv import load_dotenv
import json

# 加载环境变量
load_dotenv()

PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "http://82.29.54.80:13001/proxy/gemini-hk/v1beta")
PROVIDER_AUTH_TOKEN = os.getenv("PROVIDER_AUTH_TOKEN", "zxc6545398")
PROVIDER_DEFAULT_MODEL = os.getenv("PROVIDER_DEFAULT_MODEL", "gemini-3-flash-preview")

def test_provider_api():
    """测试Provider API"""
    print("=" * 60)
    print("🧪 Gemini Provider API 测试")
    print("=" * 60)

    # 测试用例
    tests = [
        {
            "name": "简单问答",
            "prompt": "Hi, 用中文回答",
            "expected_keywords": []
        },
        {
            "name": "代码生成",
            "prompt": "写一个Python函数计算斐波那契数列",
            "expected_keywords": ["def", "fibonacci"]
        },
        {
            "name": "长文本处理",
            "prompt": "详细解释什么是Docker容器技术",
            "expected_keywords": ["Docker", "容器"]
        }
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n📝 测试: {test['name']}")
        print(f"   提示词: {test['prompt']}")

        try:
            # 构造请求
            url = f"{PROVIDER_BASE_URL}/models/{PROVIDER_DEFAULT_MODEL}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PROVIDER_AUTH_TOKEN}"
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": test['prompt']}
                        ]
                    }
                ]
            }

            # 发送请求
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # 提取响应文本
                if "candidates" in data and len(data["candidates"]) > 0:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    token_count = data.get("usageMetadata", {}).get("totalTokenCount", 0)

                    print(f"   ✅ 成功")
                    print(f"   响应: {text[:100]}...")
                    print(f"   Token: {token_count}")

                    # 检查关键词
                    if test['expected_keywords']:
                        found = all(kw in text for kw in test['expected_keywords'])
                        if found:
                            print(f"   关键词验证: ✅ 全部匹配")
                        else:
                            print(f"   关键词验证: ⚠️  部分缺失")

                    passed += 1
                else:
                    print(f"   ❌ 响应格式异常")
                    print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    failed += 1

        except Exception as e:
            print(f"   ❌ 失败: {str(e)}")
            failed += 1

    # 总结
    print("\n" + "=" * 60)
    print(f"测试结果: ✅ {passed} 个通过, ❌ {failed} 个失败")
    print("=" * 60)

    return passed, failed

if __name__ == "__main__":
    test_provider_api()
