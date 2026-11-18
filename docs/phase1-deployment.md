# Phase 1 部署说明（Cloudflare Pages + GitHub App）

## 当前代码

- `index.html`：V80 单页应用，保留原有排盘逻辑，增加 GitHub 连接、按日读取和保存。
- `functions/api/[[path]].js`：Cloudflare Pages Function，处理 OAuth、会话和每日 JSON 的 GitHub 读写。
- `daily-records/`：Public GitHub 上的每日记录目录。

## 1. 创建 GitHub App

在 GitHub 账户 `symbi` 下创建一个 GitHub App：

- App name：例如 `Liuyao Learning Phase 1`。
- Homepage URL：部署后的 Cloudflare Pages 网站 URL。
- Callback URL：`https://<你的-pages-域名>/api/auth/callback`。
- User authorization：启用用户授权（OAuth）流程。
- Repository permissions：`Contents: Read and write`；`Metadata: Read-only`。
- 安装范围：只选择 `symbi/liuyao-learning-app` 这一个仓库。
- 不需要 Webhook，不需要组织权限，不要授予其他仓库访问权限。

记录 GitHub App 的 Client ID，并生成 Client Secret。**不要把 Client Secret 发到聊天、写进 HTML 或提交到 GitHub。**

## 2. 创建 Cloudflare Pages 项目

1. 在 Cloudflare Dashboard 创建 Pages 项目，连接 GitHub 仓库 `symbi/liuyao-learning-app`。
2. Framework preset 选 `None`；Build command 留空；Build output directory 填 `.`（仓库根目录）。
3. 部署完成后，复制 Pages 域名，例如 `https://<project>.pages.dev`。
4. 回到 GitHub App 设置，把 Homepage URL 和 Callback URL 更新为真实 Pages 域名。

Cloudflare Pages 同时托管 `index.html` 和 `/api/*` Functions，页面与 API 同源，避免跨站 Cookie。

## 3. 创建 KV 并配置 Pages

1. 在 Cloudflare Workers & Pages → KV 创建一个 Namespace，例如 `LIUYAO_SESSIONS`。
2. 打开 Pages 项目 Settings → Functions → KV namespace bindings。
3. 添加 binding：Variable name `SESSIONS`，Namespace 选择刚创建的 KV。
4. 在 Settings → Variables and Secrets 配置 Production 环境变量：
   - `GITHUB_APP_CLIENT_ID`：GitHub App Client ID。
   - `GITHUB_APP_CLIENT_SECRET`：GitHub App Client Secret（必须设为 Secret）。
   - `GITHUB_APP_REDIRECT_URI`：`https://<你的-pages-域名>/api/auth/callback`。
   - `ALLOWED_GITHUB_LOGIN`：`symbi`。
5. 保存设置后重新部署 Pages 项目。

## 4. 首次验收

1. 打开 Pages 网站，点击「连接 GitHub」。
2. GitHub 授权页应显示刚创建的 App；确认授权账户是 `symbi`。
3. 返回页面后，状态应显示 GitHub 已连接。
4. 保存一条测试卦例，确认仓库生成 `daily-records/YYYY/MM/YYYY-MM-DD.json`。
5. 刷新页面，确认同一天记录被重新读取。
6. 修改 Memo 再保存，确认仍更新同一个 JSON 文件，而不是创建第二份。
7. 新增一个非 daily Category 的额外问题，确认它进入 `additionalQuestions`，且不覆盖 `dailyFortune`。
8. 切换到没有记录的日期，确认页面显示空白每日卦；切回原日期确认内容恢复。

## 5. 安全与发布注意事项

- `daily-records/` 在 Public 仓库，数据公开；不要写入敏感内容。
- 不要将 Client Secret、GitHub Token、KV 内容或任何会话数据提交到仓库。
- 如果 GitHub App 权限、Callback URL 或 KV binding 改动，需重新部署并重新授权测试。
- GitHub 保存失败时页面显示失败状态，不应显示保存成功。
- 如果两台设备同时修改同一天记录，SHA 不匹配会返回冲突；当前版本不会静默覆盖。重新加载最新版本后再编辑保存。

## 当前 HTML 保存服务的边界

当前 Cloudflare Pages + Pages Functions 只负责网页托管、GitHub OAuth 和每日 JSON 文件读写；这部分不包含 Neo4j、Embedding、GraphRAG 或最终分析模型。

知识库建设是独立的 Phase 1 工作流：在用户 Mac 运行 Python Importer，调用 Gemini 生成模型做候选结构抽取、调用 Embedding 模型生成向量，并写入 Neo4j AuraDB。实施细节与后续在线分析服务见 [Phase 1 实际运行架构](phase1-operating-model.md)。本阶段不需要部署自有 Backend Container 或 Supabase。