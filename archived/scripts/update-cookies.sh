#!/bin/bash
# Cookie快速更新脚本
# 用途: 更新Gemini Reverse API的Cookie配置并重启服务

set -e

SERVER="root@82.29.54.80"
PROJECT_DIR="/root/02-production/gemini-reverse-api"
LOCAL_DIR="/Users/houzi/code/02-production/my-reverse-api/gemini-text"

echo "🔄 开始更新Cookie配置..."

# 1. 检查本地.env文件是否存在
if [ ! -f "$LOCAL_DIR/.env" ]; then
    echo "❌ 错误: 本地.env文件不存在: $LOCAL_DIR/.env"
    exit 1
fi

# 2. 同步.env文件到服务器
echo "📤 上传.env文件到服务器..."
scp "$LOCAL_DIR/.env" "$SERVER:$PROJECT_DIR/.env"

# 3. 同步api_server.py到服务器
echo "📤 上传api_server.py到服务器..."
scp "$LOCAL_DIR/api_server.py" "$SERVER:$PROJECT_DIR/api_server.py"

# 4. 重启Docker容器
echo "🔄 停止并删除旧容器..."
ssh $SERVER "docker stop google-reverse 2>/dev/null || true"
ssh $SERVER "docker rm google-reverse 2>/dev/null || true"

echo "🔨 重新构建Docker镜像..."
ssh $SERVER "cd $PROJECT_DIR && docker build --no-cache -t gemini-reverse-api:latest ."

echo "🚀 启动新容器..."
# 检查是否需要代理（通过环境变量控制）
if [ "${USE_PROXY}" = "true" ]; then
    echo "  🌐 使用代理模式: http://127.0.0.1:8118"
    ssh $SERVER "
docker run -d \
  --name google-reverse \
  -p 8100:8100 \
  --restart unless-stopped \
  -e HTTP_PROXY=http://172.17.0.1:8118 \
  -e HTTPS_PROXY=http://172.17.0.1:8118 \
  -e NO_PROXY=localhost,127.0.0.1 \
  gemini-reverse-api:latest
"
else
    ssh $SERVER "
docker run -d \
  --name google-reverse \
  -p 8100:8100 \
  --restart unless-stopped \
  gemini-reverse-api:latest
"
fi

# 5. 等待容器启动
echo "⏳ 等待容器启动 (5秒)..."
sleep 5

# 6. 验证Cookie状态
echo "✅ 验证Cookie状态..."
RESPONSE=$(curl -s https://google-api.aihang365.com/api/cookies/status)
echo "$RESPONSE" | python3 -m json.tool

# 7. 检查是否成功
if echo "$RESPONSE" | grep -q '"valid":true'; then
    echo ""
    echo "🎉 Cookie更新成功! 服务已恢复正常"
else
    echo ""
    echo "⚠️  警告: Cookie状态异常,请检查配置"
    echo "📋 查看容器日志: ssh $SERVER 'docker logs google-reverse --tail 50'"
fi
