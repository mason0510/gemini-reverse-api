#!/bin/bash
# Cookie更新脚本 - 从Netscape格式cookie文件更新
# 使用方法: ./update-cookies-from-file.sh <cookie_file_path>

set -e

COOKIE_FILE="$1"
SERVER="82.29.54.80"

if [ -z "$COOKIE_FILE" ]; then
    echo "❌ 错误：请提供cookie文件路径"
    echo "使用方法: $0 <cookie_file_path>"
    exit 1
fi

if [ ! -f "$COOKIE_FILE" ]; then
    echo "❌ 错误：文件不存在: $COOKIE_FILE"
    exit 1
fi

echo "🔍 解析cookie文件..."

# 提取关键cookie值
SECURE_1PSID=$(grep "__Secure-1PSID" "$COOKIE_FILE" | grep -v "PSIDTS\|PSIDCC" | awk '{print $7}')
SECURE_1PSIDCC=$(grep "__Secure-1PSIDCC" "$COOKIE_FILE" | awk '{print $7}')
SECURE_1PSIDTS=$(grep "__Secure-1PSIDTS" "$COOKIE_FILE" | awk '{print $7}')

if [ -z "$SECURE_1PSID" ] || [ -z "$SECURE_1PSIDCC" ] || [ -z "$SECURE_1PSIDTS" ]; then
    echo "❌ 错误：无法从cookie文件中提取必需的cookie值"
    echo "SECURE_1PSID: ${SECURE_1PSID:0:50}..."
    echo "SECURE_1PSIDCC: ${SECURE_1PSIDCC:0:50}..."
    echo "SECURE_1PSIDTS: ${SECURE_1PSIDTS:0:50}..."
    exit 1
fi

echo "✅ Cookie提取成功"
echo "   SECURE_1PSID: ${SECURE_1PSID:0:50}..."
echo "   SECURE_1PSIDCC: ${SECURE_1PSIDCC:0:50}..."
echo "   SECURE_1PSIDTS: ${SECURE_1PSIDTS:0:50}..."

# 更新本地.env文件
echo ""
echo "📝 更新本地.env文件..."
cat > .env << EOF
SECURE_1PSID=$SECURE_1PSID
SECURE_1PSIDCC=$SECURE_1PSIDCC
SECURE_1PSIDTS=$SECURE_1PSIDTS

# Google AI API Keys (多平台支持)
GOOGLE_AI_API_KEY=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
GOOGLE_AI_API_KEY_BACKUP=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
GOOGLE_AI_API_KEY_PLATFORM2=
GOOGLE_AI_API_KEY_PLATFORM3=
EOF

echo "✅ 本地.env文件已更新"

# 上传到服务器
echo ""
echo "📤 上传到服务器 ($SERVER)..."
scp .env root@${SERVER}:/root/gemini-text-api/.env

# 重启服务
echo ""
echo "🔄 重启服务..."
ssh root@${SERVER} "cd /root/gemini-text-api && docker stop gemini-text-api && docker rm gemini-text-api && docker run -d --name gemini-text-api --restart unless-stopped -p 8765:8000 --env-file .env gemini-text-api"

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 3

# 检查服务状态
echo ""
echo "🔍 检查服务状态..."
ssh root@${SERVER} "docker logs gemini-text-api --tail 10"

echo ""
echo "✅ Cookie更新完成！"
echo ""
echo "📍 服务地址："
echo "   http://${SERVER}:8765"
echo "   http://gemini-text.satoshitech.xyz"
