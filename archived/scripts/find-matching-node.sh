#!/bin/bash
# 切换服务器Clash到所有可用节点并测试出口IP

echo "测试所有节点的出口IP，找到183.192.93.255..."
echo ""

NODES=(
  "HK - 香港原生 - 04"
  "HK - 香港CMHK - 02"
  "HK - 香港HKBN - 03"
  "HK - 香港HGC - 05"
  "HK - 香港HKBN - 06"
  "HK - 香港HKT - 07"
  "HK - 香港HGC - 08"
  "HK - 香港WTT - 09"
  "HK - 香港HKT - 10"
)

for node in "${NODES[@]}"; do
  echo -n "测试节点: $node ... "

  # 切换节点
  ssh root@82.29.54.80 "curl -s -X PUT http://127.0.0.1:9090/proxies/%F0%9F%94%B0%20%E8%8A%82%E7%82%B9%E9%80%89%E6%8B%A9 -H 'Content-Type: application/json' -d '{\"name\":\"$node\"}'" > /dev/null

  sleep 2

  # 测试出口IP
  IP=$(ssh root@82.29.54.80 "curl -x http://127.0.0.1:7890 -s --max-time 5 https://ifconfig.me 2>/dev/null")

  echo "出口IP: $IP"

  if [ "$IP" = "183.192.93.255" ]; then
    echo ""
    echo "✅ 找到匹配节点: $node"
    echo "✅ 出口IP: $IP"
    exit 0
  fi
done

echo ""
echo "❌ 未找到出口IP为183.192.93.255的节点"
echo "请检查本地ClashX使用的节点"
