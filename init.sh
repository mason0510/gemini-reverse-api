#!/bin/bash
# Project: gemini-reverse-api
# Purpose: 快速重现开发环境并检查项目状态
# Updated: 2025-12-18

set -e

echo "🚀 Gemini Reverse API - 环境检查"
echo "=================================="

# Step 1: 检查项目状态
echo ""
echo "📁 项目目录: $(pwd)"
echo ""

# Step 2: 检查feature_list.json
if [ -f "feature_list.json" ]; then
    echo "📊 功能进度:"
    total=$(cat feature_list.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total_features'])")
    completed=$(cat feature_list.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['completed'])")
    in_progress=$(cat feature_list.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('in_progress', 0))")
    pending=$((total - completed - in_progress))
    percent=$((completed * 100 / total))
    echo "   总功能: $total"
    echo "   已完成: $completed ($percent%)"
    echo "   进行中: $in_progress"
    echo "   待办:   $pending"
else
    echo "⚠️  feature_list.json 不存在"
fi

# Step 3: 检查远程服务状态
echo ""
echo "🌐 远程服务状态:"
if curl -s --connect-timeout 3 https://google-api.aihang365.com/health > /dev/null 2>&1; then
    echo "   ✅ 服务运行中 (82.29.54.80:8100)"
    cookie_status=$(curl -s https://google-api.aihang365.com/api/cookies/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('有效' if d.get('valid') else '未配置')" 2>/dev/null || echo "未知")
    echo "   🔐 Cookie状态: $cookie_status"
else
    echo "   ❌ 服务未运行或不可达"
fi

# Step 4: Git状态
echo ""
echo "📝 Git状态:"
if [ -d ".git" ]; then
    branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo "   分支: $branch"
    changes=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$changes" -gt 0 ]; then
        echo "   ⚠️  有 $changes 个未提交的变更"
    else
        echo "   ✅ 工作区干净"
    fi
    echo ""
    echo "   最近提交:"
    git log --oneline -3 2>/dev/null | sed 's/^/   /'
else
    echo "   ⚠️  非Git仓库"
fi

# Step 5: 待办任务
echo ""
echo "🎯 待办任务 (高优先级):"
if [ -f "feature_list.json" ]; then
    python3 -c "
import json
with open('feature_list.json') as f:
    data = json.load(f)
for feat in data['features']:
    if not feat['passes'] and feat['priority'] == 'high':
        print(f\"   #{feat['id']}: {feat['description']}\")
" 2>/dev/null || echo "   无法解析"
fi

echo ""
echo "=================================="
echo "✅ 环境检查完成"
echo ""
echo "快速命令:"
echo "   部署更新: cat api_server.py | ssh root@82.29.54.80 'docker exec -i google-reverse tee /app/api_server.py > /dev/null' && ssh root@82.29.54.80 'docker restart google-reverse'"
echo "   查看日志: ssh root@82.29.54.80 'docker logs google-reverse --tail 20'"
echo ""
