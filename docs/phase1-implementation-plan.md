# Phase 1 实施计划：Neo4j 知识库、增量 Importer 与 Evidence Pack

> 版本：1.1
> 规划日期：2026-11-21
> 状态：按用户确认调整来源边界；M2-A/M2-B 已合并（PR #3，merge commit `9505ce7`）；双仓库架构与来源目录规划已合并（PR #4，merge commit `65fb501`），main 已包含 Reference Source Catalog、Reference Package Schema 与双仓库架构；M2-C 已按真实文件拆为 C1/C2/C3（见第 4、12 节），前置条件（PR #4 合并）已满足，但实现仍须用户明确授权后才启动；PDF Adapter/OCR 继续 deferred
> 如果本文与早期概念文档有差异，以本文的实施范围和验收标准为准。概念解释见 [Phase 1 实际运行架构](phase1-operating-model.md)。

## 1. 目标与最终交付

Phase 1 不是上线自动断卦网站，而是先建成可实际使用的“知识库辅助分析工作流”：

1. 用户继续在现有 HTML App 排卦、录入课堂案例、保存每日记录；Cloudflare Pages + Pages Functions + GitHub 流程保持不变。
2. 在用户 Mac 上运行 Python Importer，把经过选择的课程笔记、案例 JSON，以及独立 Source Collector 输出的标准 Reference Package 增量同步到 Neo4j AuraDB Free 云端图数据库。
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
- 不把古籍、外部开源项目内容混成老师课堂规则。
- Phase 1 知识库仓库不负责爬取外部网站、自动翻页或下载文件；由独立 repository `symbi/liuyao-source-collector` 负责。
- 当前不开发 PDF Adapter 或扫描件 OCR；只有用户选定具体 PDF 并确认使用权后，才单独评估。
- 不把 Neo4j LLM Knowledge Graph Builder 当成必需运行组件；它只是可选的图谱构建/观察工具。

## 3. 部署架构与数据流

~~~mermaid
flowchart TB
  subgraph SOURCES["资料来源：GitHub / 明确选择的文件"]
    A["Private raw：录音 + Raw ASR<br/>默认只归档/回查"]
    B["Learning：ChatGPT 整理的课程笔记"]
    C["HTML 保存的课堂案例 / 个人练习 JSON"]
    D["独立 Collector 输出的获准 Reference Package"]
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
| external_reference_text | Source Collector 输出的古籍/网页文本包 | 校验 manifest、来源、版权和内容哈希，再按章节导入 | 外部参考，单独分区 |
| pdf_reference | 将来用户明确选定且获准使用的 PDF | 当前 deferred；无 PDF Adapter、无 OCR | 暂不导入 |
| external_project_doc | 选定的公开 GitHub README/docs | 记录 URL、commit SHA、作者和 License 后 Chunk | 外部技术参考 |
| external_project_code | 选定的开源项目源码 | 第二子阶段按文件/类/函数边界切分；不能随机截断 | 外部实现参考 |

### 双轨规则

1. **Source A — Raw**：原始录音与原始 ASR 留在 Private raw。用户目前估计 ASR 识别准确率约 70%，所以不把它与正式笔记混为一谈。
2. **Source B — Curated**：ChatGPT 整理、结合课堂上下文修订后放入 Learning 的正式课程笔记，是 Phase 1 的主要 Chunk 来源。
3. 课程笔记应尽可能保留 lessonId、原始 ASR 文件路径或来源引用、段落/标题定位。
4. 将来 Raw ASR 通过更好的模型生成 v2 时，v2 是同一来源的新 revision；v1 保留，不覆盖。默认仍不提升为正式课程笔记。
5. 外部古籍/网页/GitHub 资料先由独立 Source Collector 采集并输出标准 Reference Package；知识库只读取经批准的包，不直接访问网站。
6. PDF 目前不是已确认输入：当前两个仓库最近扫描均未发现 PDF；当前也没有指定要导入的 PDF 版本。因此 PDF Adapter 与 OCR 均 deferred。

### 当前资料状态（最近核对：2026-11-22，已含第十九课 case-002）

- liuyao-learning-app 有第 5～20 课整理笔记、外部参考文档和案例目录说明；正式课程笔记以 Markdown 为主。
- liuyao-learning-raw 有部分课程原始 ASR TXT；Raw ASR 默认不进入主要索引。
- 2026-11-19 的两个仓库 main 分支扫描均未发现 PDF；2026-11-21 的 ChatGPT Library PDF 清单也没有返回 PDF。当前没有已选定、准备导入的 PDF。
- 课堂案例相关资料目前有四种不同形式，必须区分处理（以下均已按 main 真实文件核对）：
  1. **课程案例 JSON**：`materials/class-cases/lesson-19/case-001.json`，`recordType=class-case`，独立案例 ID `L19-C01-work-transfer`，`lessonId=lesson-19`，并通过 `dailyRecord.recordId` 关联到 HTML 每日记录中的子记录 `9f89c47a-ba51-44d1-81b5-ffba16a30ca2`；其 `matchStatus=verified`，`verificationBasis` 记录了与第十九课 ASR 讲解的核对依据。
  2. **课堂案例 MD 表示**：`materials/class-cases/lesson-19/case-001-analysis.md` 是 case-001 这同一个课堂案例的 Markdown 可读表示，与案例 JSON 同属一个 `case_id`，不是独立案例，也不是一份额外的分析来源；它与下面第 4 项的每日记录生成 MD 是两类不同的 MD，不得混淆。文件内容中出现的老师课堂讲解、用户补充的卦盘、用户 memo、AI 计算仍须分别标明来源——同属一个案例不等于来源权威性相同。
  3. **HTML 每日记录 JSON**：`daily-records/2026/11/2026-11-21.json` 是每日记录容器，顶层不是案例；其 `additionalQuestions[]` 中有多个独立子记录（各有自己的 UUID、`recordType=additionalQuestion`、`isCase`、`caseSource`）。不得把整个每日记录容器当成一个 Case。注意该文件内两个子记录都带 `isCase=true`、`caseSource=classroom`，但只有 `9f89...` 被 case-001 显式关联——`isCase`/`caseSource` 只能用于分类，不能仅凭它们自动认定某条记录已匹配到具体课堂案例或已验证。
  4. **自动生成的记录 MD**：`daily-records/2026/11/markdown/2026-11-21--7e0a6b19-92f2-4f8c-b7b0-8771955ad45b.md` 是 HTML 按每日记录 JSON 与确定性排盘规则生成的可读呈现，对应子记录 `7e0a6b19-...`（与 case-001 关联的 `9f89...` 是两条不同记录，不得混淆）；其 `## 原始记录 JSON` 一节内嵌完整 JSON。它是该记录的另一种表示，不是第二个独立案例，不得重复创建 Case 节点或重复计数。
- **课堂案例身份原则（核心）**：Learning App 中的课堂案例是老师在实际课程中讲解过的教学案例（`classroom_case`），不是用户新创建的个人练习数据，不得归类为 `personal_practice`；个人练习是独立类别。每个课堂案例应尽可能连接五类来源：（1）老师原始课堂录音 / ASR 转录中的案例讲解位置；（2）对应课程整理笔记中的案例内容；（3）用户补充并核对的完整卦盘结构；（4）HTML 保存的 JSON 记录及其生成 MD 表达；（5）与案例 JSON 配对的课堂案例 MD 表示。课程笔记或 ASR 提到同一案例时，建立引用/提及关系并保留课程、文件、段落或时间定位；同一案例在笔记、ASR、案例 JSON、案例 MD 中重复出现，不产生多个案例。案例 JSON 与课堂案例 MD 都只是该案例的表示形式：在图模型中以 `ClassCase -[:HAS_REPRESENTATION]-> SourceDocument` 表达（关系上标明 format=json/markdown），不为 MD 另建案例身份。老师 ASR 的来源定位不依赖 Chunk：Raw ASR 默认不 Chunk，ClassCase 可以直接关联 ASR 的 SourceDocument / DocumentRevision，并在关系上保留 Locator（原始仓库与文件路径、课程 ID、转录段落序号、有可靠时间戳时的时间范围）与置信度/校正状态；未经音频校正的 ASR 只能标为当前可用的老师讲解线索，不得称为经音频验证的逐字原话。案例身份规则：保留稳定案例 ID；课程归属用 `lessonId` 与来源定位表达；HTML 原始记录 ID 只通过明确的 `dailyRecord.recordId` 关联；JSON 与课堂案例 MD 通过同一个稳定 `case_id` 配对；必要时辅以内容一致性校验；`matchStatus` / `verificationBasis` 说明与课堂原始教学资料的匹配程度；ASR 未经音频校正时保留低置信度说明；用户补充的卦盘结构、老师原话、AI 推算必须分开标记，不得混为一谈。此原则同时适用于 M2-C 的 Mapper、M3 的 Neo4j 数据模型与 M7 的 Evidence Pack 检索逻辑。
- **案例核对生命周期样本（2026-11-22，真实数据）**：`daily-records/2026/11/2026-11-22.json` 的子记录 `13e9c29a-cdbc-41e0-912d-5e02fa7c54d3` 最初只有 `isCase=true`、`caseSource=classroom` 标记，其生成 MD 标注“案例核对状态：待核对”，记录本身没有 case_id 或 matchStatus——按上列身份原则，它当时只是待核对的 CastRecord 候选：不创建已验证的 ClassCase、不建 BASED_ON_RECORD、不计入课堂案例数量。其后它被显式核对并配对为第十九课案例：`materials/class-cases/lesson-19/case-002.json`（稳定 case_id `L19-C02-shop-operation-transfer`，`matchStatus=matched`，附 `verificationBasis`）通过 `dailyRecord.recordId` 显式关联该子记录，ClassCase 身份自此才成立。注意：关联信息保存在案例 JSON 一侧，每日记录本身没有被回填 case_id；从待核对到成立案例，走的是显式核对与显式关联，不是分类标记的自动升级。
- **matchStatus 规范语义（2026-11-22 回读全部真实案例 JSON 后确定）**：规范状态为 `verified`——案例身份已与课堂来源（课程笔记 / ASR 定位）显式核对一致，且来源位置与 `verificationBasis` 已记录。case-002 使用的 `matched` 是同一状态的历史写法：其 verificationBasis 与 case-001（`verified`）同为“ASR 内容核对 + 用户提供卦盘 + 明确限定”，证据结构与严格程度相同，不构成更低一级的状态。M2-C Mapper 读取时须把 `matched` 归一化为 `verified` 并保留原始值；新案例统一写 `verified`；`needs_review` / `not_found` / `disputed` 及任何未知值不得静默丢弃或误判，未知值保留原始值并标记待核对。注意 `verified` 只证明案例身份已核对，不代表老师讲解已通过音频逐字验证——ASR 校正状态、卦盘来源等限定以 `verificationBasis` / `matchConfidence` 等字段为准，Evidence Pack 须一并呈现。
- 每日记录仍默认不全量导入：只有显式允许的记录 ID 才进入知识库。
- M2-C 实施准备要求（本计划只记录要求，不在本 PR 实现）：（1）实施前先检查真实的 `case-001.json` 与每日记录 JSON，了解实际字段结构；（2）检查 HTML 导出 JSON 与课堂案例 JSON 的字段关系；（3）自动化测试使用合成 fixtures 独立进行，不把真实案例、私人 ASR 全文或个人每日记录复制进 fixtures；（4）映射时保留原始字段、来源链和案例身份，不随意丢弃数据；（5）不要因为已有一个案例就假定所有历史案例都符合相同结构，字段差异必须显式处理。
- daily-records/ 是否有真实记录以同步时重新扫描为准，默认仍不导入个人每日 Memo。

因此 M2 只测试 Markdown/TXT 和结构化 JSON；不为不存在的 PDF 准备 fixture 或解析器。不得为了测试伪造老师案例。

## 5. 资料来源配置与安全

外部资料目录与两个项目之间的 Package contract 见 [六爻外部参考资料来源目录](reference-source-catalog.md)。

Importer 使用显式 allowlist 配置，不扫描或上传用户电脑全部文件。

建议配置文件：tools/liuyao-kb/sources.yaml（只提交无秘密的路径/来源配置模板）。配置中明确：

- Learning 本地仓库根目录和允许的目录/文件模式；
- Private raw 本地仓库根目录（默认禁用内容读取）；
- Source Catalog 中的 source_id、获准 Reference Package 路径、选定章节/文件、固定版本/commit、License/版权及 allowlist 状态；
- PDF 仅作为未来可选来源；当前不配置 PDF 路径，不启用 PDF parser；
- 是否导入每日卦例、是否只导入 isCase=true 的记录。

**默认安全设置：**

- raw_asr.enabled=false
- daily_records.include=false，或者仅允许用户显式选中的案例记录；不要默认把所有每日 Memo 传给模型。
- external_projects 为空，须由用户选择和核对 License 后添加。
- 不从知识库 Importer 内爬取或下载外部资料；只读取显式批准的 Reference Package。
- PDF 当前关闭；未来只有选定具体文件并确认允许本地处理/云端处理后才开启。
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
│   │   ├── case_json.py
│   │   └── reference_package.py
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
| ClassCase | 老师课堂讲解的教学案例（classroom_case） | case_id、lesson_id、match_status、verification_basis、case_memo |
| Concept | 六亲、暗动、日辰等概念 | concept_id、name、aliases |
| RuleCandidate | LLM 抽取的候选规则 | candidate_id、statement、conditions、uncertainty、extractor_model、status=candidate |
| ExternalProject | 外部 GitHub 项目来源 | repo_url、commit_sha、license、license_status |
| ReferencePackage | Source Collector 输出的获准资料包 | package_id、schema_version、collector_version、created_at、validation_status |

关系示例：

- SourceDocument -[:HAS_REVISION]-> DocumentRevision
- DocumentRevision -[:CONTAINS]-> Chunk
- Chunk -[:MENTIONS]-> Concept
- RuleCandidate -[:EXTRACTED_FROM]-> Chunk
- ClassCase -[:TAUGHT_IN]-> Lesson
- ClassCase -[:HAS_REPRESENTATION]-> SourceDocument（案例的某种文件表示；关系属性 format=json 或 markdown。案例 JSON 与课堂案例 MD 都用这条关系挂到同一个 ClassCase，不另建案例节点）
- ClassCase -[:REFERENCES]-> Chunk（对已 Chunk 的来源，如课程整理笔记中的案例段落）
- ClassCase -[:REFERENCES]-> SourceDocument / DocumentRevision（对未 Chunk 的来源，主要用于 Raw ASR：关系属性保留 Locator——source_uri、仓库与文件路径、lesson_id、转录段落序号、可选时间范围——以及置信度与校正状态，如 confidence=low、verification_status=asr_unverified）
- SourceDocument（ASR 转录） -[:TRANSCRIPT_OF]-> SourceDocument（原始录音 WAV/M4A；录音补入后用这条关系把转录与原始音频关联）
- ClassCase -[:BASED_ON_RECORD]-> CastRecord（仅当 `dailyRecord.recordId` 与 CastRecord 的 record_id 明确匹配时建立）
- CastRecord -[:RENDERS]-> SourceDocument（仅指 daily-records 中 HTML 自动生成的记录 MD，是该 CastRecord 的可读呈现；与课堂案例 MD 的 HAS_REPRESENTATION 是两条不同的关系，不得混用）
- ExternalProject -[:HAS_SOURCE]-> SourceDocument

重要实现约束：

- 对 document_id、revision_id、chunk_id、record_id、case_id 建唯一约束。
- 对 JSON 中嵌套的六爻字段，用原始 JSON 字符串或明确的扁平化属性保存；不要假设 Neo4j 节点属性可直接存任意嵌套 JSON 对象。
- ClassCase 与 CastRecord 是两个独立节点，各自保留唯一 ID（case_id 与 record_id）；不得把两者压成同一个节点或同一个 ID。只有 `dailyRecord.recordId` 明确匹配时才建立 BASED_ON_RECORD 关系；匹配不明确时不建关系，并保留 matchStatus 说明。
- 同一个课堂案例的 JSON 与 MD 是同一案例的两种表示（结构化读取与人类阅读/文本检索），不产生重复 ClassCase 节点或重复案例计数；课堂案例 MD 不是独立分析资料，不得为它另立来源身份。自动生成 MD（daily-records）与课堂案例 MD 是两类文件：前者是 CastRecord 的呈现（RENDERS），其 Chunk 必须排除 `## 原始记录 JSON` 代码块，避免把内嵌 JSON 当作独立文本重复索引。
- 不得假设 Raw ASR 一定有 Chunk：案例与 ASR 的引用关系通过 ClassCase 直接关联 SourceDocument/DocumentRevision 并携带 Locator 与置信度建立；不得为了建立引用就把全部 Raw ASR 自动纳入 Chunk、Embedding 或主要课程规则抽取。
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
- record_id = HTML 每日记录 JSON 中子记录的现有稳定 id（CastRecord 的身份）；不能只用日期或卦名当 ID。
- case_id = 课堂案例的稳定身份（ClassCase 的身份，如 `L19-C01-work-transfer`）。case_id 与 record_id 是两套 ID，不得混用；只有 `dailyRecord.recordId` 明确匹配时，才在 ClassCase 与 CastRecord 之间建立 BASED_ON_RECORD。

同步行为：

| 情况 | 必须行为 |
|---|---|
| 新文件 | 创建 SourceDocument + DocumentRevision + Chunks |
| 相同文件再次运行 | 完全跳过；不得重复请求 Embedding/LLM |
| 文档修改 | 创建新 revision；仅对变化 Chunk 执行新处理；未变化 Chunk 尽量复用 |
| 文档删除/路径变化 | 标记旧来源不再 active，不物理删除历史 |
| Raw ASR v1 → v2 | 创建新 revision；不覆盖 v1，不自动提升为 Curated |
| 课堂案例内容修改（Memo、卦盘等） | 更新同一个 case_id 的 ClassCase 对应表示或 revision，并保留 audit 信息；案例身份（case_id）不变 |
| 每日记录修改 | 更新对应 record_id 的 CastRecord 当前内容，并保留 revision/audit 信息；不因此创建或替换 ClassCase |
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
2. 主要课程笔记证据：课次、文件路径、标题/段落位置、短摘录。
3. 相关课堂案例：课堂案例标签、核对状态、老师分析 Memo 和来源。
4. 个人练习案例：独立分区，不当作老师规则证据。
5. 外部古籍/网页/GitHub 参考：独立分区，附书名/作者/版本或 URL、commit SHA、License/版权状态和用途；未核实来源必须显示待核实。
6. Raw ASR 按三档规则返回（本节为唯一口径，第 12 节 M7 与其他章节与此一致）：
   - **默认返回来源元数据**：Raw ASR 所在仓库与文件路径、DocumentRevision、Locator（段落序号；有可靠时间戳时附时间范围）、来源置信度、音频校正状态。
   - **默认不返回**：Raw ASR 正文与长篇摘录。
   - **仅当用户明确启用 Raw ASR 正文时**：才返回正文或摘录，且必须放在独立的低置信度区域，并明确说明其未经音频校正，不得当成经过验证的老师逐字原话。
   此规则只管 Evidence Pack 的返回内容，不改变 Raw ASR 默认不进入主要 Chunk / Embedding / 规则抽取流程的原则。
7. 来源冲突、缺少依据和模型不确定性。
8. 提供一段可直接交给 ChatGPT 网页版的分析任务说明。

Evidence Pack 不是最终断卦报告；它是有来源依据的“证据包”。涉及课堂案例时按 case_id 归并同一案例的多种表示与来源（课程笔记提及、ASR 定位、案例 JSON 与其 MD 表示、关联的每日记录），并分开标示老师讲解、用户补充与 AI 推算；同时按上面第 6 项的三档规则返回 ASR 来源元数据（文件定位、DocumentRevision、置信度与音频校正状态）——即使该 ASR 没有 Chunk，也不得丢失它作为课堂来源的引用；正文默认不返回，须用户明确启用后才可放入低置信度区域。

## 12. 里程碑与用户验收

| Milestone | 交付物 | 用户验收标准 |
|---|---|---|
| M0：Aura 准备 | AuraDB Free 实例、凭据放本机 .env | Aura Console 显示实例运行；本机 doctor 能连通；秘密不提交 |
| M1：项目骨架 | Python CLI、配置、日志、单元测试 | doctor、sources list、ingest --dry-run 正常 |
| M2-A：来源模型 | 统一 ParsedDocument/Section、Locator、source identity | `approved_merged`；PR #3，merge commit `9505ce7` |
| M2-B：Markdown/TXT | Markdown 与 TXT Adapter | `approved_merged`；PR #3，merge commit `9505ce7`（验收：144 tests / 38 adapter tests 通过，用户接受等价复跑作为验收依据） |
| M2-C1：案例 JSON Mapping | class-case JSON 与每日记录容器中的独立子记录 Mapper | 支持 `recordType=class-case` 的课程案例 JSON，以及 HTML 每日记录容器中显式允许的子记录；保留原始字段、稳定 ID 与来源链；不把每日记录容器整体当成 Case；matchStatus 须显式处理真实历史值（`matched` 归一化为 `verified` 并保留原始值，未知值保留并标记待核对，不得静默丢弃或误判，见第 4 节）；实现须用户明确授权后启动 |
| M2-C2：自动生成 MD 伴随文件 | Generated Markdown companion | 支持 HTML 自动生成的记录 MD：校验文件名、MD 内嵌 JSON 的 ID 与原始 daily JSON 中子记录 ID 一致；MD 以 RENDERS 关系关联到 CastRecord，不创建第二个 Case；Chunk 时排除 `## 原始记录 JSON` 代码块 |
| M2-C3：课堂案例 MD 表示 | Classroom Case Markdown Representation | 处理与案例 JSON 配对的课堂案例 MD（如 `case-xxx-analysis.md`）：它是同一 ClassCase 的可读表示，以 HAS_REPRESENTATION（format=markdown）关联到同一 case_id，不建第二个 Case、不另立分析来源；内容中的老师讲解、用户补充、AI 计算仍分别标明来源 |
| M2-D：PDF | PDF 文本解析 / 页码 Locator | **deferred**；没有当前 PDF 输入，不纳入本轮 M2 |
| 外部参考包接收 | Reference Package Validator / Adapter | 首批采集验证后实施；知识库不负责爬网站 |
| M3：Neo4j Schema | 唯一约束、关系、Vector Index、测试节点 | 可创建/查询节点；向量索引 smoke test 成功 |
| M4：增量 Importer | Manifest、Hash、Chunk、MERGE、版本管理 | 第一次导入新增；第二次重复运行 0 个新 Chunk/Embedding；修改一个段落只处理变化部分 |
| M5：Gemini 双路径 | Embedding + 结构化候选抽取 | Chunk 有向量；候选知识能回到来源 Chunk；没有自动确认规则 |
| M6：外部参考资料 | 从 Source Catalog 选择并导入获准 Reference Package 中的古籍章节、网页文本、README/docs 或源码文件 | 来源/版本/版权/commit 完整；不混入老师课程来源；不在本仓库内爬取 |
| PDF 扩展 | 仅在将来用户明确指定 PDF 后单独立项 | 不属于当前 Phase 1 必需交付 |
| M7：Evidence Pack | 本地 Query Tool、向量检索 + 图关系扩展 | 输入已知问题时找到相关课堂段落/案例；输出可读、可追溯的 Markdown；同一课堂案例无论出现在课程笔记、ASR、案例 JSON 还是案例 MD 中，都按同一 case_id 归并呈现，不重复计数；Raw ASR 按第 11 节三档规则返回（默认只返回来源元数据） |
| M8：端到端验收 | 真实课程 + 真实课堂案例 + 至少一份获准的外部 Reference Package（若已完成采集） | 你能把 Evidence Pack 交给 ChatGPT，且引用来源正确、分类明确；PDF 不是验收前提 |

### 最低验收测试矩阵

- 同一 Markdown 连续导入两次，第二次不得创建重复节点或重复模型调用。
- 修改 Markdown 的一个段落，只重做变化 Chunk；未变化 Chunk ID 保持可复用。
- 同一个 Raw ASR v1 再次导入仍然处于 Raw / Low Confidence，不进入主索引。
- 新建 Raw ASR v2 时保留 v1 与 v2 两个 revision。
- Case JSON 的六爻原始字段、日期、问题、案例类型和 Memo 不得在映射中丢失。
- Reference Package 必须能通过 manifest 回溯原始 URL、章节/文件定位、版本和内容哈希。
- 当前阶段不执行 PDF Parser 测试；将来立项后 PDF Chunk 必须追溯原文件及页码，扫描件 OCR 必须单独验收。
- 外部开源项目必须显示 repository URL、commit SHA、License；不能被标注成课堂规则。
- Collector 的采集行为必须符合来源网站条款与版权许可；不绕过登录、付费墙、验证码或反爬控制。
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

## 14. 谁来实现、阶段审核与跨模型记忆

采用“Claude Code 本地执行 + ChatGPT 阶段审核 + 用户验收”的协作方式；用户也可以在不同阶段切换 Claude 模型、Codex 或其他 coding agent。**模型可以切换，项目状态不能只留在某个聊天窗口。**

### 角色分工

- **Claude Code（Mac 本机主执行者）**：在本地 checkout 中实现当前 milestone、运行测试、建立 virtualenv、连接用户在本机配置的 AuraDB/Gemini API、提交分支并创建 Draft PR。
- **ChatGPT（架构审查与验收者）**：维护实施计划、检查 GitHub PR diff、审查数据模型/安全/来源追溯/增量逻辑、解释错误、给出修改要求；审核通过后由用户决定合并，或明确授权 ChatGPT 合并。
- **用户**：创建 AuraDB Free、在本机安全保存凭据、选择获准导入的外部来源/章节或文件、逐个验收里程碑。PDF 只有未来明确选定后才考虑。不要把数据库密码或 API Key 发给 ChatGPT。

### 强制 GitHub checkpoint 流程

1. 每个 milestone 使用单独分支，例如 `phase1/m1-python-skeleton`、`phase1/m2-source-parsers`。
2. 分支从最近一个已审核并合并到 main 的版本创建；不能直接在 main 开发或推送。
3. 一个 PR 只完成一个 milestone，不把 M1–M8 一次性提交。
4. 完成后运行测试、lint、`git diff --check` 和 Secret 检查；更新 `docs/phase1-progress.md`。
5. Commit 并推送分支，创建 Draft PR 指向 main；PR 中写明改动、测试命令/结果、限制和下一阶段。
6. 把 PR URL 交给用户，再由 ChatGPT 检查 diff。审核未通过则在同一分支修复，不创建无关的新分支。
7. **未经 ChatGPT 审核和用户确认，不得合并，不得开始下一 milestone。**
8. 审核通过并合并后，更新 progress 文件中的 merge commit、状态和下一里程碑。

### 跨模型持久化记忆

- 仓库根目录 `AGENTS.md`：所有 coding agent 通用约束。
- 仓库根目录 `CLAUDE.md`：Claude Code 的入口指引。
- `docs/phase1-progress.md`：当前 milestone、已批准 main SHA、分支/PR、测试结果、阻塞项和下一步；这是模型切换时的主要记忆文件。
- `docs/claude-code-phase1-execution-prompt.md`：Claude Code 可直接使用的执行 Prompt。
- 新模型开始工作前必须先读以上文件；不得依赖旧模型的聊天摘要或声称。

详细的 checkpoint 模板和停止规则见 [AGENTS.md](../AGENTS.md)、[CLAUDE.md](../CLAUDE.md)、[Phase 1 Progress](phase1-progress.md) 与 [Claude Code 执行 Prompt](claude-code-phase1-execution-prompt.md)。

ChatGPT 可以直接检查 GitHub 上已推送的分支/PR，但无法代替用户在 Mac 上操作 Aura Console 或读取未提交的本地工作区。没有推送到 GitHub 的代码，ChatGPT 无法做完整 diff review。

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
