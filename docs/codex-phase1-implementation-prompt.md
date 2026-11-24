# Codex 执行任务：实现 Liuyao Learning App Phase 1 知识库

> **2026-11-24 同步说明**：本文已按 Phase 1 云端优先架构（完整在线分析，方案 B）同步，与 PR #11 合并后的 AGENTS.md、CLAUDE.md、docs/master-plan.md、docs/phase1-implementation-plan.md、docs/phase1-operating-model.md、docs/phase1-progress.md、docs/workspace-handoff.md 一致。**本文是执行指引，不是开发授权**：任何里程碑（尤其 M3）未经用户明确授权不得启动；当前状态以 docs/phase1-progress.md 为准（M0、M1、M2 已完成；M3 尚未开始）。本地未提交的 M3 草稿不是正式实现，不得当作当前成果。

你在与用户 Mac 独立的开发环境中工作（生产运行在 Google Cloud Run；本地 checkout 只作开发与验证）。请先完整阅读以下项目文档，再开始修改：

1. README.md
2. docs/master-plan.md
3. docs/phase1-operating-model.md
4. docs/phase1-implementation-plan.md
5. docs/phase1-knowledge-base-architecture.md
6. docs/data-model-and-storage.md
7. docs/lessons/README.md
8. materials/class-cases/README.md
9. docs/rules-status.md
10. docs/reference-research-plan.md

## 总目标

实现 Phase 1 的完整在线分析产品：用户在现有 HTML 页面录入或选择卦例并点击“分析”，云端后台自动检索 Neo4j 知识库、构建内部 Evidence Context、调用生成模型，最后直接在 HTML 页面显示完整六爻分析报告和出处。组成部分：运行在 Google Cloud Run Jobs 上的 Python Importer（把选定的整理课程笔记、案例 JSON，以及经独立 Source Collector 输出并获准的 Reference Package 增量导入 Neo4j AuraDB Free）、云端 Embedding 与 AI 知识抽取（M5），以及运行在 Cloud Run Service 上的在线分析 API（M7）。Evidence Pack 是后端内部的证据结构（Evidence Context），不再以“用户手工交给 ChatGPT 网页版”为最终工作流；本地 CLI 的 evidence 输出只作开发验证。PDF 当前 deferred，不属于 Phase 1 范围。HTML 不直接连接 Neo4j。

## 严格边界（必须遵守）

- Cloud Run 是 Phase 1 的目标运行环境（Jobs 承载批处理、Service 承载在线分析 API）；但未经用户明确授权对应里程碑，不得创建或部署任何 Cloud Run/GCP 资源，不得修改 AuraDB，不得操作生产密钥。需要用户授权的事项（凭据恢复、GCP Project/Billing、Secret 录入、部署）必须明确列为阻塞项，不能把本文的未来计划当作当前操作许可。不使用 Supabase/PostgreSQL。
- 不得把固定 Mac 或本地环境描述成最终产品运行的必要条件；本地工具只用于开发和验证，不能替代目标云端运行环境。
- 不把 Neo4j 换成本地数据库；目标主库是 AuraDB Free。
- 不修改现有 index.html、functions/api/[[path]].js、Cloudflare OAuth、排盘逻辑或每日记录保存格式。若发现必要兼容问题，先报告，不自行扩大改动。
- 不默认读取 Private raw 的 ASR 内容；Raw ASR 只作为来源/版本轨道，默认不切主 Chunk、不做主 Embedding、不抽取课程规则。
- Curated Lesson Notes 才是主要课程 Chunk 来源。
- HTML Case JSON 必须由结构化 Case Mapper 导入，不可让 LLM 重算或猜测六爻。
- PDF Adapter/OCR 继续 deferred：当前没有选定的 PDF 输入，不引入 PDF 依赖；未来用户选定具体 PDF 并单独授权后再评估。外部 GitHub 项目必须标记来源类别、版本、License/版权状态；不得和课程来源混合。外部资料统一经独立仓库 Source Collector 输出 Reference Package 后再导入（M6，第一轮延期、非阻塞）。
- 不要求用户逐条人工审核 AI 抽取节点；保留来源 Chunk、模型、候选状态和不确定性。
- 不得将任何 API Key、Neo4j 密码、GitHub Token、真实个人资料或本地路径秘密提交到仓库。
- 不要把整个 GitHub Repository 无差别全量导入。只处理 allowlist。
- 不把 LLM Knowledge Graph Builder 当成必需依赖。
- 不使用已弃用的 neo4j-genai 包；如果用 Neo4j GraphRAG SDK，使用当前官方 neo4j-graphrag 包并核对最新文档。第一版可以使用官方 Neo4j Python Driver + Cypher 实现受控检索，不必为使用 GraphRAG 名称而增加不必要依赖。

## 推荐实现位置

在仓库新增 tools/liuyao-kb/，以 Python 3.12 + virtual environment 为开发基线。可使用：

- neo4j：官方 Python Driver；
- 模型 SDK：按 M5 确定的 Provider 选用官方 SDK（优先评估 Vertex AI Gemini 的 Google Gen AI SDK），负责 Embedding 与生成调用；不要在本文阶段写死 Provider 或模型；
- pydantic：配置和结构化输出校验；
- PyYAML：来源 allowlist；
- PyMuPDF：PDF 已 deferred，当前不引入；未来 PDF 立项后再评估；
- python-dotenv：本机环境变量（仅开发便利；生产凭据由 Secret Manager 在运行时绑定到 Cloud Run，开发环境不持有生产密码）；
- typer 或 argparse：CLI；
- pytest、ruff：测试和静态检查。

依赖要在 pyproject.toml 锁定/约束合理版本。不要在多个地方写死模型名称或向量维度。

## 先做项目检查

1. 检查当前工作树，不覆盖用户已有改动；不要擅自清理未跟踪文件。
2. 确认 Python 版本和 repo 路径。对缺少的仓库/凭据，不要猜路径或要求用户把 Secret 发到任何聊天；凭据缺失时报告 BLOCKED 并列明需要用户在控制台完成的操作。
3. 检查真实资料目录，并以 docs/phase1-progress.md 记录的当前状态为准（课程笔记、课堂案例与每日记录的实际清单以仓库现状为准，不要沿用旧扫描结论）。测试要用 fixture；不能伪造真实课堂案例。
4. 把实际目录差异记录在工具 README，不要静默假设样本文件存在。

## 实施阶段

### M1：Python 项目骨架与配置

创建 CLI、配置 schema、日志、.env.example、sources.example.yaml、.gitignore 规则和单元测试。

本机环境变量模板至少包括：

- NEO4J_URI
- NEO4J_USERNAME
- NEO4J_PASSWORD
- NEO4J_DATABASE
- 生成模型与 Embedding 模型的 Provider、模型 ID 与向量维度配置（具体变量名按 M5 决策与代码现有配置确定；优先评估 Vertex AI Gemini，但不在本文写死）

真实 .env 必须 gitignored，绝不提交。默认 config 必须关闭 raw_asr、关闭全量 daily records 导入，外部 GitHub 项目必须 allowlist。

先实现：
- liuyao-kb doctor
- liuyao-kb sources list
- liuyao-kb ingest --dry-run

没有 credentials 时，dry-run 和本地 parser tests 仍要能运行。

### M2：Source Adapters / Parser

先支持：
- Markdown（保留标题层级、段落序号、文件路径）；
- TXT；
- PDF 不在本阶段范围（deferred，见严格边界）；
- HTML App 每日 JSON / 案例 JSON（兼容 dailyFortune、additionalQuestions 和 isCase/caseSource/caseMemo 字段）。

再支持显式 allowlist 的外部 GitHub 项目：
- 第一轮先 README / Markdown / docs；
- 源代码 Chunking 放在核心链路稳定之后，按文件/类/函数或语法节点切，不可随机字符长度切断；
- 记录 repo URL、commit SHA、path、author、license 和 license status。

Raw ASR adapter 可扫描文件元数据，但默认不读内容、不生成 Chunk。只有用户显式打开配置才允许单独导入到低置信度轨道，且必须和 Curated 索引分离。

### M3：Neo4j Schema、约束、索引与最小云端执行基础

M3 定义节点/关系目录、稳定 ID 公式、唯一约束与 Vector Index 管理，并建立最小云端执行基础（GCP Project、Secret Manager、最小权限身份、GitHub OIDC/WIF、一次性 Cloud Run Schema Job）；实际文件扫描、Hash、Revision 与 Chunk 生成属于 M4。M3 须经用户明确授权后才可启动（当前未开始）。

必须实现：
- 稳定 document_id、revision_id、chunk_id、record_id；
- document SHA-256；
- Chunker version；
- 唯一约束；
- DocumentRevision 的 current/superseded 状态；
- Neo4j-backed Sync Manifest（不要另建 SQLite 同步数据库）；
- MERGE 幂等写入。

同一文本片段跨 revision 未变化时尽量复用 chunk_id；修改段落只重做变化 Chunk。旧 revision 保留，默认检索只使用当前 revision。

节点/关系至少覆盖 implementation plan 的 SourceDocument、DocumentRevision、Chunk、Lesson、CastRecord/Case、Concept、RuleCandidate、ExternalProject。JSON 的嵌套 casting 用 JSON string 或明确扁平字段保存，不能直接写任意嵌套对象作为 Neo4j property。

### M4：云端增量 Importer 核心（Cloud Run Job）

在不调用生成/Embedding 模型的情况下先完成：
- 来源扫描、Parser、Chunker、稳定 ID、content/revision/chunk hash；
- Neo4j Document / Revision / Chunk 的幂等 MERGE；
- Neo4j-backed Sync Manifest；
- dry-run、日志、重试和失败恢复；
- 重复运行不产生重复 Document / Revision / Chunk。

此阶段可把 embedding 标记为待生成，但不能伪造向量或将无向量 Chunk 放入语义检索结果。

### M5：云端 Embedding 与 AI 知识抽取（Cloud Run Job）

对允许处理的 Curated Chunk 并行执行：

A. Embedding Model：
- 选定模型/维度后，给每个 Chunk 生成向量；
- 把 embedding、model ID、dimensions 存到 Neo4j；
- 创建并检查 Vector Index；
- Query 必须使用同一个 embedding profile。

B. Generative LLM：
- 抽取候选 Concept / Entity / Relationship / RuleCandidate；
- 用 Pydantic/JSON Schema 验证输出；
- 每个候选必须含 source_chunk_id、证据摘录、模型 ID、不确定性；
- 状态恒为 candidate，不修改规则状态文件；
- 抽取失败不能丢失原始 Chunk 和来源记录。

不同 Embedding 模型的向量空间互不兼容。请先用小样本比较中文检索效果，再冻结一个 embedding profile；切换模型要使用新 profile/index 并重生成向量，不可混用。Provider、模型与生产向量维度在 M5 实施时确定（优先评估 Vertex AI Gemini），不得提前写死。

调用前检查所选 Provider 当时的 API 条款与数据使用政策；默认只发送用户允许发送的整理笔记/测试材料。Private raw 和私人记录不得默认发送。

### M6：外部参考源启用（第一轮延期、非阻塞；M8 验收后再恢复，不作为 M7/M8 的前置条件）

在用户确认来源/License 后：
- 添加一个外部 GitHub Repository allowlist；
- 第一轮导入 README、Markdown、docs，并记录 URL、commit SHA、作者和 License；
- 后续再为选定的 Python / JavaScript / TypeScript 源码实现按 AST / 符号边界切分；
- PDF 继续 deferred，不在当前范围；未来用户选定具体文件并单独授权后再评估，不能伪造用户资料。

### M4 补充：Importer CLI 与运行报告

提供：
- liuyao-kb ingest --dry-run
- liuyao-kb ingest
- 可选 --source / --lesson / --extract-knowledge 等有限参数。

每次报告扫描、跳过、新建/复用 Chunk、Embedding 请求、LLM 抽取、失败数量。对模型 API 使用合理超时、重试、速率限制；日志不泄露 Secret。

第二次重复执行相同来源必须跳过所有不变内容，不产生重复节点，不再次请求 Embedding/LLM。文档有修改时仅重处理变化 Chunk。写入失败重试后不能产生重复数据。

### M7：在线分析 API 与 HTML 集成（Cloud Run Service）

提供：
- Cloud Run Service 上的分析端点：接收经认证的分析请求（卦盘快照 + 用户问题），HTML 不直接连接 Neo4j；接口的认证方式与 Pages Function 的 BFF/session 职责在 M7 设计时确认，不在本文预设。
- Vector Search + 必要的关键词/全文检索 + 一至两跳图关系扩展。
- 对来源分层：Curated Lesson Notes / Classroom Case 优先；Personal Practice / External Reference 分开显示；Raw ASR 默认只使用来源元数据。
- 在后端构建内部 Evidence Context（含问题/卦盘事实、课程号、路径、标题/页码、原文短摘录、课堂案例 Memo、外部项目 URL/commit/license 与不确定性），调用生成模型生成完整分析报告，返回 HTML 页面展示。

本地 CLI 的 evidence 输出（Markdown Evidence Pack）只作开发与验收验证，不是最终产品形态。

### M8：端到端验收

M8 的验收对象是完整在线流程：从浏览器提交卦例、点击分析，到云端检索/生成、HTML 显示完整分析报告及出处。至少跑以下测试（其中导入类项目为支撑该流程的回归检查）：
1. 解析 lesson-11 或其他实际可用的课程 Markdown，保留课次/标题/出处。
2. PDF 不在验收范围（deferred）；不得以 PDF fixture 代替真实样本验收。
3. Case JSON fixture 不丢六爻字段、Memo、类型、record ID。
4. Raw ASR 默认不进入主 Chunk / Vector Index。
5. 相同文件第二次导入零重复写入/零模型调用。
6. 修改一个段落，变化 Chunk 新建，未变化 Chunk 复用。
7. 同一案例 ID 更新，不重复 Case。
8. 外部资料保留 repo、commit、license，来源分类为 external。
9. 从 HTML 发起分析，云端返回带真实来源出处的完整报告并在页面正确展示；未授权请求被拒绝。
10. 测试和 lint 通过；无任何 Secret 被跟踪。

## 工程原则

- 第一版先小而可验证，避免微服务化。
- 任何内容抽取都必须保留可回溯来源。
- LLM 产物是候选知识，不是老师最终规则。
- 不更改 HTML 当前保存格式。Cloud Run 是目标运行环境，但未经用户明确授权不得创建或部署任何 Cloud Run/GCP 资源（见严格边界）。
- 不要因为没有 Aura/模型凭据就假报通过；把需要用户操作的步骤列成明确阻塞项。
- 发生数据模型重大变更时，先更新 docs/phase1-implementation-plan.md，再改代码。
- 每完成一个 M 阶段，提供变更文件列表、测试命令/结果、未完成项和需要用户验收的具体事项。
