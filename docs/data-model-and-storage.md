# Phase 1：每日卦例 GitHub 保存与 AI 分析

## 1. 当前阶段的边界

Phase 1 是验证每日排卦、记录、保存和 AI 分析流程是否好用，不是最终产品架构。

- **Public `symbi/liuyao-learning-app`**：保存 HTML 应用、Cloudflare Pages Functions、课程整理笔记、规则、课堂案例，以及 Phase 1 每日卦例 JSON。
- **Private `symbi/liuyao-learning-raw`**：继续保存课堂原始录音、ASR 转录、原始 PDF 和未整理来源资料。每日卦例不再写入这里。
- **当前 HTML 记录存储**：继续使用 GitHub Contents API 保存每日 JSON。
- **知识图谱数据库**：Phase 1 另行建立 Neo4j AuraDB，Importer 将整理后的课程资料、案例和选定参考项目增量同步进去。Neo4j 是图数据库，可以保存 Case、Lesson、Chunk、Concept、Rule 节点和关系；不需要为知识库再部署 Supabase/PostgreSQL。
- **Supabase 不是必选项**：只有将来需要多用户身份、严格用户隔离或典型关系型业务数据时才重新评估。实际职责见 `docs/phase1-operating-model.md`。

每日卦例和 Memo 会公开。Public 文件可能被任何人查看、复制或 Fork；即使日后删除，也无法保证其他副本消失。不要在 Memo 写入密码、访问令牌、公司机密或不希望公开的个人信息。

## 2. 每日记录行为

- 页面默认打开日本当地日期 `Asia/Tokyo`。
- 默认 Category 为「今日运势（每日卦）」，问题栏留空。
- 每个日期只有一条 `dailyFortune`。重复打开、修改卦盘或更新 Memo 都更新同一条每日记录。
- 其他 Category 作为独立 `additionalQuestions`，每条有自己的 ID、Category、问题文字和六爻快照。
- Memo 属于日期本身，保存在顶层 `dailyMemo`，不跟某个额外问题绑定。
- 页面切换日期时读取该日期文件；没有文件则显示空白每日卦。
- 只有 GitHub 写入成功后才显示「已保存到 GitHub」。网络失败不得假报成功。

## 3. 文件路径

一天一个文件：

```text
liuyao-learning-app/
└── daily-records/
    └── 2026/
        └── 11/
            └── 2026-11-16.json
```

文件内容示例：

```json
{
  "schemaVersion": 1,
  "recordDate": "2026-11-16",
  "timezone": "Asia/Tokyo",
  "dailyFortune": {
    "id": "daily-2026-11-16",
    "question": { "category": "daily", "categoryLabel": "今日运势（每日卦）", "text": "" },
    "date": "2026-11-16",
    "lines": []
  },
  "additionalQuestions": [],
  "dailyMemo": "",
  "createdAt": "2026-11-16T09:00:00+09:00",
  "updatedAt": "2026-11-16T09:00:00+09:00"
}
```

`lines` 在真实文件中保存 V80 已计算/手工填写的六爻字段；示例中的空数组只是占位，不代表有效卦盘。

## 4. Phase 1 部署结构

```text
浏览器
  └── Cloudflare Pages（同源静态页面 + Pages Functions）
        ├── /                  -> index.html（V80 页面）
        └── /api/*             -> functions/api/[[path]].js
                                  ├── GitHub App OAuth 登录
                                  ├── 当前用户状态 / 退出
                                  └── 只读写 daily-records/YYYY/MM/YYYY-MM-DD.json

GitHub Public Repository：symbi/liuyao-learning-app
  ├── index.html
  ├── functions/api/[[path]].js
  └── daily-records/...
```

使用 Cloudflare Pages 同时托管页面和 API，保持同源 Cookie，避免 GitHub Pages 与独立 Worker 之间的跨站 Cookie 问题。GitHub 仍然是代码与每日 JSON 的版本化存储位置。

## 5. 授权与安全

- 创建 GitHub App，只安装到 `symbi/liuyao-learning-app`。
- Repository permissions：Contents = Read and write；Metadata = Read-only。
- GitHub 登录只允许指定的仓库所有者账户（当前配置 `symbi`）。
- OAuth code exchange、PKCE verifier、Client Secret、短期 user access token 和 refresh token 全部由 Pages Function 服务端处理，并用 Cloudflare KV 保存 OAuth state/session。
- 前端不保存 GitHub Token，不出现 PAT 输入框。
- Function 只允许操作固定仓库和 `daily-records/` 路径，不接受前端传入任意 repository/path。
- 更新文件时，前端带上读取时的 blob SHA；服务端再次核对当前 SHA。若文件已被其他设备更新，返回 409 冲突，不静默覆盖。
- Pages Function 仅允许同源请求；设置 GitHub App Secret 为 Cloudflare Secret，不提交到 GitHub。

## 6. ChatGPT 分析流程

用户提出「分析今天的卦」或指定日期时，ChatGPT 通过已连接的 GitHub 连接器读取 `daily-records/YYYY/MM/YYYY-MM-DD.json`，再按 Category / Real Question 检索 Public Learning 中的课程笔记、规则和课堂案例。分析时区分课程明确、老师课堂案例、外部参考和 AI 综合推理。保存成功不会自动触发分析，用户发出请求后再读取。

## 7. Phase 2 迁移原则

Phase 2 再增加 Login 和数据库（例如 Supabase）。前端页面不直接依赖 GitHub Contents API；读写统一通过 `/api/records/:date` 这一层接口。以后只替换服务端存储实现和身份认证，不需要重写排盘、六爻计算和主要页面。