# 使用 Outlook MCP 让 Agent 查看邮件

> 若要用 **Gmail**，见 [Gmail MCP 配置](gmail-mcp-setup.md)。

可以用 **Outlook MCP** 把 Cursor（或其它支持 MCP 的 agent）连到 Microsoft Outlook，用来查看、搜索、管理邮件。有两种常见做法：

1. **在 Cursor 里用社区 MCP 服务器（推荐）**：用 `@softeria/ms-365-mcp-server`，支持个人/工作账号，无需加入微软预览计划。
2. **微软官方 Mail MCP**：属于 Microsoft Agent 365，需要 Frontier 预览资格，主要面向 Copilot Studio 等微软生态。

下面以 **Cursor + 社区 Outlook MCP** 为例。

---

## 方式一：Cursor + ms-365-mcp-server（推荐）

[ms-365-mcp-server](https://github.com/softeria/ms-365-mcp-server) 通过 Microsoft Graph 提供 Outlook 邮件、日历、OneDrive 等能力，在 Cursor 里配置成 MCP 后，agent 就能用“查邮件”等工具。

### 1. 在 Cursor 里配置 MCP

**方法 A：用项目里的示例配置**

1. 复制示例配置并改名为 Cursor 使用的配置：
   ```bash
   cp .cursor/mcp.json.example .cursor/mcp.json
   ```
2. 如无 `.cursor` 目录，先建一个：`mkdir -p .cursor`，再复制上述文件。
3. 重启 Cursor，或到 **Settings → Features → MCP** 里确认已加载。

**方法 B：在 Cursor 里手动添加**

1. 打开 **Cursor Settings → Features → MCP**。
2. 点击 **Add New MCP Server**。
3. 填一个名字（例如 `ms365`），然后使用下面任一配置。

**仅邮件（个人或工作账号）：**

```json
{
  "mcpServers": {
    "ms365": {
      "command": "npx",
      "args": ["-y", "@softeria/ms-365-mcp-server", "--preset", "mail"]
    }
  }
}
```

**工作/学校账号（含 Teams、共享邮箱等）：**

```json
{
  "mcpServers": {
    "ms365": {
      "command": "npx",
      "args": ["-y", "@softeria/ms-365-mcp-server", "--preset", "mail", "--org-mode"]
    }
  }
}
```

把上面任意一段放进 `.cursor/mcp.json` 的 `mcpServers` 里，或通过 Cursor 的 MCP 界面等效添加即可。

### 2. 登录 Microsoft 账号

第一次使用前需要登录：

1. 在终端执行：
   ```bash
   npx @softeria/ms-365-mcp-server --preset mail --login
   ```
   （若用工作账号，加上 `--org-mode`：  
   `npx @softeria/ms-365-mcp-server --preset mail --org-mode --login`）

2. 终端会打印一个 URL 和一段**设备码**。用浏览器打开 URL，输入设备码，用要查邮件的 Microsoft 账号登录并授权。

3. 登录成功后，凭证会缓存在本机（优先用系统钥匙串）。之后在 Cursor 里用该 MCP 时，agent 就可以直接查邮件，无需再登录。

### 3. 在 Cursor 里用 Agent 查邮件

配置并登录完成后，在 Cursor 的 Agent / Chat 里可以直接说例如：

- “列出我收件箱最近 10 封邮件”
- “搜索主题里带 ‘会议’ 的邮件”
- “把某封邮件的正文内容发给我”

Agent 会通过 MCP 调用 Outlook 的工具，例如：

- `list-mail-messages`：列出邮件
- `list-mail-folders`：列出文件夹
- `list-mail-folder-messages`：按文件夹列邮件
- `get-mail-message`：获取单封邮件内容
- `send-mail`、`create-draft-email` 等（若未开只读模式）

这样就把 **agent 通过 Outlook MCP 接到 Outlook，用于 examine the emails**。

### 4. 可选：只读模式

若只想“查看”邮件、不让 agent 发信或删信，可加 `--read-only`：

```json
{
  "mcpServers": {
    "ms365": {
      "command": "npx",
      "args": ["-y", "@softeria/ms-365-mcp-server", "--preset", "mail", "--read-only"]
    }
  }
}
```

---

## 方式二：微软官方 Mail MCP（Microsoft Agent 365）

微软在 [Microsoft Agent 365](https://learn.microsoft.com/en-us/microsoft-agent-365/mcp-server-reference/mail) 里提供了官方 **Mail MCP**（`mcp_MailTools`），能力包括：

- 创建/发送草稿、发送邮件
- 获取、删除、更新邮件
- 回复/全部回复
- 用 KQL 搜索邮件等

要点：

- 需要参加 [Frontier 预览计划](https://adoption.microsoft.com/copilot/frontier-program/) 才能用 Microsoft Agent 365。
- 主要集成在微软自家产品（如 Copilot Studio），不是给 Cursor 直接装一个“Outlook MCP 插件”就能用。
- 若你已经在用 Agent 365，可以在其配置里启用 Mail MCP，让微软的 agent 去 examine emails。

若你的目标是在 **Cursor 里** 用 agent 查 Outlook 邮件，优先用上面的 **方式一（ms-365-mcp-server）** 即可。

---

## 小结

| 目标                     | 建议做法                          |
|--------------------------|-----------------------------------|
| 在 Cursor 里用 agent 查邮件 | 用 **Outlook MCP**：ms-365-mcp-server |
| 只查不发/不删             | 加 `--preset mail --read-only`   |
| 工作/学校账号、共享邮箱   | 加 `--org-mode` 并先 `--login`   |
| 微软自家 Agent 365 生态   | 用官方 Mail MCP（需 Frontier）   |

按上面在 Cursor 里配置好 MCP 并完成一次设备码登录，就可以用 **Outlook MCP** 让 agent 稳定地 **examine the emails**。
