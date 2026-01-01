#!/bin/bash
# 在服务器上安装Clash并配置代理

echo "==============================================="
echo "  服务器Clash代理安装脚本"
echo "==============================================="
echo ""

SERVER="root@82.29.54.80"

echo "📦 步骤1: 下载Clash客户端"
echo "----------------------------------------"
ssh $SERVER << 'EOF'
set -e

# 创建clash目录
mkdir -p /opt/clash
cd /opt/clash

# 下载clash-linux-amd64（如果没有）
if [ ! -f "clash-linux-amd64" ]; then
    echo "下载Clash..."
    wget https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz
    gunzip clash-linux-amd64-v1.18.0.gz
    mv clash-linux-amd64-v1.18.0 clash-linux-amd64
    chmod +x clash-linux-amd64
fi

echo "✅ Clash客户端已准备"
EOF

echo ""
echo "📝 步骤2: 配置Clash"
echo "----------------------------------------"
echo ""
echo "请提供你的Clash订阅链接或配置文件URL："
read -p "订阅链接: " CLASH_URL

if [ -z "$CLASH_URL" ]; then
    echo "❌ 未提供订阅链接"
    echo ""
    echo "手动配置步骤："
    echo "1. ssh $SERVER"
    echo "2. vim /opt/clash/config.yaml"
    echo "3. 粘贴你的Clash配置"
    exit 1
fi

echo "下载配置文件..."
ssh $SERVER << EOF
cd /opt/clash
curl -L "$CLASH_URL" -o config.yaml
echo "✅ 配置文件已下载"
EOF

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
ExecStart=/opt/clash/clash-linux-amd64 -d /opt/clash
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable clash
systemctl start clash

echo "✅ Clash服务已启动"
EOF

echo ""
echo "🔍 步骤4: 验证Clash代理"
echo "----------------------------------------"
ssh $SERVER << 'EOF'
sleep 3
echo "测试代理连接..."
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
PROXY_IP=$(curl -s https://ifconfig.me)
echo "通过代理的出口IP: $PROXY_IP"

# 测试访问Google
if curl -s --max-time 5 https://www.google.com > /dev/null; then
    echo "✅ 代理工作正常"
else
    echo "❌ 代理测试失败"
fi
EOF

echo ""
echo "🐳 步骤5: 配置Docker容器使用代理"
echo "----------------------------------------"
echo ""
echo "现在重新部署容器，使用代理..."

# 使用代理模式部署
USE_PROXY=true ./update-cookies.sh

echo ""
echo "==============================================="
echo "  🎉 安装完成！"
echo "==============================================="
echo ""
echo "📝 服务管理命令："
echo "  启动Clash: ssh $SERVER 'systemctl start clash'"
echo "  停止Clash: ssh $SERVER 'systemctl stop clash'"
echo "  查看状态: ssh $SERVER 'systemctl status clash'"
echo "  查看日志: ssh $SERVER 'journalctl -u clash -f'"
echo ""
echo "🔍 验证代理："
echo "  ssh $SERVER 'curl -x http://127.0.0.1:7890 https://ifconfig.me'"
echo ""
