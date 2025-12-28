#!/bin/bash
# 一键更新服务器容器Cookie

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COOKIE_FILE="$SCRIPT_DIR/cookies.json"

if [ ! -f "$COOKIE_FILE" ]; then
    echo "❌ Cookie文件不存在: $COOKIE_FILE"
    echo "请先运行: npm run save"
    exit 1
fi

echo "📖 读取Cookie..."
SECURE_1PSID=$(cat "$COOKIE_FILE" | grep -o '"SECURE_1PSID": "[^"]*"' | cut -d'"' -f4)
SECURE_1PSIDCC=$(cat "$COOKIE_FILE" | grep -o '"SECURE_1PSIDCC": "[^"]*"' | cut -d'"' -f4)
SECURE_1PSIDTS=$(cat "$COOKIE_FILE" | grep -o '"SECURE_1PSIDTS": "[^"]*"' | cut -d'"' -f4)

if [ -z "$SECURE_1PSID" ] || [ -z "$SECURE_1PSIDTS" ]; then
    echo "❌ Cookie提取失败"
    exit 1
fi

echo "✅ Cookie提取成功"
echo "   PSID: ${SECURE_1PSID:0:30}..."
echo "   PSIDTS: ${SECURE_1PSIDTS:0:30}..."
echo ""

echo "🛑 停止并删除旧容器..."
ssh root@82.29.54.80 'docker stop google-reverse && docker rm google-reverse' 2>/dev/null || true

echo "🚀 创建新容器..."
ssh root@82.29.54.80 "docker run -d \
  --name google-reverse \
  --restart unless-stopped \
  -p 8100:8100 \
  -e 'SECURE_1PSID=$SECURE_1PSID' \
  -e 'SECURE_1PSIDCC=$SECURE_1PSIDCC' \
  -e 'SECURE_1PSIDTS=$SECURE_1PSIDTS' \
  -e 'GOOGLE_AI_API_KEY=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw' \
  gemini-reverse-api:latest"

echo ""
echo "⏳ 等待服务启动..."
sleep 5

echo "🧪 测试API..."
HEALTH=$(curl -s https://google-api.aihang365.com/health)
echo "   Health: $HEALTH"

COOKIE_STATUS=$(curl -s https://google-api.aihang365.com/api/cookies/status)
echo "   Cookie Status: $COOKIE_STATUS"

echo ""
echo "✅ 完成！"
echo ""
echo "测试gchat:"
echo "  gchat -b local -p '你好'"
