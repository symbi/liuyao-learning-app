# Codex 执行任务：实现 Liuyao Learning App Phase 1 知识库

你在用户 Mac 的本地 Git checkout 中工作。请先完整阅读以下项目文档，再开始修改：

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

实现 Phase 1：一个运行在 Mac 本地的 Python Importer + Query Tool，连接 Neo4j AuraDB Free 云端数据库和 Gemini API。它负责把选定的整理课程笔记、案例 JSON、PDF、外部 GitHub 参考资料增量导入 Neo4j，并根据用户问题/记录 ID 检索资料，生成带来源的 Markdown Evidence Pack，供用户交给 ChatGPT 网页版完成最终分析。

## 严格边界（必须遵守）

- 不部署 Cloud Run，不创建在线 Backend，不使用 Supabase/PostgreSQL，不使用 Docker。
- 不把 Neo4j 换成本地数据库；目标主库是 AuraDB Free。
- 不修改现有 index.html、functions/api/[[path]].js、Cloudflare OAuth、排盘逻辑或每日记录保存格式。若发现必要兼容问题，先报告，不自行扩大改动。
- 不默认读取 Private raw 的 ASR 内容；Raw ASR 只作为来源/版本轨道，默认不切主 Chunk、不做主 Embedding、不抽取课程规则。
- Curated Lesson Notes 才是主要课程 Chunk 来源。
- HTML Case JSON 必须由结构化 Case Mapper 导入，不可让 LLM 重算或猜测六爻。
- PDF、外部 GitHub 项目必须标记来源类别、版本、License/版权状态；不得和课程来源混合。
- 不要求用户逐条人工审核 AI 抽取节点；保留来源 Chunk、模型、候选状态和不确定性。
- 不得将任何 API Key、Neo4j 密码、GitHub Token、真实个人资料或本地路径秘密提交到仓库。
- 不要把整个 GitHub Repository 无差别全量导入。只处理 allowlist。
- 不把 LLM Knowledge Graph Builder 当成必需依赖。
- 不使用已弃用的 neo4j-genai 包；如果用 Neo4j GraphRAG SDK，使用当前官方 neo4j-graphrag 包并核对最新文档。第一版可以使用官方 Neo4j Python Driver + Cypher 实现受控检索，不必为使用 GraphRAG 名称而增加不必要依赖。

## 推荐实现位置

在仓库新增 tools/liuyao-kb/，以 Python 3.12 + virtual environment 为开发基线。可使用：

- neo4j：官方 Python Driver；
- google-genai：当前 Google Gen AI Python SDK，负责 Gemini Embedding 与 Generative API；
- pydantic：配置和结构化输出校验；
- PyYAML：来源 allowlist；
- PyMuPDF：PDF 文本和页码提取；
- python-dotenv：本机环境变量；
- typer 或 argparse：CLI；
- pytest、ruff：测试和静态检查。

依赖要在 pyproject.toml 锁定/约束合理版本。不要在多个地方写死模型名称或向量维度。

## 先做项目检查

1. 检查当前工作树，不覆盖用户已有改动；不要擅自清理未跟踪文件。
2. 确认 Python 版本和本地 repo 路径。对缺少的本地仓库/凭据，不要猜路径或要求用户把 Secret 发给 ChatGPT。
3. 检查真实资料目录。当前 GitHub main 分支扫描结果是：Learning 有第 5～17 课整理笔记和参考文档；Raw 有部分 Raw ASR TXT；目前两个 repo 没找到 PDF；materials/class-cases/ 目前只有 README；daily-records/ 当前无 JSON。测试要用 fixture；不能伪造真实课堂案例。
4. 把实际目录差异记录在工具 README，不要静默假设样本文件存在。

## 实施阶段

### M1：Python 项目骨架与配置

创建 CLI、配置 schema、日志、.env.example、sources.example.yaml、.gitignore 规则和单元测试。

本机环境变量模板至少包括：

- NEO4J_URI
- NEO4J_USERNAME
- NEO4J_PASSWORD
- NEO4J_DATABASE
- GEMINI_API_KEY
- GEMINI_GENERATION_MODEL
- GEMINI_EMBEDDING_MODEL
- GEMINI_EMBEDDING_DIMENSIONS

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
- PDF（按页提取文本并保留 page number；扫描 PDF 明确报告 OCR 未支持，不静默返回空结果）；
- HTML App 每日 JSON / 案例 JSON（兼容 dailyFortune、additionalQuestions 和 isCase/caseSource/caseMemo 字段）。

再支持显式 allowlist 的外部 GitHub 项目：
- 第一轮先 README / Markdown / docs；
- 源代码 Chunking 放在核心链路稳定之后，按文件/类/函数或语法节点切，不可随机字符长度切断；
- 记录 repo URL、commit SHA、path、author、license 和 license status。

Raw ASR adapter 可扫描文件元数据，但默认不读内容、不生成 Chunk。只有用户显式打开配置才允许单独导入到低置信度轨道，且必须和 Curated 索引分离。

### M3：Chunker、ID 和 Neo4j Schema

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

### M4：Gemini 双路径

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

Gemini 的 gemini-embedding-001 与 gemini-embedding-2 向量空间不兼容。请先用小样本比较中文检索效果，再冻结一个 embedding profile；切换模型要使用新 profile/index 并重生成向量，不可混用。

调用前检查当时 Gemini API 条款。Free tier 的内容可能用于改进 Google 产品；默认只发送用户允许发送到 Google 的整理笔记/测试材料。Private raw 和私人记录不得默认发送。

### M5：增量 Importer

提供：
- liuyao-kb ingest --dry-run
- liuyao-kb ingest
- 可选 --source / --lesson / --extract-knowledge 等有限参数。

每次报告扫描、跳过、新建/复用 Chunk、Embedding 请求、LLM 抽取、失败数量。对模型 API 使用合理超时、重试、速率限制；日志不泄露 Secret。

第二次重复执行相同来源必须跳过所有不变内容，不产生重复节点，不再次请求 Embedding/LLM。文档有修改时仅重处理变化 Chunk。写入失败重试后不能产生重复数据。

### M6：Query Tool / Evidence Pack

提供：
- liuyao-kb evidence --question "..."
- 可选 --record-id ... 获取已导入的 CastRecord/Case 上下文。
- Vector Search + 必要的关键词/全文检索 + 一至两跳图关系扩展。
- 对来源分层：Curated Lesson Notes / Classroom Case 优先；Personal Practice / External Reference 分开显示；Raw ASR 默认不返回。

输出本地 Markdown Evidence Pack，含问题/卦盘事实、课程号、路径、标题/页码、原文短摘录、课堂案例 Memo、外部项目 URL/commit/license、不确定性和可直接交给 ChatGPT Web 的任务提示。它不是最终分析报告。

### M7：端到端验收

至少跑以下测试：
1. 解析 lesson-11 或其他实际可用的课程 Markdown，保留课次/标题/出处。
2. PDF fixture 的页码定位可用；无 PDF 真实样本时先用 fixture 并说明。
3. Case JSON fixture 不丢六爻字段、Memo、类型、record ID。
4. Raw ASR 默认不进入主 Chunk / Vector Index。
5. 相同文件第二次导入零重复写入/零模型调用。
6. 修改一个段落，变化 Chunk 新建，未变化 Chunk 复用。
7. 同一案例 ID 更新，不重复 Case。
8. 外部资料保留 repo、commit、license，来源分类为 external。
9. Query 返回相关来源并生成 Evidence Pack。
10. 测试和 lint 通过；无任何 Secret 被跟踪。

## 工程原则

- 第一版先小而可验证，避免微服务化。
- 任何内容抽取都必须保留可回溯来源。
- LLM 产物是候选知识，不是老师最终规则。
- 不更改 HTML 当前保存格式，不接 Cloud Run。
- 不要因为没有 Aura/Gemini 凭据就假报通过；把需要用户操作的步骤列成明确阻塞项。
- 发生数据模型重大变更时，先更新 docs/phase1-implementation-plan.md，再改代码。
- 每完成一个 M 阶段，提供变更文件列表、测试命令/结果、未完成项和需要用户验收的具体事项。
