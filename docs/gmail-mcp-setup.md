# 使用 Gmail MCP 让 Agent 查看/管理邮件

可以用 **Gmail MCP** 把 Cursor（或其它支持 MCP 的 agent）连到 Gmail，实现读邮件、搜索、发信、标签/过滤器等。推荐使用 **@gongrzhe/server-gmail-autoauth-mcp**（OAuth 自动打开浏览器登录，凭证存于 `~/.gmail-mcp/`）。

---

## 快速开始（约 2 分钟）

### 1. 创建 Google OAuth 凭据

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)
2. **新建项目** 或选择现有项目
3. **APIs & Services → Library**，搜索并启用 **Gmail API**
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. 应用类型选择 **Desktop app**
6. 创建后**下载 JSON**，重命名为 **`gcp-oauth.keys.json`**
7. 将文件放到 `~/.gmail-mcp/`：

   ```bash
   mkdir -p ~/.gmail-mcp
   cp /path/to/downloaded.json ~/.gmail-mcp/gcp-oauth.keys.json
   ```

### 2. 首次登录（授权）

```bash
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
```

会打开浏览器，用你的 Gmail 登录并同意授权。凭证保存到 `~/.gmail-mcp/credentials.json`。

### 3. 重启 Cursor

项目 `.cursor/mcp.json` 已配置 Gmail MCP，重启 Cursor 即可使用。

---

## 详细说明

### 1. 准备 Google 凭证（同上）

1. **创建/选择 Google Cloud 项目**
   - 打开 [Google Cloud Console](https://console.cloud.google.com/)
   - 新建项目或选已有项目

2. **启用 Gmail API**
   - 在项目中进入 **APIs & Services → Library**
   - 搜索并启用 **Gmail API**

3. **创建 OAuth 2.0 凭据**
   - **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - 应用类型选 **Desktop app**（推荐，最简单）
   - 或选 **Web application**，需在 **Authorized redirect URIs** 中添加：`http://localhost:3000/oauth2callback`
   - 创建后下载 JSON，重命名为 **`gcp-oauth.keys.json`**

---

## 2. 登录（首次认证）

凭证可放当前目录或全局目录，推荐全局：

```bash
mkdir -p ~/.gmail-mcp
mv /path/to/gcp-oauth.keys.json ~/.gmail-mcp/

npx @gongrzhe/server-gmail-autoauth-mcp auth
```

或把 `gcp-oauth.keys.json` 放在当前目录后直接执行：

```bash
npx @gongrzhe/server-gmail-autoauth-mcp auth
```

流程会：

- 在当前目录或 `~/.gmail-mcp/` 查找 `gcp-oauth.keys.json`
- 若在当前目录找到，会复制到 `~/.gmail-mcp/`
- 自动打开浏览器完成 Google 登录与授权
- 将凭证保存为 `~/.gmail-mcp/credentials.json`，之后任意目录都可使用

---

## 3. 在 Cursor 里配置 Gmail MCP

**方法 A：用项目示例配置**

项目根目录的 `.cursor/mcp.json.example` 里已包含 Gmail 条目。复制为正式配置：

```bash
mkdir -p .cursor
cp .cursor/mcp.json.example .cursor/mcp.json
```

若只需 Gmail，可把 `mcp.json` 改成只保留 `gmail` 的 `mcpServers` 条目。然后重启 Cursor 或在 **Settings → Features → MCP** 中确认已加载。

**方法 B：在 Cursor 里手动添加**

在 **Cursor Settings → Features → MCP** 中 **Add New MCP Server**，名字例如 `gmail`，配置：

```json
{
  "mcpServers": {
    "gmail": {
      "command": "npx",
      "args": ["@gongrzhe/server-gmail-autoauth-mcp"]
    }
  }
}
```

---

## 4. 在 Cursor 里用 Agent 操作 Gmail

配置并完成一次 `auth` 后，在对话里可直接说例如：

- “列出我收件箱最近 10 封邮件”
- “搜索来自 xxx@example.com 的邮件”
- “把某封邮件的内容发给我”
- “发一封邮件给 xxx，主题是 ……”

Agent 会通过 MCP 调用 Gmail 的工具，例如：

| 工具 | 说明 |
|------|------|
| `search_emails` | 按 Gmail 搜索语法查邮件 |
| `read_email` | 按 ID 读单封邮件（含附件信息） |
| `list_email_labels` | 列出所有标签 |
| `send_email` | 发信（支持附件、HTML） |
| `draft_email` | 创建草稿 |
| `modify_email` | 加/删标签（移动、归档等） |
| `download_attachment` | 下载附件到本地 |
| `create_filter` / `list_filters` | 创建、查看过滤器 |

搜索语法示例：`from:xxx@example.com after:2024/01/01 has:attachment`。

---

## 5. 安全与故障排查

- 凭证保存在本机 `~/.gmail-mcp/`，不要提交到版本控制。
- 若提示找不到 OAuth 密钥，确认 `gcp-oauth.keys.json` 在 **当前目录** 或 **`~/.gmail-mcp/`**。
- 若用 Web 应用类型，确认已添加重定向 URI：`http://localhost:3000/oauth2callback`。
- 认证时若端口 3000 被占用，先释放该端口再执行 `auth`。

更多说明与工具参数见：[Gmail-MCP-Server README](https://github.com/GongRzhe/Gmail-MCP-Server)。
