#!/bin/bash
# Gmail MCP 首次登录 - 个人账号
# 1. 在 ~/.gmail-mcp/ 放入 gcp-oauth.keys.json（从 Google Cloud Console 下载）
# 2. 运行: ./scripts/gmail-mcp-auth.sh

set -e
DIR=~/.gmail-mcp
mkdir -p "$DIR"

if [ ! -f "$DIR/gcp-oauth.keys.json" ]; then
  echo "请先在 $DIR 放入 gcp-oauth.keys.json"
  echo ""
  echo "获取步骤："
  echo "  1. 打开 https://console.cloud.google.com/"
  echo "  2. 创建/选择项目 → APIs & Services → Library → 启用 Gmail API"
  echo "  3. Credentials → Create Credentials → OAuth client ID"
  echo "  4. 应用类型选 Desktop app"
  echo "  5. 下载 JSON，重命名为 gcp-oauth.keys.json，放入 $DIR"
  echo ""
  exit 1
fi

echo "开始 Gmail 登录（会打开浏览器）..."
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
