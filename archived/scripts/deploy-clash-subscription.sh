#!/bin/bash
# 部署Clash订阅服务脚本

set -e

SERVER="82.29.54.80"
PORT="9527"
WEB_ROOT="/var/www/html"

echo "🚀 部署Clash订阅服务..."

# 1. 创建订阅配置文件
cat > /tmp/clash-subscription.yaml << 'EOF'
# Clash Subscription Configuration
# 日本和美国节点订阅

proxies:
  - name: JP - 日本Vmess
    type: vmess
    server: 31.58.223.134
    port: 8443
    uuid: 78cdc6b7-8b14-47d6-bf09-3167bc5124fb
    alterId: 0
    cipher: auto
    tls: false
    udp: true

  - name: US - 美国Vmess
    type: vmess
    server: 82.29.54.80
    port: 8443
    uuid: 60f4e0e4-71ed-441c-a226-82abb655168a
    alterId: 0
    cipher: auto
    tls: false
    udp: true
EOF

# 2. 上传到服务器
echo "📤 上传订阅文件到服务器..."
scp /tmp/clash-subscription.yaml root@${SERVER}:${WEB_ROOT}/clash.yaml

# 3. 设置权限
echo "🔒 设置文件权限..."
ssh root@${SERVER} "chmod 644 ${WEB_ROOT}/clash.yaml"

# 4. 测试服务器端访问
echo "🧪 测试服务器端访问..."
ssh root@${SERVER} "curl -I http://localhost:${PORT}/clash.yaml | head -5"

echo ""
echo "✅ 部署完成！"
echo ""
echo "📍 订阅链接："
echo "   http://${SERVER}:${PORT}/clash.yaml"
echo ""
echo "⚠️  重要提示："
echo "   1. 在Clash Verge中使用此链接前，请先关闭Clash代理"
echo "   2. 或在浏览器中直接下载此文件后，在Clash Verge中选择'导入' > '从本地文件'"
echo ""
echo "🔗 直接下载链接（在浏览器中打开）："
echo "   http://${SERVER}:${PORT}/clash.yaml"
