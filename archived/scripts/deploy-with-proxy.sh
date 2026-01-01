#!/bin/bash
# 完整的代理部署流程

echo "==============================================="
echo "  Gemini Cookie代理部署完整流程"
echo "==============================================="
echo ""
echo "📋 问题说明:"
echo "  Cookie获取IP: 183.192.93.255 (ClashX代理)"
echo "  服务器IP: 82.29.54.80"
echo "  → IP不一致导致Cookie验证失败"
echo ""
echo "==============================================="
echo "  解决方案: 使用SSH隧道让服务器走代理"
echo "==============================================="
echo ""

# 步骤1: 创建SSH隧道
echo "步骤1: 创建SSH隧道（新开一个终端窗口执行）"
echo "----------------------------------------"
echo "cd /Users/houzi/code/02-production/my-reverse-api/gemini-text"
echo "./ssh-proxy-tunnel.sh"
echo ""
echo "⚠️  保持该终端窗口运行！"
echo ""
read -p "按回车键继续（确保SSH隧道已建立）..."

# 步骤2: 验证隧道
echo ""
echo "步骤2: 验证SSH隧道是否工作"
echo "----------------------------------------"
ssh root@82.29.54.80 "curl -x http://127.0.0.1:8118 -s https://ifconfig.me"
PROXY_IP=$(ssh root@82.29.54.80 "curl -x http://127.0.0.1:8118 -s https://ifconfig.me")
echo "通过代理的出口IP: $PROXY_IP"
echo ""
if [ "$PROXY_IP" != "183.192.93.255" ]; then
    echo "❌ 警告: 代理IP不匹配，期望: 183.192.93.255"
    read -p "是否继续? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

# 步骤3: 使用代理模式部署
echo ""
echo "步骤3: 使用代理模式重新部署容器"
echo "----------------------------------------"
read -p "开始部署? (y/n): " DEPLOY
if [ "$DEPLOY" = "y" ]; then
    USE_PROXY=true ./update-cookies.sh
fi

# 步骤4: 测试API
echo ""
echo "步骤4: 测试API功能"
echo "----------------------------------------"
echo "等待5秒让容器完全启动..."
sleep 5

echo ""
echo "测试文本生成API..."
curl -X POST https://google-api.aihang365.com/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello", "model": "gemini-2.5-flash"}' \
  2>/dev/null | jq .

echo ""
echo "==============================================="
echo "  部署完成"
echo "==============================================="
echo ""
echo "📝 注意事项:"
echo "  1. SSH隧道窗口必须保持运行"
echo "  2. 如果ClashX重启，需要重新建立隧道"
echo "  3. 长期方案：在服务器上配置xray客户端"
echo ""
echo "🔗 详细文档: PROXY_SETUP.md"
