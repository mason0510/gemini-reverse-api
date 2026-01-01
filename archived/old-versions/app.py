import asyncio
import os
from gemini_webapi import GeminiClient

async def main():
    print("=== Gemini Reverse API Service ===")
    
    # 创建客户端
    client = GeminiClient()
    
    # 设置cookies
    client.cookies = {
        "__Secure-1PSID": os.getenv("SECURE_1PSID"),
        "__Secure-1PSIDCC": os.getenv("SECURE_1PSIDCC"),
        "__Secure-1PSIDTS": os.getenv("SECURE_1PSIDTS")
    }
    
    print("正在初始化Gemini客户端...")
    
    try:
        await client.init()
        print("✅ Gemini客户端初始化成功!")
        
        # 测试对话
        print("\n发送测试消息...")
        response = await client.generate_content("你好,请用一句话介绍你自己")
        print(f"\n✅ 响应成功:")
        print(f"{response.text}")
        
        await client.close()
        print("\n✅ 测试完成!")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(main())
