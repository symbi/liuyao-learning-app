# Phase 1 实施计划：Neo4j 知识库、增量 Importer 与 Evidence Pack

> 版本：1.0  
> 规划日期：2026-11-19  
> 状态：实施基线，等待用户逐个验收里程碑  
> 如果本文与早期概念文档有差异，以本文的实施范围和验收标准为准。概念解释见 [Phase 1 实际运行架构](phase1-operating-model.md)。

## 1. 目标与最终交付

Phase 1 不是上线自动断卦网站，而是先建成可实际使用的“知识库辅助分析工作流”：

1. 用户继续在现有 HTML App 排卦、录入课堂案例、保存每日记录；Cloudflare Pages + Pages Functions + GitHub 流程保持不变。
2. 在用户 Mac 上运行 Python Importer，把经过选择的课程笔记、案例 JSON、PDF 和外部 GitHub 参考资料增量同步到 Neo4j AuraDB Free 云端图数据库。
3. Importer 对主要课程资料执行 Chunk、Embedding 和候选知识抽取；案例 JSON 由确定性的 Case Mapper 读取，不让 LLM 重新猜测卦盘。
4. 提供本地 Query Tool：输入问题或已保存卦例，搜索 Neo4j，组合向量检索和图关系扩展，产生带出处的 Evidence Pack。
5. 用户把卦盘 + Evidence Pack 交给 ChatGPT 网页版，由 ChatGPT 完成最终分析报告。

**Phase 1 完成时的可见成果：** 一条可重复运行的本地命令，可以把指定来源增量同步进 AuraDB；另一条命令可以针对某个卦例/问题检索课程、案例和外部参考，并输出可直接交给 ChatGPT 的 Markdown Evidence Pack。

## 2. Phase 1 不做什么

- 不部署 Cloud Run / 自建在线 Backend Container。
- 不接入 Supabase / PostgreSQL；Neo4j AuraDB 是知识库唯一主数据库。
- 不修改现有排盘规则、HTML 页面布局、Cloudflare OAuth 或每日 JSON 存储结构（除非另有明确需求）。
- 不把 Gemini Embedding 当成最终分析模型；Embedding 只负责向量。
- 不要求用户逐条人工审核 Neo4j 节点和关系；系统自动保存来源、来源类别、版本和不确定性。
- 不默认读取或索引 Private raw 中低准确率的 ASR；Raw ASR 与 Curated Notes 保持不同轨道。
- 不把 PDF、外部开源项目内容混成老师课堂规则。
- 不把 Neo4j LLM Knowledge Graph Builder 当成必需运行组件；它只是可选的图谱构建/观察工具。

## 3. 部署架构与数据流

~~~mermaid
flowchart TB
  subgraph SOURCES["资料来源：GitHub / 明确选择的文件"]
    A["Private raw：录音 + Raw ASR<br/>默认只归档/回查"]
    B["Learning：ChatGPT 整理的课程笔记"]
    C["HTML 保存的课堂案例 / 个人练习 JSON"]
    D["获准导入的 PDF / 古籍 / 外部 GitHub 项目"]
  end

  subgraph MAC["Mac 本地：Phase 1"]
    I["Python Importer"]
    S["Source Scanner + Parser"]
    H["Hash / Revision / Chunker"]
    E["Evidence Query CLI"]
    P["Evidence Pack.md"]
  end

  subgraph MODELS["Gemini API"]
    EM["Embedding Model"]
    GL["Generative LLM：候选知识抽取"]
  end

  N[("Neo4j AuraDB Free：Document / Revision / Chunk / Case / Concept / RuleCandidate / Relationships / Vector Index")]

  subgraph HUMAN["最终分析"]
    CHAT["ChatGPT Web：卦盘 + Evidence Pack"]
    REPORT["分析报告"]
  end

  B --> I
  C --> I
  D --> I
  A -. "默认不进入主要索引" .-> I
  I --> S --> H
  H --> EM
  H --> GL
  EM --> I
  GL --> I
  I -->|"Neo4j Driver / Cypher MERGE"| N
  E -->|"问题向量 + Vector / Full-text Search"| N
  N -->|"图关系扩展 + 来源证据"| E
  E --> P --> CHAT --> REPORT
~~~

**部署位置：**

| 组件 | 运行位置 | Phase 1 部署方式 |
|---|---|---|
| HTML App | Cloudflare Pages | 保持现状 |
| Pages Functions | Cloudflare Workers Runtime | 保持现状 |
| GitHub 代码、整理笔记、每日记录 | GitHub | 保持现状 |
| Python Importer / Query Tool | 用户 Mac | Python 3.12 + virtualenv；不需要 Docker |
| Gemini Embedding / Generative API | Google 托管 API | 本地 Python 发起 HTTPS 请求 |
| Neo4j AuraDB Free | Neo4j 托管云服务 | 本项目唯一知识图谱主库 |
| LLM Knowledge Graph Builder | Neo4j Labs 在线工具 | 可选试验，不依赖它运行 |
| Cloud Run Backend | Phase 2 | 本阶段不部署 |

### Neo4j 免费层注意事项

截至 2026-11-19，Neo4j 官方额度文档列出的 AuraDB Free 限额为 200,000 nodes、400,000 relationships、1 GB storage；免费层没有 SLA，备份为 on-demand。官方价格页将 Vector Optimization 列为非 Free 功能，但这不等于没有基础 Vector Index。实际建库时必须运行连接、创建 Vector Index 和查询的 smoke test，确认当前 Free 实例支持情况，再开始批量导入。

官方来源：

- [AuraDB quotas and limits](https://neo4j.com/docs/aura/quotas-and-limits/)
- [AuraDB pricing](https://neo4j.com/pricing/)
- [Cypher vector indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/vector-indexes/)
- [Search indexes / vector + full-text hybrid](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/)

## 4. 双 Source Track 与其他输入类型

课程来源必须区分：

| Source Type | 典型位置 | 初期处理 | 检索地位 |
|---|---|---|---|
| raw_audio | Private raw 音频 | 保存来源信息，不转成 Chunk | 不作为文本检索 |
| raw_asr | Private raw 的 TXT 转写 | 默认只保留来源/版本信息，不做主 Embedding、不抽取课程规则 | 低置信度、默认关闭 |
| curated_lesson_note | Learning 的 docs/lessons/*.md | 解析、Chunk、Embedding、候选知识抽取 | 主要课程知识来源 |
| classroom_case | materials/class-cases/ 或 HTML JSON | Case Mapper 结构化导入，保存老师分析 Memo 和来源 | 老师课堂案例来源 |
| personal_practice | HTML JSON | Case Mapper 结构化导入 | 个人练习；不作为老师规则证据 |
| daily_casting | HTML 每日卦 JSON | 只有配置显式允许时才导入 | 个人记录 |
| pdf_reference | 用户选定的 PDF | 每页提取文本，保留页码后 Chunk；扫描件 OCR 不在第一版范围 | 外部参考 |
| external_project_doc | 选定的公开 GitHub README/docs | 记录 URL、commit SHA、作者和 License 后 Chunk | 外部技术参考 |
| external_project_code | 选定的开源项目源码 | 第二子阶段按文件/类/函数边界切分；不能随机截断 | 外部实现参考 |

### 双轨规则

1. **Source A — Raw**：原始录音与原始 ASR 留在 Private raw。用户目前估计 ASR 识别准确率约 70%，所以不把它与正式笔记混为一谈。
2. **Source B — Curated**：ChatGPT 整理、结合课堂上下文修订后放入 Learning 的正式课程笔记，是 Phase 1 的主要 Chunk 来源。
3. 课程笔记应尽可能保留 lessonId、原始 ASR 文件路径或来源引用、段落/标题定位。
4. 将来 Raw ASR 通过更好的模型生成 v2 时，v2 是同一来源的新 revision；v1 保留，不覆盖。默认仍不提升为正式课程笔记。
5. PDF、GitHub 外部资料都能 Chunk，不要求先由 ChatGPT 改写。但必须保留外部来源、许可证和来源等级。

### 当前仓库扫描结果（2026-11-19）

- liuyao-learning-app 有第 5～17 课的整理笔记、课程外部参考文档和案例目录说明。
- liuyao-learning-raw 有部分第 5～17 课的原始 ASR TXT。
- 当前两个仓库的 main 分支树中都没有找到 PDF 文件。
- materials/class-cases/ 当前只有 README 约定，没有已提交的案例 JSON。
- daily-records/ 当前没有已提交的每日记录 JSON。

因此第一轮开发必须先用自动化 fixture 测试 Markdown、PDF parser 和 Case Mapper；真实 PDF 与真实课堂案例验收，需要用户之后指定/保存一份合适的文件。不得为了测试伪造老师案例。

## 5. 资料来源配置与安全

Importer 使用显式 allowlist 配置，不扫描或上传用户电脑全部文件。

建议配置文件：tools/liuyao-kb/sources.yaml（只提交无秘密的路径/来源配置模板）。配置中明确：

- Learning 本地仓库根目录和允许的目录/文件模式；
- Private raw 本地仓库根目录（默认禁用内容读取）；
- 外部 GitHub repository URL、选定路径、commit/ref、License 状态；
- PDF 本地路径及是否允许送到模型服务；
- 是否导入每日卦例、是否只导入 isCase=true 的记录。

**默认安全设置：**

- raw_asr.enabled=false
- daily_records.include=false，或者仅允许用户显式选中的案例记录；不要默认把所有每日 Memo 传给模型。
- external_projects 为空，须由用户选择和核对 License 后添加。
- PDF 只导入用户明确选定的文件；不把受版权保护或不允许上传的 PDF 送入云端模型。
- 不把原始录音、ASR、私人案例或其他不适合提交给第三方模型的内容发送到 Gemini。
- .env、API Key、Neo4j password、下载缓存和本地输出都必须在 .gitignore 中；仓库只提交 .env.example。
- 绝不把 Gemini API Key、Neo4j 凭据、GitHub Token 写入 HTML、公开文档、测试快照或日志。

Google Gemini API 官方当前说明：免费层内容可能用于改进 Google 产品；付费层内容不用于该用途。实际启用前应再次查看条款。第一轮只使用用户允许发送给 Google 的整理后课程文本和测试资料。

- [Gemini API pricing / data use](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)

## 6. 推荐目录与模块边界

建议由 Codex 在仓库创建：

~~~text
tools/liuyao-kb/
├── pyproject.toml
├── README.md
├── .env.example
├── sources.example.yaml
├── src/liuyao_kb/
│   ├── cli.py
│   ├── config.py
│   ├── ids.py
│   ├── models.py
│   ├── sources/
│   │   ├── markdown.py
│   │   ├── text.py
│   │   ├── pdf.py
│   │   ├── case_json.py
│   │   └── github_project.py
│   ├── chunking/chunker.py
│   ├── providers/gemini.py
│   ├── neo4j/
│   │   ├── driver.py
│   │   ├── schema.py
│   │   ├── writer.py
│   │   └── retrieval.py
│   ├── pipeline/
│   │   ├── scan.py
│   │   ├── ingest.py
│   │   └── evidence_pack.py
│   └── prompts/extract_knowledge.md
└── tests/
    ├── fixtures/
    ├── test_chunking.py
    ├── test_ids.py
    ├── test_case_json.py
    ├── test_incremental.py
    ├── test_provenance.py
    └── test_evidence_pack.py
~~~

目录是建议结构，Codex 可在不改变模块职责的前提下微调。第一版不应为了“完整架构”过早拆成微服务。

## 7. Neo4j 数据模型 v1

第一版使用一个 AuraDB 数据库，不增加 Supabase/PostgreSQL。建议节点：

| Label | 用途 | 关键字段 |
|---|---|---|
| SourceDocument | 一个稳定的源文件身份 | document_id、source_type、source_uri、trust_level、current_revision_id |
| DocumentRevision | 某一版本的文档内容 | revision_id、content_hash、revision_ref、parser_version、chunker_version、status |
| Chunk | 可检索的文本段落 | chunk_id、text、text_hash、ordinal、page、heading、embedding、embedding_model、embedding_dimensions |
| Lesson | 课程课次 | lesson_id、lesson_number、title |
| CastRecord | HTML 记录/每日卦 | record_id、record_type、date、question、casting_json |
| Case | 被标记为案例的 CastRecord | case_type、review_status、case_memo |
| Concept | 六亲、暗动、日辰等概念 | concept_id、name、aliases |
| RuleCandidate | LLM 抽取的候选规则 | candidate_id、statement、conditions、uncertainty、extractor_model、status=candidate |
| ExternalProject | 外部 GitHub 项目来源 | repo_url、commit_sha、license、license_status |

关系示例：

- SourceDocument -[:HAS_REVISION]-> DocumentRevision
- DocumentRevision -[:CONTAINS]-> Chunk
- Chunk -[:MENTIONS]-> Concept
- RuleCandidate -[:EXTRACTED_FROM]-> Chunk
- Case -[:TAUGHT_IN]-> Lesson
- Case -[:REFERENCES]-> Chunk
- ExternalProject -[:HAS_SOURCE]-> SourceDocument

重要实现约束：

- 对 document_id、revision_id、chunk_id、record_id 建唯一约束。
- 对 JSON 中嵌套的六爻字段，用原始 JSON 字符串或明确的扁平化属性保存；不要假设 Neo4j 节点属性可直接存任意嵌套 JSON 对象。
- Case 与 CastRecord 可以是同一个节点的多个 Label。
- 每个候选概念/关系/规则必须连回产生它的 Chunk。
- AI 抽取状态永远是 candidate，不得自动改成课程“已确认”。
- 检索时优先当前 revision；历史 revision 仍保留，但默认不参与普通检索。
- 节点和关系由 Cypher MERGE 幂等写入；不因重复运行产生重复内容。

## 8. 增量同步与版本策略

**不要另建一个本地 SQLite 数据库管理同步状态。** 同步清单直接保存在 Neo4j 的 SourceDocument / DocumentRevision 节点中；本地只保留运行日志和临时缓存。

标识策略：

- document_id = source_type + repository + path（稳定身份）。
- revision_id = document_id + content_hash。
- chunk_id = document_id + chunker_version + normalized_chunk_hash + occurrence_index。
- record_id = HTML JSON 中现有稳定 id；不能只用日期或卦名当 ID。

同步行为：

| 情况 | 必须行为 |
|---|---|
| 新文件 | 创建 SourceDocument + DocumentRevision + Chunks |
| 相同文件再次运行 | 完全跳过；不得重复请求 Embedding/LLM |
| 文档修改 | 创建新 revision；仅对变化 Chunk 执行新处理；未变化 Chunk 尽量复用 |
| 文档删除/路径变化 | 标记旧来源不再 active，不物理删除历史 |
| Raw ASR v1 → v2 | 创建新 revision；不覆盖 v1，不自动提升为 Curated |
| Case Memo 修改 | 同一个 record_id 更新 Case 当前内容，并保留 revision/audit 信息 |
| 规则候选重复抽取 | 使用稳定 candidate_id / MERGE 去重；始终保留来源 Chunk |

模型升级规则：

- 同一个 Embedding Index 中不能混用不同模型的向量。
- 首轮用小型检索样例比较可用模型后，确定一个 embedding profile，并记录模型 ID、维度、创建日期。
- 若未来从 gemini-embedding-001 改为 gemini-embedding-2，必须新建 embedding profile / index 并重新生成对应向量，不能直接比较两种不同空间的向量。
- 官方 Embedding 文档明确指出这两个模型的向量空间不兼容，需要重新 Embedding。

参考：[Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings)。

## 9. Gemini 的两个任务

### Embedding Model

- 把每个选定 Chunk 转成数值向量。
- 查询时把用户问题转换成同一模型、同一维度的向量。
- 向量存储在 Neo4j Chunk 节点，并创建 Vector Index。
- 它不产生规则、不写分析报告。

### Generative LLM

- 读取选定的 Curated Chunk。
- 按严格 JSON Schema 抽取候选 Concept、Entity、Relationship、RuleCandidate、摘要。
- 每个候选输出必须带 source_chunk_id、短证据引文、来源类型和不确定性。
- 输出不是已确认规则，不直接改写 docs/rules-status.md。
- Phase 1 不调用它生成最终卦象报告；最终报告仍由 ChatGPT 网页版完成。

使用 Google 官方 Python SDK google-genai，不要用旧版 google-generativeai SDK。模型 ID 放在环境变量/配置中，不要写死在业务逻辑。

官方资料：

- [Gemini Embedding API](https://ai.google.dev/gemini-api/docs/embeddings)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [Gemini API pricing / data use](https://ai.google.dev/gemini-api/docs/pricing)

## 10. CLI 与用户使用方式

建议至少提供以下命令（最终命令名可调整，但功能必须具备）：

~~~bash
liuyao-kb doctor
liuyao-kb schema apply
liuyao-kb sources list
liuyao-kb ingest --dry-run
liuyao-kb ingest
liuyao-kb evidence --record-id <record-id> --question "请分析这个卦，参考老师类似案例"
liuyao-kb evidence --question "老师在第十一课如何讲暗动？"
~~~

具体 CLI 可使用 Typer 或 argparse。每次运行必须报告：发现文件数、新 revision 数、复用 Chunk 数、新 Chunk 数、Embedding 调用数、候选抽取数、跳过数、失败数。

## 11. Evidence Pack 格式

输出为本地 Markdown 文件，默认不自动提交到 Public GitHub。至少包含：

1. 当前卦盘事实（如果通过 record_id 查询）和用户问题；不能凭模型重新计算或改写事实。
2. 主要课程笔记证据：课次、文件路径、标题/页码/段落位置、短摘录。
3. 相关课堂案例：课堂案例标签、核对状态、老师分析 Memo 和来源。
4. 个人练习案例：独立分区，不当作老师规则证据。
5. 外部 GitHub/PDF 参考：独立分区，附 URL、commit SHA、License 和用途。
6. Raw ASR：默认不返回；若用户显式启用，必须放在低置信度单独分区。
7. 来源冲突、缺少依据和模型不确定性。
8. 提供一段可直接交给 ChatGPT 网页版的分析任务说明。

Evidence Pack 不是最终断卦报告；它是有来源依据的“证据包”。

## 12. 里程碑与用户验收

| Milestone | 交付物 | 用户验收标准 |
|---|---|---|
| M0：Aura 准备 | AuraDB Free 实例、凭据放本机 .env | Aura Console 显示实例运行；本机 doctor 能连通；秘密不提交 |
| M1：项目骨架 | Python CLI、配置、日志、单元测试 | doctor、sources list、ingest --dry-run 正常 |
| M2：来源解析 | Markdown/TXT、PDF 页文本、HTML 案例 JSON Adapter | 测试可显示段落、页码、案例 ID；没有丢失来源路径 |
| M3：Neo4j Schema | 唯一约束、关系、Vector Index、测试节点 | 可创建/查询节点；向量索引 smoke test 成功 |
| M4：增量 Importer | Manifest、Hash、Chunk、MERGE、版本管理 | 第一次导入新增；第二次重复运行 0 个新 Chunk/Embedding；修改一个段落只处理变化部分 |
| M5：Gemini 双路径 | Embedding + 结构化候选抽取 | Chunk 有向量；候选知识能回到来源 Chunk；没有自动确认规则 |
| M6：外部资料 | 选定 PDF、README/docs；随后选定代码文件 | 来源/许可证/版本完整；不混入老师课程来源 |
| M7：Evidence Pack | 本地 Query Tool、向量检索 + 图关系扩展 | 输入已知问题时找到相关课堂段落/案例；输出可读、可追溯的 Markdown |
| M8：端到端验收 | 真实课程 + 真实案例 + 允许的 PDF/外部参考 | 你能把 Evidence Pack 交给 ChatGPT，且引用来源正确、分类明确 |

### 最低验收测试矩阵

- 同一 Markdown 连续导入两次，第二次不得创建重复节点或重复模型调用。
- 修改 Markdown 的一个段落，只重做变化 Chunk；未变化 Chunk ID 保持可复用。
- 同一个 Raw ASR v1 再次导入仍然处于 Raw / Low Confidence，不进入主索引。
- 新建 Raw ASR v2 时保留 v1 与 v2 两个 revision。
- Case JSON 的六爻原始字段、日期、问题、案例类型和 Memo 不得在映射中丢失。
- PDF Chunk 必须能追溯到原文件及页码；扫描版若无法抽取，报告明确提示而不是静默跳过。
- 外部开源项目必须显示 repository URL、commit SHA、License；不能被标注成课堂规则。
- 每一条 RuleCandidate / Concept Extraction 都能定位到来源 Chunk。
- 生成 Evidence Pack 时，课堂、个人练习、外部资料、Raw ASR 分区清楚。
- Neo4j/Google 请求失败时保留来源文件，不把同步状态标记为成功。

## 13. Phase 2 连接原则

Phase 2 不是把 Phase 1 数据库搬上云。AuraDB 从 Phase 1 开始就是云端主库。

未来如需 HTML 一键分析：

- 在 Google Cloud Run 部署一个 Python FastAPI Service（初期一个 Container）。
- 把 Phase 1 的 Query / Evidence Pack 逻辑迁入同一个 Service。
- 后端增加 LLM Orchestrator，调用 Gemini 或 OpenAI 的生成模型，生成分析报告并返回 HTML。
- 继续使用同一个 AuraDB；不重新导入、不重建 Chunk/Embedding。
- 当前 GitHub 每日记录流程可以继续保留；只有明确需要多用户隔离时，才重新评估 Supabase。

## 14. 谁来实现

推荐协作分工：

- **ChatGPT**：维护架构与实施计划、编写/审阅关键文件和 Schema、检查 Codex 的 diff、帮助解释错误并设计验收。
- **Codex（Mac 本机）**：在本地 checkout 中创建 Python 项目、运行测试、建立 virtualenv、连接用户本机配置的 AuraDB/Gemini API、修复实际运行问题。
- **用户**：创建 AuraDB Free、在本机安全保存凭据、选择愿意导入的 PDF/外部项目、逐个验收里程碑。

ChatGPT 可以直接修改 GitHub 仓库文件，但无法代替用户在 Mac 上完成 Neo4j 控制台操作，也不应要求用户把数据库密码或 API Key 发到聊天中。最稳妥的路径是 Codex 在 Mac 执行实施，ChatGPT 负责审查计划、diff 和验收结果。

## 15. 官方技术参考

- [Neo4j AuraDB quotas and limits](https://neo4j.com/docs/aura/quotas-and-limits/)
- [Neo4j Cypher Vector Indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/vector-indexes/)
- [Neo4j Search Indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/)
- [Neo4j GraphRAG for Python](https://neo4j.com/docs/neo4j-graphrag-python/current/)
- [Neo4j GraphRAG RAG user guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- [Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [Gemini API pricing / data handling](https://ai.google.dev/gemini-api/docs/pricing)
- [Neo4j LLM Knowledge Graph Builder](https://neo4j.com/developer/genai-ecosystem/llm-graph-builder/)
