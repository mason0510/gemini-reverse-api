#!/bin/bash
# 步骤1验证脚本 - 检查当前IP是否为美国

echo "==============================================="
echo "  步骤1: 验证ClashX节点"
echo "==============================================="
echo ""
echo "📋 操作步骤："
echo "1. 打开ClashX菜单"
echo "2. 选择一个美国节点（USA/US/United States）"
echo "3. 确保是全局模式（Global Mode）"
echo ""
echo "按回车键继续验证..."
read

echo "🔍 正在检查当前出口IP..."
CURRENT_IP=$(curl -s https://ipinfo.io/json)
echo "$CURRENT_IP" | jq .

COUNTRY=$(echo "$CURRENT_IP" | jq -r .country)
IP=$(echo "$CURRENT_IP" | jq -r .ip)

echo ""
if [ "$COUNTRY" = "US" ]; then
    echo "✅ 成功！当前使用美国IP: $IP"
    echo ""
    echo "继续执行步骤2..."
else
    echo "❌ 当前IP不是美国: $COUNTRY"
    echo "❌ 当前IP: $IP"
    echo ""
    echo "⚠️  请切换ClashX到美国节点后重新运行此脚本"
    exit 1
fi
