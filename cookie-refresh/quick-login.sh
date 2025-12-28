#!/bin/bash
# 一键登录：自动启动SSH隧道和带代理的Chrome

set -e

echo "════════════════════════════════════════"
echo "  一键登录 Gemini（通过SSH隧道）"
echo "════════════════════════════════════════"
echo ""

# 检查是否已有SSH隧道
if lsof -i :1081 > /dev/null 2>&1; then
    echo "⚠️  端口1081已被占用，清理中..."
    pkill -f "ssh -D 1081" || true
    sleep 1
fi

# 建立SSH隧道
echo "📡 建立SSH隧道到美国服务器..."
ssh -D 1081 -N -f root@82.29.54.80

sleep 2

echo "✅ SSH隧道已建立"
echo ""

# 启动带代理的Chrome
echo "🚀 启动Chrome浏览器（通过代理）..."
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --proxy-server="socks5://127.0.0.1:1081" \
    --new-window \
    "https://gemini.google.com" \
    > /dev/null 2>&1 &

sleep 2

echo "✅ Chrome已启动并访问 Gemini"
echo ""
echo "════════════════════════════════════════"
echo "下一步操作："
echo "════════════════════════════════════════"
echo ""
echo "1. ✅ Chrome已自动打开 gemini.google.com"
echo ""
echo "2. 🔐 登录你的Google账号"
echo ""
echo "3. 📋 登录成功后，按F12打开开发者工具："
echo "   - 点击顶部 Application 标签"
echo "   - 左侧展开 Cookies"
echo "   - 点击 https://gemini.google.com"
echo "   - 找到并复制以下Cookie的值（Value列）："
echo ""
echo "     __Secure-1PSID       (很长的字符串)"
echo "     __Secure-1PSIDCC     (较短的字符串)"
echo "     __Secure-1PSIDTS     (sidts-开头的字符串)"
echo ""
echo "4. 💾 运行以下命令保存Cookie："
echo "   npm run save"
echo ""
echo "5. 📤 同步到服务器："
echo "   npm run sync"
echo ""
echo "════════════════════════════════════════"
echo ""
echo "完成后关闭SSH隧道："
echo "  pkill -f 'ssh -D 1081'"
echo ""
