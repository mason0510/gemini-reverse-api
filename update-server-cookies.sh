#!/bin/bash
# 从cookie文件提取值并更新服务器上的.env配置
# 用法: ./update-server-cookies.sh /path/to/cookies.txt

set -e

COOKIE_FILE="${1:-/Users/houzi/Downloads/gemini.google.com_cookies.txt}"
SERVER="root@82.29.54.80"
REMOTE_ENV_PATH="/root/gemini-text-api/.env"
CONTAINER_NAME="google-reverse"
IMAGE_NAME="google-reverse"

if [ ! -f "$COOKIE_FILE" ]; then
    echo "❌ Cookie文件不存在: $COOKIE_FILE"
    echo "用法: $0 <cookie文件路径>"
    exit 1
fi

echo "📖 从cookie文件提取值..."

# 提取cookie值
SECURE_1PSID=$(grep "__Secure-1PSID" "$COOKIE_FILE" | grep -v "PSIDCC\|PSIDTS" | head -1 | awk '{print $NF}')
SECURE_1PSIDCC=$(grep "__Secure-1PSIDCC" "$COOKIE_FILE" | head -1 | awk '{print $NF}')
SECURE_1PSIDTS=$(grep "__Secure-1PSIDTS" "$COOKIE_FILE" | head -1 | awk '{print $NF}')

if [ -z "$SECURE_1PSID" ] || [ -z "$SECURE_1PSIDCC" ] || [ -z "$SECURE_1PSIDTS" ]; then
    echo "❌ 无法从cookie文件中提取所有必需的值"
    echo "  SECURE_1PSID: ${SECURE_1PSID:-未找到}"
    echo "  SECURE_1PSIDCC: ${SECURE_1PSIDCC:-未找到}"
    echo "  SECURE_1PSIDTS: ${SECURE_1PSIDTS:-未找到}"
    exit 1
fi

echo "✅ 提取到的Cookie值:"
echo "  SECURE_1PSID: ${SECURE_1PSID:0:50}..."
echo "  SECURE_1PSIDCC: ${SECURE_1PSIDCC:0:30}..."
echo "  SECURE_1PSIDTS: ${SECURE_1PSIDTS:0:30}..."

echo ""
echo "🔄 更新服务器 $SERVER 上的配置..."

# 重新创建容器（因为环境变量是在容器创建时设置的）
ssh "$SERVER" << EOF
    # 备份当前配置
    cp $REMOTE_ENV_PATH ${REMOTE_ENV_PATH}.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

    # 获取当前API KEY
    CURRENT_API_KEY=\$(docker inspect $CONTAINER_NAME --format='{{range .Config.Env}}{{println .}}{{end}}' | grep GOOGLE_AI_API_KEY= | head -1 | cut -d= -f2)
    CURRENT_API_KEY_BACKUP=\$(docker inspect $CONTAINER_NAME --format='{{range .Config.Env}}{{println .}}{{end}}' | grep GOOGLE_AI_API_KEY_BACKUP= | head -1 | cut -d= -f2)

    echo "🔄 停止并删除旧容器..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME

    echo "🔄 使用新Cookie创建容器..."
    docker run -d \\
      --name $CONTAINER_NAME \\
      --restart unless-stopped \\
      -p 8100:8000 \\
      -e "SECURE_1PSID=$SECURE_1PSID" \\
      -e "SECURE_1PSIDCC=$SECURE_1PSIDCC" \\
      -e "SECURE_1PSIDTS=$SECURE_1PSIDTS" \\
      -e "GOOGLE_AI_API_KEY=\${CURRENT_API_KEY:-AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw}" \\
      -e "GOOGLE_AI_API_KEY_BACKUP=\${CURRENT_API_KEY_BACKUP:-AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw}" \\
      $IMAGE_NAME

    echo "✅ 容器已重新创建"
    docker ps | grep $CONTAINER_NAME
EOF

echo ""
echo "🎉 完成！服务器cookie已更新"
echo "⏳ 等待5秒后测试..."
sleep 5
curl -s -X POST "https://google-api.aihang365.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "回复ok"}], "max_tokens": 10}' | head -c 200
echo ""
