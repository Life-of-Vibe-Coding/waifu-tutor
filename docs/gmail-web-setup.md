# Gmail 集成配置（Web App）

Waifu Tutor 使用 **Google Gmail API + OAuth2** 实现读收件箱、发邮件。

## 配置步骤

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)
2. 新建项目或选择现有项目
3. **APIs & Services → Library** → 启用 **Gmail API**
4. **APIs & Services → Credentials** → **Create Credentials** → **OAuth client ID**
5. 应用类型选 **Web application**
6. **Authorized redirect URIs** 添加：`http://localhost:3000/api/gmail/callback`
7. 复制 Client ID 和 Client Secret 到 `.env`：

```env
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxx
GMAIL_REDIRECT_URI=http://localhost:3000/api/gmail/callback
GMAIL_SUCCESS_URL=/
```

## 使用

1. 点击右上角邮件图标
2. 点击 **Connect Gmail**，完成 Google 登录授权
3. 授权后显示「Connected」

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/gmail/auth` | 获取 Google 登录 URL |
| `GET /api/gmail/callback` | OAuth 回调 |
| `GET /api/gmail/status` | 检查是否已连接 |
| `GET /api/gmail/mail` | 列出邮件 |
| `POST /api/gmail/mail/send` | 发送邮件 |
