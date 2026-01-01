#!/bin/bash
# 从浏览器Cookie文件快速提取并更新

COOKIE_FILE="${1:-$HOME/Downloads/aistudio.google.com_cookies.txt}"

if [ ! -f "$COOKIE_FILE" ]; then
    echo "❌ Cookie文件不存在: $COOKIE_FILE"
    echo "用法: $0 <cookie_file_path>"
    exit 1
fi

echo "📄 读取Cookie文件: $COOKIE_FILE"

# 提取Cookie值
PSID=$(grep "__Secure-1PSID" "$COOKIE_FILE" | awk '{print $7}')
PSIDCC=$(grep "__Secure-1PSIDCC" "$COOKIE_FILE" | awk '{print $7}')
PSIDTS=$(grep "__Secure-1PSIDTS" "$COOKIE_FILE" | awk '{print $7}')

if [ -z "$PSID" ] || [ -z "$PSIDCC" ] || [ -z "$PSIDTS" ]; then
    echo "❌ Cookie提取失败，请检查文件格式"
    exit 1
fi

echo "✅ Cookie提取成功"
echo "  PSID: ${PSID:0:50}..."
echo "  PSIDCC: ${PSIDCC:0:50}..."
echo "  PSIDTS: ${PSIDTS:0:50}..."

# 更新.env文件
cat > .env << EOF
SECURE_1PSID=$PSID
SECURE_1PSIDCC=$PSIDCC
SECURE_1PSIDTS=$PSIDTS
GOOGLE_AI_API_KEY=AIzaSyAvRND5W3EKCGxwG17siL7Xt1Gg5nwI1bw
EOF

echo "✅ 已更新本地.env文件"

# 询问是否部署
read -p "是否立即部署到服务器？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 开始部署..."
    ./update-cookies.sh
fi
