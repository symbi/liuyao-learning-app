# Phase 1：每日卦例 GitHub 保存与 AI 分析

## 1. 当前阶段的边界

Phase 1 是验证每日排卦、记录、保存和 AI 分析流程是否好用，不是最终产品架构。

- **Public `symbi/liuyao-learning-app`**：保存 HTML 应用、Cloudflare Pages Functions、课程整理笔记、规则、课堂案例，以及 Phase 1 每日卦例 JSON。
- **Private `symbi/liuyao-learning-raw`**：继续保存课堂原始录音、ASR 转录、原始 PDF 和未整理来源资料。每日卦例不再写入这里。
- **当前 HTML 记录存储**：继续使用 GitHub Contents API 保存每日 JSON；每一条卦例另有一份由 JavaScript 生成的 Markdown 文字资料作为配套副本。JSON 是权威原始数据，Markdown 是可独立交给其他 AI 阅读的衍生文件，不是 AI 模型分析结果。
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

## 7. HTML 课堂案例与原始课程的匹配

HTML 保存的课堂案例需要与老师实际讲过的原始卦例建立可追溯关联。后续 ChatGPT 或 Importer 处理案例时，应执行以下流程：

1. 读取 HTML 案例中的卦盘快照、占问内容、Category、备注和记录 ID。
2. 在 `docs/lessons/` 的课程整理稿及 `materials/class-cases/lesson-XX/` 中寻找候选案例；优先比对卦名、上下卦、世应、六亲、纳甲地支、动爻、变爻、日月信息和问事背景。
3. 再回查 Private raw 对应课次的原始 ASR/录音，确认老师讲解的上下文、原始表述和可用段落/时间戳。
4. 匹配结果必须保留课程编号、课程笔记路径、原始来源仓库/路径及转录定位；有对应案例 JSON 时建立双向关联。
5. 只有卦盘与问事背景足以确认是同一案例时，才标记 `verified`。相似但不能确认的标记 `needs_review`；不同来源存在冲突的标记 `disputed`；当前资料找不到的标记 `not_found`。
6. 不得仅凭 Category、卦名相似或单一爻象强行匹配；不得把 ASR 识别错误、AI 推断或用户个人分析写成老师原话。

关联链为：HTML 案例记录 → 课堂案例 JSON → 对应课程笔记 → Private raw 原始转录/录音位置 → 老师分析摘要。课程笔记保留整堂课的知识脉络，单个案例独立保存。课程案例的核对状态应在检索和分析结果中显示。

## 8. 后续在线化原则

当前 HTML 的每日记录仍由 Pages Function 写入 GitHub JSON；Phase 1 Importer 再把这些记录同步为 Neo4j 中的 Case 节点与知识关系。若后续希望 HTML 直接读写 Neo4j，并在页面内运行知识检索和 AI 分析，可在 Phase 2 增加 Python FastAPI 服务（初期一个 Cloud Run Container），由它统一处理 Case API、GraphRAG 检索、规则引擎和生成模型调用。Supabase 仍为可选项，不是默认必须迁移的目标。
## 9. 每条卦例的 Markdown 文字资料

JSON 继续作为唯一权威原始记录；每一条具体卦例另外保存一份独立 Markdown（.md）文件，便于用户复制、下载或交给其他 AI 阅读。Markdown 是从 JSON 和页面现有确定性排盘规则生成的衍生资料，不调用 AI 模型、不需要 API Key，也不包含 AI 对卦象的解释或结论。

### 路径

每日 JSON 仍是一日一个文件：

    daily-records/YYYY/MM/YYYY-MM-DD.json

每条卦例的 Markdown 按日期和记录 ID 单独保存，避免同一天多条卦例互相覆盖：

    daily-records/YYYY/MM/markdown/YYYY-MM-DD--<record-id>.md

### 生成与同步规则

- 新卦例保存时，先保存当天 JSON；JSON 保存成功后，再由 HTML 页面中的 JavaScript 生成对应 Markdown 并通过 Pages Function 保存到 GitHub。
- 修改已有卦例时，更新对应 Markdown；删除卦例时，同时清理对应 Markdown。
- 对历史旧卦例，打开记录列表后点击「复制 MD」会按当前 JSON 即时重建并补存该卦例的 Markdown，再将内容复制到剪贴板。因此旧记录按需迁移，不会在打开列表时批量产生大量提交。
- 「复制」保留原有完整卦盘文字资料（含原始 JSON）；「复制 MD」复制带 Markdown 标题和 JSON 代码块的独立文件内容。
- JSON 已保存但 Markdown 写入失败时，页面必须明确显示「JSON 已保存；MD 未同步」，不得把 JSON 保存失败或 MD 保存成功混为一谈；用户可重试「复制 MD」。
- 从记录列表删除卦例时，若 JSON 删除成功但 Markdown 清理失败，页面明确显示部分成功，不能假报两者均已删除。

### Memo 的来源和标题

- 课堂案例（isCase=true 且 caseSource=classroom）：caseMemo 标为「老师分析 Memo」，caseConclusion 标为「老师结论」。
- 个人练习案例（caseSource=practice）：个人备注标为「个人案例 Memo」，个人结论标为「个人结论」，不冒充老师意见。
- 普通每日卦（非案例的 dailyFortune）：日期级 dailyMemo 标为「个人复盘 Memo」，用于保存当天晚上回看上午卦象与实际经历的反思。额外问事的 MD 不会自动附带这份日期级 Memo。
- 没有相应 Memo 或结论时，Markdown 不生成虚构段落。

Markdown 文件与 JSON 一样保存在 Public 仓库，内容对外可见；不要在 Memo 中写入不希望公开的隐私或机密。
