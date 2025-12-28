#!/usr/bin/env python3
# 功能: 从BitBrowser自动提取Gemini Cookie并部署到服务器
# 关键词: cookie, bitbrowser, auto-extract, gemini, 自动提取

import sqlite3
import subprocess
import base64
import os
import sys
from pathlib import Path
import hashlib
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
import datetime

class BitBrowserCookieExtractor:
    def __init__(self):
        self.cookie_db_path = Path.home() / "Library/Application Support/BitBrowser/BrowserCache/01b343e0255140dc8d9a890f61cd3657/Default/Cookies"
        self.encryption_key = None

    def get_encryption_key(self):
        """从macOS Keychain获取加密密钥"""
        try:
            # 先尝试BitBrowser Safe Storage
            result = subprocess.run(
                ['security', 'find-generic-password', '-w', '-s', 'BitBrowser Safe Storage', '-a', 'BitBrowser'],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # 回退到Chrome Safe Storage
                result = subprocess.run(
                    ['security', 'find-generic-password', '-w', '-s', 'Chrome Safe Storage'],
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:
                raise Exception("无法从Keychain获取加密密钥")

            # 密钥是base64编码的
            password = result.stdout.strip()

            # 使用PBKDF2派生实际的AES密钥
            # Chromium使用固定的salt "saltysalt" 和 1003次迭代
            salt = b'saltysalt'
            iterations = 1003
            key = PBKDF2(password.encode('utf-8'), salt, dkLen=16, count=iterations)

            self.encryption_key = key
            print("✅ 成功获取加密密钥")
            return key

        except Exception as e:
            print(f"❌ 获取加密密钥失败: {e}")
            sys.exit(1)

    def decrypt_cookie_value(self, encrypted_value):
        """解密Cookie值"""
        if not encrypted_value:
            return ""

        # Chromium加密格式: v10 prefix + 12字节IV + 加密数据 + 16字节tag
        if encrypted_value[:3] != b'v10':
            return ""

        # 提取IV和加密数据
        iv = encrypted_value[3:15]
        encrypted_data = encrypted_value[15:-16]
        tag = encrypted_value[-16:]

        # 使用AES-GCM解密
        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=iv)
        try:
            decrypted = cipher.decrypt_and_verify(encrypted_data, tag)
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"⚠️ 解密失败: {e}")
            return ""

    def extract_gemini_cookies(self):
        """提取Gemini相关的Cookie"""
        if not self.cookie_db_path.exists():
            print(f"❌ Cookie数据库不存在: {self.cookie_db_path}")
            sys.exit(1)

        # 复制数据库文件（避免锁定问题）
        temp_db = "/tmp/bitbrowser_cookies.db"
        import shutil
        shutil.copy(self.cookie_db_path, temp_db)

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # 查找Gemini的Cookie
            cursor.execute('''
                SELECT name, host_key, value, encrypted_value, expires_utc
                FROM cookies
                WHERE host_key LIKE '%.google.com%' AND name IN ('__Secure-1PSID', '__Secure-1PSIDCC', '__Secure-1PSIDTS')
                ORDER BY name
            ''')

            cookies = {}
            for row in cursor.fetchall():
                name, host, value, encrypted_value, expires_utc = row

                # 解密Cookie值
                if encrypted_value:
                    decrypted_value = self.decrypt_cookie_value(encrypted_value)
                else:
                    decrypted_value = value

                # 只保留.google.com的Cookie（不要.google.com.sg等）
                if host == '.google.com' and decrypted_value:
                    cookies[name] = {
                        'value': decrypted_value,
                        'expires': expires_utc,
                        'host': host
                    }

            conn.close()

            # 验证是否获取到所有必需的Cookie
            required_cookies = ['__Secure-1PSID', '__Secure-1PSIDCC', '__Secure-1PSIDTS']
            missing_cookies = [c for c in required_cookies if c not in cookies]

            if missing_cookies:
                print(f"❌ 缺少必需的Cookie: {', '.join(missing_cookies)}")
                print(f"   提示: 请先在BitBrowser中登录 gemini.google.com")
                sys.exit(1)

            # 打印Cookie信息
            print("\n✅ 成功提取Cookie:")
            for name, data in cookies.items():
                # 转换Chrome时间戳为可读格式
                # Chrome时间戳: 从1601-01-01 00:00:00 UTC开始的微秒数
                chrome_epoch = datetime.datetime(1601, 1, 1)
                expires_datetime = chrome_epoch + datetime.timedelta(microseconds=data['expires'])

                value_preview = data['value'][:50] + '...' if len(data['value']) > 50 else data['value']
                print(f"  {name}:")
                print(f"    值: {value_preview}")
                print(f"    过期时间: {expires_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            return cookies

        except Exception as e:
            print(f"❌ 提取Cookie失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            # 清理临时文件
            if os.path.exists(temp_db):
                os.remove(temp_db)

    def generate_cookies_txt(self, cookies):
        """生成cookies.txt格式"""
        lines = []
        lines.append("# Netscape HTTP Cookie File")
        lines.append("# This is a generated file! Do not edit.")
        lines.append("")

        for name, data in sorted(cookies.items()):
            # Netscape格式: domain, flag, path, secure, expiration, name, value
            domain = ".google.com"
            flag = "TRUE"
            path = "/"
            secure = "TRUE"
            expiration = str(data['expires'] // 1000000 - 11644473600)  # 转换为Unix时间戳
            value = data['value']

            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}")

        return "\n".join(lines)

    def save_to_file(self, cookies, output_file):
        """保存Cookie到文件"""
        cookies_txt = self.generate_cookies_txt(cookies)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(cookies_txt)

        print(f"\n✅ Cookie已保存到: {output_path}")
        return output_path

    def deploy_to_server(self, cookies):
        """部署Cookie到服务器"""
        print("\n" + "="*60)
        print("正在部署到服务器...")
        print("="*60)

        # 提取Cookie值
        psid = cookies['__Secure-1PSID']['value']
        psidcc = cookies['__Secure-1PSIDCC']['value']
        psidts = cookies['__Secure-1PSIDTS']['value']

        # SSH到服务器并重建容器
        deploy_script = f"""
set -e

echo "🛑 停止旧容器..."
docker stop google-reverse 2>/dev/null || true
docker rm google-reverse 2>/dev/null || true

echo "🚀 创建新容器..."
docker run -d \\
  --name google-reverse \\
  --restart unless-stopped \\
  -p 8100:8000 \\
  -e "SECURE_1PSID={psid}" \\
  -e "SECURE_1PSIDCC={psidcc}" \\
  -e "SECURE_1PSIDTS={psidts}" \\
  -e "GOOGLE_AI_API_KEY=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw" \\
  google-reverse-api

echo "📦 安装依赖..."
sleep 3
docker exec google-reverse pip install google-genai 2>&1 | grep -v "already satisfied" || true

echo "🔍 测试API..."
sleep 2
curl -sf https://google-api.aihang365.com/health || echo "⚠️ 健康检查失败"

echo ""
echo "✅ 部署完成！"
docker ps --filter name=google-reverse --format "table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}"
"""

        try:
            result = subprocess.run(
                ['ssh', 'root@82.29.54.80', 'bash -s'],
                input=deploy_script,
                capture_output=True,
                text=True,
                timeout=60
            )

            print(result.stdout)

            if result.returncode != 0:
                print(f"❌ 部署失败:\n{result.stderr}")
                sys.exit(1)

            print("\n" + "="*60)
            print("🎉 自动化部署完成！")
            print("="*60)
            print("\n📊 验证步骤:")
            print("  1. Chat API: curl -X POST https://google-api.aihang365.com/v1/chat/completions \\")
            print("       -d '{\"model\":\"gemini-2.5-flash\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}'")
            print("  2. Image API: curl -X POST https://google-api.aihang365.com/v1/images/generations \\")
            print("       -d '{\"model\":\"gemini-3-pro-image-preview\",\"prompt\":\"a cat\"}'")

        except subprocess.TimeoutExpired:
            print("❌ 部署超时（>60秒）")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 部署失败: {e}")
            sys.exit(1)

def main():
    print("="*60)
    print("BitBrowser Cookie 自动提取工具")
    print("="*60)
    print()

    extractor = BitBrowserCookieExtractor()

    # 步骤1: 获取加密密钥
    print("步骤1: 获取加密密钥...")
    extractor.get_encryption_key()

    # 步骤2: 提取Cookie
    print("\n步骤2: 提取Gemini Cookie...")
    cookies = extractor.extract_gemini_cookies()

    # 步骤3: 保存到文件
    print("\n步骤3: 保存Cookie到文件...")
    output_file = Path(__file__).parent / "extracted_cookies.txt"
    extractor.save_to_file(cookies, output_file)

    # 步骤4: 部署到服务器
    deploy = input("\n是否立即部署到服务器? (y/N): ").strip().lower()
    if deploy == 'y':
        extractor.deploy_to_server(cookies)
    else:
        print("\n✅ Cookie已提取完成，跳过部署")
        print(f"   Cookie文件: {output_file}")
        print(f"   手动部署命令: ./deploy-cookies.sh {output_file}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(1)
