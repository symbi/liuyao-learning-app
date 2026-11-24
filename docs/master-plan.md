# 六爻起卦与排盘网页：项目主计划

> 六爻规则以课程资料和 `docs/rules-status.md` 为准；未核实内容不得被模型或程序静默补齐。  
> Phase 1 执行基线见 [Phase 1 实施计划](phase1-implementation-plan.md)；Codex 本机执行说明见 [Codex Phase 1 Prompt](codex-phase1-implementation-prompt.md)。

## 1. 产品目标

制作一个轻量的六爻学习与排盘工具。核心用途包括：正确生成和保存卦盘；按用户课堂所学检索相关规则和老师案例；辅助分析每日卦例；通过 Memo 记录实际情况并事后复盘。

## 2. 仓库与资料分工

- Public Learning：`symbi/liuyao-learning-app`，保存网页代码、整理好的课程笔记、规则状态、课堂案例、参考资料，以及 Phase 1 每日卦例 JSON。
- Private raw：`symbi/liuyao-learning-raw`，保存课堂原始录音、ASR 转录、原始 PDF 和未整理来源资料。
- 原始 ASR 可能有术语识别错误，只作为回查老师讲解的参考；整理后的课堂总结和独立案例放在 Public Learning。
- 课堂总结、案例、原始 ASR 用相同课次编号 `lesson-XX` 关联。
- Phase 1 每日卦例公开保存在 Public Learning 的 `daily-records/`。数据可能被查看、复制或 Fork，不写入敏感信息。

## 3. Phase 1：现有 App + Neo4j 知识库辅助分析

Phase 1 分为现有 App 记录系统与新建知识库两部分，彼此保持边界，不破坏已有每日记录流程。

### 3.1 现有 HTML 记录系统（保持现状）

- 当前基线：V80 单页 HTML 原型，排盘规则和 UI 先保持不动。
- 默认 Category 为「今日运势（每日卦）」，问题栏留空；按日本当地日期 `Asia/Tokyo` 读取和保存。
- 每天一个 JSON：`daily-records/YYYY/MM/YYYY-MM-DD.json`。
- HTML 通过 `/api/records/:date` 读写；GitHub 是当前 App 记录持久化位置。
- Cloudflare Pages 托管静态页面和同源 Pages Functions；Pages Functions 负责 GitHub App OAuth 与 GitHub Contents API。
- GitHub App 只安装到 `symbi/liuyao-learning-app`，只授予 Contents Read and write / Metadata Read-only。前端不保存 Token。
- 写入时核对 GitHub blob SHA；冲突时不静默覆盖。

### 3.2 Neo4j 知识库与检索（新增 Phase 1 工作）

- **主知识库：Neo4j AuraDB Free 云端图数据库**；不另建 Supabase/PostgreSQL，不需要 Docker 或 VPS。
- **云端 Python Importer（Google Cloud Run Jobs）**：按 allowlist 读取 Learning 整理课程笔记（Markdown/TXT）和明确选择的课堂案例 JSON；外部资料只通过独立 Source Collector 输出、经批准的 Reference Package 进入知识库，Importer 不直接爬取或下载外部网站/GitHub 资料。本地运行仅作开发便利，不依赖用户的固定 Mac。PDF Adapter 与 OCR 当前 deferred，不是 Phase 1 必须功能；将来用户明确选定具体 PDF 并确认使用权后，再单独评估（与 [Phase 1 实施计划](phase1-implementation-plan.md) 一致）。
- Source A Raw ASR 默认只保留来源和版本，不进入主要 Chunk / Embedding / Rule Candidate 流程；Source B Curated Lesson Notes 是主要课程知识来源。
- Chunk 之后并行运行 Embedding 和 Generative LLM 候选知识抽取；案例 JSON 由 Case Mapper 结构化写入。
- Importer 使用 content hash、revision ID、chunk ID 和 Neo4j MERGE 实现增量、幂等更新；不变资料不重复请求模型。
- 检索层（M7 起位于 Cloud Run Service）使用向量检索 + 图关系扩展，生成带课次、文件、页码/段落、案例来源的内部 Evidence Context（Evidence Pack 的内部结构）。
- **Phase 1 最终分析在云端完成（2026-11-24 决策，方案 B：完整在线分析）**：Cloud Run Service 调用生成模型产出完整分析报告并返回 HTML 展示；Evidence Pack 是后端内部证据结构，用户不再手工复制给 ChatGPT。
- 不要求用户逐条人工审核 AI 节点；必须自动保留来源类别、出处、版本和不确定性。LLM 抽取的规则始终是 candidate，不能自动成为课程已确认规则。

详细目录、数据模型、执行顺序和验收标准见 [Phase 1 实施计划](phase1-implementation-plan.md)。

## 4. 在线分析（Phase 1 的 M7/M8）与 Phase 2 边界

2026-11-24 决策：在线分析提前到 Phase 1，不再等 Phase 2。Phase 1 的完成标志是“用户从浏览器发起分析，云端完成检索和生成，网页显示有来源依据的分析报告”。

- M7 在 Google Cloud Run 部署一个 Python FastAPI Service（初期一个 Service / 一个 Container）作为在线分析 API；M8 做浏览器到报告的端到端验收。
- 内部模块包括 Case/Record 读取适配、GraphRAG Retriever、确定性 Rule Engine、LLM Orchestrator。
- Backend 连接 **同一个 Neo4j AuraDB**，继续使用 Phase 1 已有 Document、Chunk、Embedding、Case 和关系；不重新 Chunk、不重新 Embedding、不重建知识库。
- 后端调用生成模型（优先评估 Vertex AI Gemini，最终模型在 M5/M7 确定）生成最终分析报告，再返回 HTML。
- 当前 HTML 的每日 JSON 仍可继续保存在 GitHub；不因为上 Cloud Run 就必须迁移记录数据。
- Phase 2 留给扩展项：多用户与租户隔离、私人资料存储、分析报告历史与权限管理、异步任务/队列、通知、复杂工作流、生产级监控/备份/灾备、更多模型 Provider 与 AuraDB 付费层优化。Supabase/PostgreSQL 仅在未来真正需要多用户身份、私人数据隔离或关系型业务数据时重新评估。

## 5. 分阶段分析工作流

### Phase 1：云端完整在线分析（M7/M8 交付）

1. 用户在 HTML 录入或选择卦例，点击“分析”。
2. 请求经同源 Pages Function 代理（BFF 形态与服务间认证方式待 M7 设计确认）到达 Cloud Run 分析 Service。
3. Service 校验请求与卦盘快照，检索 Neo4j（向量 + 关键词 + 图关系扩展），构建内部 Evidence Context。
4. Service 调用生成模型生成完整分析报告，附真实来源出处与不确定性说明。
5. 报告直接显示在 HTML 页面；必须区分课堂课程、老师案例、个人练习、外部参考和 AI 推理。在 M7 落地之前，开发阶段仍可用本地 CLI 做检索验证，但那不是 Phase 1 的最终产品形态。

### Phase 2：扩展能力

多用户、分析历史、异步任务、监控运营等扩展（见第 4 节），不改变当前 GitHub 记录保存方案，除非用户明确要求。

## 6. 通用工程原则

- 先读现有 README、规则状态、课程笔记、案例与外部参考，再修改项目。
- 排盘计算必须确定性、可测试；AI 分析和排盘事实分层。
- 课程明确、外部参考、推断、有分歧分别标记。
- 不提交未授权原始课程材料、秘密、令牌、个人隐私或公司资料到 Public。
- 所有记录保留原始日期、时区、规则快照和来源信息，以便复核。
