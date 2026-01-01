#!/usr/bin/env python3
"""
Gemini Reverse API 全模型自动化测试工具

使用方法:
    python3 test-all-models.py                    # 默认测试
    python3 test-all-models.py --api https://xxx  # 指定API
    python3 test-all-models.py --output ./reports # 指定输出目录

作者: Mason
版本: 1.0.0
"""

import json
import time
import subprocess
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# 默认配置
DEFAULT_API = "https://google-api.aihang365.com"


class GeminiAPITester:
    def __init__(self, api_base: str, output_dir: str = "."):
        self.api_base = api_base.rstrip("/")
        self.output_dir = Path(output_dir)
        self.results = []
        self.start_time = datetime.now()

    def curl_request(self, method: str, endpoint: str, data=None,
                     timeout: int = 60, output_file: str = None) -> str:
        """执行curl请求"""
        cmd = ["curl", "-s", "--max-time", str(timeout), "-X", method]

        if output_file:
            cmd.extend(["-o", output_file])

        if data and not isinstance(data, list):
            cmd.extend(["-H", "Content-Type: application/json"])
            cmd.extend(["-d", json.dumps(data)])
        elif isinstance(data, list):
            cmd.extend(data)

        cmd.append(f"{self.api_base}{endpoint}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            return result.stdout if not output_file else ""
        except subprocess.TimeoutExpired:
            return '{"error": "timeout"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def test_endpoint(self, name: str, category: str, method: str, endpoint: str,
                      data=None, success_check=None, timeout: int = 60,
                      output_file: str = None) -> bool:
        """通用端点测试"""
        print(f"🔍 测试 {name}...", end=" ", flush=True)
        start = time.time()
        resp = self.curl_request(method, endpoint, data, timeout, output_file)
        elapsed = time.time() - start

        success = False
        note = ""

        if output_file:
            # 检查文件类型
            try:
                result = subprocess.run(["file", output_file], capture_output=True, text=True)
                success = "WAVE" in result.stdout or "audio" in result.stdout.lower()
                note = "WAV音频" if success else "非音频文件"
                if not success:
                    with open(output_file, "r") as f:
                        content = f.read()[:100]
                    if "leaked" in content.lower():
                        note = "API Key被禁用"
                    elif "quota" in content.lower():
                        note = "配额耗尽"
                    elif "error" in content.lower():
                        note = content[:40]
            except Exception as e:
                note = str(e)[:30]
        else:
            try:
                data_resp = json.loads(resp)
                if success_check:
                    success, note = success_check(data_resp)
                else:
                    success = "error" not in str(data_resp).lower()
                    note = "成功" if success else str(data_resp.get("detail", data_resp))[:40]
            except Exception as e:
                success = False
                note = str(e)[:30]

        status_icon = "✅" if success else "❌"
        print(f"{status_icon} ({elapsed:.2f}s)")

        self.results.append({
            "category": category,
            "name": name,
            "status": status_icon,
            "time": f"{elapsed:.2f}s",
            "note": note
        })

        time.sleep(2)  # 避免限流
        return success

    # 检查函数
    @staticmethod
    def check_health(r):
        return r.get("status") == "ok", f"v{r.get('version', '?')}"

    @staticmethod
    def check_cookie(r):
        return r.get("valid") == True, "有效" if r.get("valid") else "无效"

    @staticmethod
    def check_chat(r):
        if r.get("choices"):
            return True, r["choices"][0]["message"]["content"][:20]
        return False, r.get("detail", str(r))[:40]

    @staticmethod
    def check_image(r):
        if r.get("data") or r.get("images"):
            return True, "生成成功"
        return False, r.get("detail", str(r))[:40]

    @staticmethod
    def check_analysis(r):
        if r.get("analysis") or r.get("content") or r.get("description"):
            return True, "分析成功"
        return False, r.get("detail", str(r))[:40]

    def create_test_files(self):
        """创建测试用的PDF和图片文件"""
        # 创建PDF
        try:
            subprocess.run(["python3", "-c", """
from reportlab.pdfgen import canvas
c = canvas.Canvas('/tmp/test_gemini_api.pdf')
c.drawString(100, 750, 'Test Document')
c.save()
"""], capture_output=True, timeout=10)
        except:
            with open("/tmp/test_gemini_api.pdf", "w") as f:
                f.write("%PDF-1.4 test")

        # 创建图片
        try:
            subprocess.run(["python3", "-c", """
from PIL import Image
Image.new('RGB', (100, 100), 'white').save('/tmp/test_gemini_ui.png')
"""], capture_output=True, timeout=10)
        except:
            pass

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("Gemini Reverse API 全模型自动化测试")
        print(f"API: {self.api_base}")
        print(f"时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        # 系统检查
        print("📋 系统检查")
        print("-" * 40)
        self.test_endpoint("健康检查", "系统", "GET", "/health",
                           success_check=self.check_health)
        self.test_endpoint("Cookie状态", "系统", "GET", "/api/cookies/status",
                           success_check=self.check_cookie)
        print()

        # 文本模型
        print("📝 文本生成模型")
        print("-" * 40)
        for model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-pro"]:
            self.test_endpoint(model, "文本生成", "POST", "/v1/chat/completions",
                               {"model": model, "messages": [{"role": "user", "content": "1+1=?只答数字"}]},
                               success_check=self.check_chat, timeout=60)
        print()

        # 图片模型
        print("🎨 图片生成模型")
        print("-" * 40)
        for model in ["gemini-2.5-flash-image", "gemini-3-pro-image-preview",
                      "gemini-3-pro-image-preview-2k", "gemini-3-pro-image-preview-4k"]:
            self.test_endpoint(model, "图片生成", "POST", "/v1/images/generations",
                               {"model": model, "prompt": "a simple red circle", "n": 1},
                               success_check=self.check_image, timeout=120)
        print()

        # TTS模型
        print("🎤 TTS语音模型")
        print("-" * 40)
        for model in ["tts-1", "tts-1-hd"]:
            self.test_endpoint(model, "TTS语音", "POST", "/v1/audio/speech",
                               {"model": model, "input": "你好", "voice": "nova"},
                               timeout=60, output_file=f"/tmp/tts_{model}.wav")
        print()

        # 创建测试文件
        self.create_test_files()

        # PDF分析
        print("📄 文档分析")
        print("-" * 40)
        self.test_endpoint("PDF分析", "文档分析", "POST", "/v1/documents/analyze",
                           ["-F", "file=@/tmp/test_gemini_api.pdf", "-F", "prompt=describe"],
                           success_check=self.check_analysis)
        print()

        # UI分析
        print("🖼️ UI设计分析")
        print("-" * 40)
        self.test_endpoint("UI设计分析", "UI分析", "POST", "/v1/design/analyze",
                           ["-F", "file=@/tmp/test_gemini_ui.png", "-F", "prompt=describe"],
                           success_check=self.check_analysis)
        print()

    def generate_report(self) -> str:
        """生成Markdown测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "✅")
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        # 获取版本号
        version = "unknown"
        for r in self.results:
            if r["name"] == "健康检查" and r["status"] == "✅":
                version = r["note"]
                break

        # 分类结果
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        # 失败项
        failures = [r for r in self.results if r["status"] == "❌"]

        report = f"""# Gemini Reverse API 测试报告

**测试日期**: {self.start_time.strftime('%Y-%m-%d')}
**测试时间**: {self.start_time.strftime('%H:%M:%S')}
**API版本**: {version}
**测试环境**: {self.api_base}

---

## 测试概览

| 指标 | 数值 |
|------|------|
| 总测试项 | {total} |
| 通过 | {passed} |
| 失败 | {failed} |
| 通过率 | **{pass_rate:.1f}%** |

---

## 详细测试结果

"""

        for cat, items in categories.items():
            cat_passed = sum(1 for r in items if r["status"] == "✅")
            report += f"### {cat} ({cat_passed}/{len(items)})\n\n"
            report += "| 测试项 | 状态 | 耗时 | 备注 |\n"
            report += "|--------|------|------|------|\n"
            for r in items:
                report += f"| {r['name']} | {r['status']} | {r['time']} | {r['note']} |\n"
            report += "\n"

        if failures:
            report += "---\n\n## 已知问题\n\n"
            for f in failures:
                report += f"### {f['name']}\n\n"
                report += f"- **类别**: {f['category']}\n"
                report += f"- **耗时**: {f['time']}\n"
                report += f"- **原因**: {f['note']}\n\n"

        # 性能统计
        report += """---

## 性能统计

### 响应时间

"""
        for cat, items in categories.items():
            times = [float(r["time"].replace("s", "")) for r in items]
            if times:
                avg = sum(times) / len(times)
                report += f"- **{cat}**: 平均 {avg:.2f}s (最快 {min(times):.2f}s, 最慢 {max(times):.2f}s)\n"

        # 结论
        if pass_rate >= 90:
            conclusion = "API运行状态良好，核心功能全部正常。"
        elif pass_rate >= 70:
            conclusion = "API基本正常运行，部分功能存在问题需要关注。"
        else:
            conclusion = "API存在较多问题，建议立即排查。"

        report += f"""
---

## 结论

{conclusion}

**推荐使用的功能**:
"""
        for cat, items in categories.items():
            cat_passed = sum(1 for r in items if r["status"] == "✅")
            if cat_passed > 0:
                models = ", ".join([r["name"] for r in items if r["status"] == "✅"])
                report += f"- ✅ {cat}: {models}\n"

        report += f"""
---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*测试工具: Gemini API Tester v1.0.0*
"""
        return report

    def save_report(self):
        """保存测试报告"""
        date_str = self.start_time.strftime('%Y-%m-%d')
        filename = f"TEST_REPORT_{date_str}.md"
        filepath = self.output_dir / filename

        report = self.generate_report()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 报告已保存: {filepath}")
        return filepath

    def print_summary(self):
        """打印测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "✅")
        failed = total - passed

        print("=" * 60)
        print("测试完成!")
        print("=" * 60)
        print(f"  总测试: {total}")
        print(f"  通过:   {passed} ✅")
        print(f"  失败:   {failed} ❌")
        print(f"  通过率: {passed/total*100:.1f}%")
        print()


def main():
    parser = argparse.ArgumentParser(description="Gemini Reverse API 测试工具")
    parser.add_argument("--api", default=DEFAULT_API, help="API地址")
    parser.add_argument("--output", "-o", default=".", help="报告输出目录")
    args = parser.parse_args()

    tester = GeminiAPITester(args.api, args.output)
    tester.run_all_tests()
    tester.print_summary()
    tester.save_report()


if __name__ == "__main__":
    main()
