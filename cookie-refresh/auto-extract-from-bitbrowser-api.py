#!/usr/bin/env python3
# 功能: 通过BitBrowser本地API自动提取Gemini Cookie并部署到服务器
# 关键词: cookie, bitbrowser-api, auto-extract, gemini, 自动化

import requests
import json
import subprocess
import sys
import time
from pathlib import Path
import datetime

class BitBrowserAPI:
    def __init__(self, base_url="http://127.0.0.1:54345"):
        self.base_url = base_url
        self.session = requests.Session()

    def health_check(self):
        """检查BitBrowser Local Server是否运行"""
        try:
            response = self.session.post(f"{self.base_url}/health", timeout=5)
            return response.json().get('success', False)
        except Exception as e:
            print(f"❌ 无法连接到BitBrowser Local Server: {e}")
            print(f"\n请确保:")
            print(f"  1. BitBrowser客户端正在运行")
            print(f"  2. Local Server已启动（设置 -> Local Server -> 端口: {self.base_url.split(':')[-1]}）")
            return False

    def list_browsers(self, page=0, page_size=100, name=None):
        """获取浏览器窗口列表"""
        data = {
            "page": page,
            "pageSize": page_size
        }
        if name:
            data["name"] = name

        try:
            response = self.session.post(
                f"{self.base_url}/browser/list",
                json=data,
                timeout=10
            )
            result = response.json()
            if result.get('success'):
                return result.get('data', {}).get('list', [])
            else:
                print(f"❌ 获取窗口列表失败: {result.get('msg')}")
                return []
        except Exception as e:
            print(f"❌ 获取窗口列表出错: {e}")
            return []

    def get_browser_detail(self, browser_id):
        """获取浏览器窗口详情"""
        try:
            response = self.session.post(
                f"{self.base_url}/browser/detail",
                json={"id": browser_id},
                timeout=10
            )
            result = response.json()
            if result.get('success'):
                return result.get('data')
            else:
                print(f"❌ 获取窗口详情失败: {result.get('msg')}")
                return None
        except Exception as e:
            print(f"❌ 获取窗口详情出错: {e}")
            return None

    def open_browser(self, browser_id, queue=True):
        """打开浏览器窗口"""
        try:
            response = self.session.post(
                f"{self.base_url}/browser/open",
                json={"id": browser_id, "queue": queue},
                timeout=30
            )
            result = response.json()
            if result.get('success'):
                return result.get('data')
            else:
                print(f"❌ 打开窗口失败: {result.get('msg')}")
                return None
        except Exception as e:
            print(f"❌ 打开窗口出错: {e}")
            return None

    def get_browser_cookies(self, browser_id):
        """获取已打开窗口的实时Cookie"""
        try:
            response = self.session.post(
                f"{self.base_url}/browser/cookies/get",
                json={"browserId": browser_id},
                timeout=10
            )
            result = response.json()
            if result.get('success'):
                return result.get('data', [])
            else:
                print(f"❌ 获取Cookie失败: {result.get('msg')}")
                return []
        except Exception as e:
            print(f"❌ 获取Cookie出错: {e}")
            return []

    def close_browser(self, browser_id):
        """关闭浏览器窗口"""
        try:
            response = self.session.post(
                f"{self.base_url}/browser/close",
                json={"id": browser_id},
                timeout=10
            )
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            print(f"⚠️ 关闭窗口出错: {e}")
            return False

class GeminiCookieExtractor:
    def __init__(self):
        self.api = BitBrowserAPI()
        self.required_cookies = ['__Secure-1PSID', '__Secure-1PSIDCC', '__Secure-1PSIDTS']

    def find_gemini_browser(self):
        """查找包含Gemini的浏览器窗口"""
        print("\n🔍 查找Gemini浏览器窗口...")

        # 先尝试按名称搜索
        browsers = self.api.list_browsers(name="gemini")
        if not browsers:
            # 搜索所有窗口
            browsers = self.api.list_browsers()

        gemini_browsers = []
        for browser in browsers:
            name = browser.get('name', '').lower()
            platform = browser.get('platform', '').lower()
            remark = browser.get('remark', '').lower()

            if 'gemini' in name or 'gemini' in platform or 'gemini' in remark:
                gemini_browsers.append(browser)

        if not gemini_browsers:
            print(f"❌ 未找到Gemini相关的浏览器窗口")
            print(f"\n提示: 请在BitBrowser中创建一个窗口并访问 gemini.google.com")
            return None

        # 显示找到的窗口
        print(f"\n✅ 找到 {len(gemini_browsers)} 个Gemini窗口:")
        for i, browser in enumerate(gemini_browsers, 1):
            seq = browser.get('seq', 'N/A')
            name = browser.get('name', 'Unnamed')
            status = '✅ 已打开' if browser.get('status') == 1 else '⚪ 未打开'
            print(f"  {i}. [{seq}] {name} {status}")

        # 如果只有一个，直接使用
        if len(gemini_browsers) == 1:
            return gemini_browsers[0]

        # 多个窗口，让用户选择
        while True:
            try:
                choice = input(f"\n请选择窗口 (1-{len(gemini_browsers)}) [默认: 1]: ").strip()
                choice = int(choice) if choice else 1
                if 1 <= choice <= len(gemini_browsers):
                    return gemini_browsers[choice - 1]
                else:
                    print(f"请输入 1-{len(gemini_browsers)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n⚠️ 用户取消")
                return None

    def extract_cookies_from_browser(self, browser):
        """从浏览器窗口提取Cookie"""
        browser_id = browser.get('id')
        browser_name = browser.get('name', 'Unnamed')
        browser_seq = browser.get('seq', 'N/A')
        is_open = browser.get('status') == 1

        print(f"\n📦 正在处理窗口: [{browser_seq}] {browser_name}")

        # 如果窗口未打开，先打开
        if not is_open:
            print(f"  ⏳ 打开浏览器窗口...")
            open_result = self.api.open_browser(browser_id)
            if not open_result:
                print(f"  ❌ 无法打开窗口")
                return None

            # 等待窗口完全加载
            print(f"  ⏳ 等待窗口加载...")
            time.sleep(5)
        else:
            print(f"  ✅ 窗口已打开")

        # 获取实时Cookie
        print(f"  🍪 提取Cookie...")
        all_cookies = self.api.get_browser_cookies(browser_id)

        if not all_cookies:
            print(f"  ❌ 未获取到任何Cookie")
            return None

        # 过滤Gemini相关的Cookie
        gemini_cookies = {}
        for cookie in all_cookies:
            name = cookie.get('name')
            domain = cookie.get('domain', '')

            # 只保留google.com域名的必需Cookie
            if 'google.com' in domain and name in self.required_cookies:
                gemini_cookies[name] = cookie

        # 验证是否获取到所有必需的Cookie
        missing_cookies = [c for c in self.required_cookies if c not in gemini_cookies]

        if missing_cookies:
            print(f"  ❌ 缺少必需的Cookie: {', '.join(missing_cookies)}")
            print(f"  提示: 请确保在该窗口中已登录 gemini.google.com 并进行过对话")
            return None

        print(f"  ✅ 成功提取 {len(gemini_cookies)} 个Cookie")

        # 如果窗口是我们打开的，关闭它
        if not is_open:
            print(f"  🛑 关闭浏览器窗口...")
            self.api.close_browser(browser_id)
            time.sleep(3)

        return gemini_cookies

    def convert_to_netscape_format(self, cookies):
        """转换为Netscape Cookie格式"""
        lines = []
        lines.append("# Netscape HTTP Cookie File")
        lines.append("# This is a generated file! Do not edit.")
        lines.append("")

        for name in sorted(cookies.keys()):
            cookie = cookies[name]

            domain = cookie.get('domain', '.google.com')
            flag = "TRUE"
            path = cookie.get('path', '/')
            secure = "TRUE" if cookie.get('secure', True) else "FALSE"
            expires = cookie.get('expires', int(time.time()) + 31536000)  # 默认1年
            value = cookie.get('value', '')

            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")

        return "\n".join(lines)

    def save_to_file(self, cookies, output_file):
        """保存Cookie到文件"""
        cookies_txt = self.convert_to_netscape_format(cookies)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(cookies_txt)

        print(f"\n✅ Cookie已保存到: {output_path}")

        # 显示Cookie信息
        print(f"\n📋 Cookie详情:")
        for name, cookie in cookies.items():
            value_preview = cookie['value'][:50] + '...' if len(cookie['value']) > 50 else cookie['value']
            expires_ts = cookie.get('expires', 0)
            expires_dt = datetime.datetime.fromtimestamp(expires_ts).strftime('%Y-%m-%d %H:%M:%S') if expires_ts else 'Session'
            print(f"  {name}:")
            print(f"    值: {value_preview}")
            print(f"    过期: {expires_dt}")

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
                return False

            print("\n" + "="*60)
            print("🎉 自动化部署完成！")
            print("="*60)
            print("\n📊 验证步骤:")
            print("  1. Chat API: curl -X POST https://google-api.aihang365.com/v1/chat/completions \\")
            print("       -d '{\"model\":\"gemini-2.5-flash\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}'")
            print("  2. Image API: curl -X POST https://google-api.aihang365.com/v1/images/generations \\")
            print("       -d '{\"model\":\"gemini-3-pro-image-preview\",\"prompt\":\"a cat\"}'")
            return True

        except subprocess.TimeoutExpired:
            print("❌ 部署超时（>60秒）")
            return False
        except Exception as e:
            print(f"❌ 部署失败: {e}")
            return False

def main():
    print("="*60)
    print("BitBrowser API Cookie 自动提取工具")
    print("="*60)

    extractor = GeminiCookieExtractor()

    # 步骤1: 健康检查
    print("\n步骤1: 检查BitBrowser Local Server...")
    if not extractor.api.health_check():
        sys.exit(1)
    print("✅ BitBrowser Local Server运行正常")

    # 步骤2: 查找Gemini浏览器窗口
    print("\n步骤2: 查找Gemini浏览器窗口...")
    browser = extractor.find_gemini_browser()
    if not browser:
        sys.exit(1)

    # 步骤3: 提取Cookie
    print("\n步骤3: 提取Cookie...")
    cookies = extractor.extract_cookies_from_browser(browser)
    if not cookies:
        sys.exit(1)

    # 步骤4: 保存到文件
    print("\n步骤4: 保存Cookie...")
    output_file = Path(__file__).parent / "extracted_cookies.txt"
    extractor.save_to_file(cookies, output_file)

    # 步骤5: 部署到服务器
    deploy = input("\n是否立即部署到服务器? (y/N): ").strip().lower()
    if deploy == 'y':
        success = extractor.deploy_to_server(cookies)
        sys.exit(0 if success else 1)
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
