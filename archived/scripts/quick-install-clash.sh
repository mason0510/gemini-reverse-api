#!/bin/bash
# 使用现有配置文件在服务器上安装Clash

set -e

SERVER="root@82.29.54.80"
LOCAL_CONFIG="/Users/houzi/.config/clash/iggfeed.yaml"

echo "==============================================="
echo "  服务器Clash代理快速安装"
echo "==============================================="
echo ""

echo "📦 步骤1: 安装Clash客户端到服务器"
echo "----------------------------------------"
ssh $SERVER << 'EOF'
set -e

# 创建clash目录
mkdir -p /opt/clash
cd /opt/clash

# 下载clash-linux-amd64
if [ ! -f "clash" ]; then
    echo "📥 下载Clash..."
    wget -O clash.gz https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz
    gunzip clash.gz
    chmod +x clash
    echo "✅ Clash下载完成"
else
    echo "✅ Clash已存在"
fi
EOF

echo ""
echo "📤 步骤2: 上传配置文件"
echo "----------------------------------------"
scp "$LOCAL_CONFIG" "$SERVER:/opt/clash/config.yaml"
echo "✅ 配置文件已上传"

echo ""
echo "⚙️  步骤3: 创建systemd服务"
echo "----------------------------------------"
ssh $SERVER << 'EOF'
cat > /etc/systemd/system/clash.service << 'SERVICE'
[Unit]
Description=Clash Proxy Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/clash
ExecStart=/opt/clash/clash -d /opt/clash
Restart=always
RestartSec=3
Environment="HOME=/root"

[Install]
WantedBy=multi-user.target
SERVICE

# 重载systemd
systemctl daemon-reload
systemctl enable clash
systemctl start clash

echo "✅ Clash服务已启动"
sleep 3
EOF

echo ""
echo "🔍 步骤4: 验证Clash代理"
echo "----------------------------------------"
PROXY_IP=$(ssh $SERVER "curl -x http://127.0.0.1:7890 -s https://ifconfig.me 2>/dev/null || echo 'failed'")

if [ "$PROXY_IP" = "failed" ]; then
    echo "❌ 代理测试失败，检查Clash日志："
    ssh $SERVER "journalctl -u clash -n 50 --no-pager"
    exit 1
else
    echo "✅ 代理工作正常！"
    echo "   出口IP: $PROXY_IP"
fi

echo ""
echo "🐳 步骤5: 重新部署Docker容器（使用代理）"
echo "----------------------------------------"
read -p "现在重新部署容器使用代理？(y/n): " DEPLOY

if [ "$DEPLOY" = "y" ]; then
    USE_PROXY=true ./update-cookies.sh

    echo ""
    echo "⏳ 等待容器启动..."
    sleep 5

    echo ""
    echo "🧪 测试API..."
    curl -X POST https://google-api.aihang365.com/v1/generate \
      -H "Content-Type: application/json" \
      -d '{"prompt": "Say hello", "model": "gemini-2.5-flash"}' \
      2>/dev/null | jq .
fi

echo ""
echo "==============================================="
echo "  🎉 安装完成！"
echo "==============================================="
echo ""
echo "📊 当前状态："
echo "  本地ClashX出口: 183.192.93.255"
echo "  服务器代理出口: $PROXY_IP"
echo "  Cookie获取IP: 183.192.93.255"
echo "  → IP一致性: $([ "$PROXY_IP" = "183.192.93.255" ] && echo "✅ 匹配" || echo "⚠️  不匹配")"
echo ""
echo "📝 服务管理："
echo "  查看Clash状态: ssh $SERVER 'systemctl status clash'"
echo "  查看Clash日志: ssh $SERVER 'journalctl -u clash -f'"
echo "  重启Clash: ssh $SERVER 'systemctl restart clash'"
echo "  停止Clash: ssh $SERVER 'systemctl stop clash'"
echo ""
echo "🔍 测试命令："
echo "  测试代理: ssh $SERVER 'curl -x http://127.0.0.1:7890 https://ifconfig.me'"
echo "  测试API: curl https://google-api.aihang365.com/api/cookies/status | jq ."
echo ""
