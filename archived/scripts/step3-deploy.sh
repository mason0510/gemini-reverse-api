#!/bin/bash
# 步骤3自动化脚本 - 提取Cookie并部署

echo "==============================================="
echo "  步骤3: 提取Cookie并部署到服务器"
echo "==============================================="
echo ""

# 检查Cookie文件
COOKIE_FILE="/Users/houzi/Downloads/cookies-us.txt"
if [ ! -f "$COOKIE_FILE" ]; then
    echo "❌ 未找到Cookie文件: $COOKIE_FILE"
    echo ""
    echo "如果使用手动复制方式，请直接编辑.env文件："
    echo "  vim .env"
    echo ""
    echo "然后运行部署："
    echo "  ./update-cookies.sh"
    exit 1
fi

echo "📄 找到Cookie文件，开始提取..."
echo ""

# 提取Cookie值
PSID=$(grep -E "\.google\.com.*__Secure-1PSID[^CTD]" "$COOKIE_FILE" | awk '{print $7}' | head -1)
PSIDCC=$(grep -E "\.google\.com.*__Secure-1PSIDCC[^T]" "$COOKIE_FILE" | awk '{print $7}' | head -1)
PSIDTS=$(grep -E "\.google\.com.*__Secure-1PSIDTS" "$COOKIE_FILE" | awk '{print $7}' | head -1)

echo "提取的Cookie值："
echo "  SECURE_1PSID: ${PSID:0:50}..."
echo "  SECURE_1PSIDCC: ${PSIDCC:0:50}..."
echo "  SECURE_1PSIDTS: ${PSIDTS:0:50}..."
echo ""

if [ -z "$PSID" ] || [ -z "$PSIDTS" ]; then
    echo "❌ Cookie提取失败！"
    echo ""
    echo "请检查Cookie文件格式，或使用手动方式："
    echo "  vim .env"
    exit 1
fi

# 更新.env文件
echo "📝 更新.env文件..."
cat > .env << EOF
SECURE_1PSID=$PSID
SECURE_1PSIDCC=$PSIDCC
SECURE_1PSIDTS=$PSIDTS

# Google AI API Keys (多平台支持)
GOOGLE_AI_API_KEY=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
GOOGLE_AI_API_KEY_BACKUP=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
GOOGLE_AI_API_KEY_PLATFORM2=
GOOGLE_AI_API_KEY_PLATFORM3=
EOF

echo "✅ .env文件已更新"
echo ""

# 部署到服务器
echo "🚀 开始部署到服务器..."
echo ""
read -p "确认部署？(y/n): " DEPLOY

if [ "$DEPLOY" = "y" ]; then
    ./update-cookies.sh

    echo ""
    echo "==============================================="
    echo "  🎉 部署完成！"
    echo "==============================================="
    echo ""
    echo "📝 验证步骤："
    echo ""
    echo "1. 测试Cookie状态："
    echo "   curl https://google-api.aihang365.com/api/cookies/status | jq ."
    echo ""
    echo "2. 测试文本生成："
    echo "   curl -X POST https://google-api.aihang365.com/v1/generate \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"prompt\": \"Say hello\", \"model\": \"gemini-2.5-flash\"}' | jq ."
    echo ""
    echo "3. 运行完整测试："
    echo "   python test-all-apis.py"
    echo ""
else
    echo "❌ 已取消部署"
fi
