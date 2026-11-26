# Phase 1 实施计划：Neo4j 知识库、云端 Importer 与在线分析

> 版本：1.2
> 规划日期：2026-11-21；云端优先修订：2026-11-24
> 状态：按用户确认调整来源边界；M2-A/M2-B 已合并（PR #3，merge commit `9505ce7`）；双仓库架构与来源目录规划已合并（PR #4，merge commit `65fb501`），main 已包含 Reference Source Catalog、Reference Package Schema 与双仓库架构；M2 已全部完成（M2-A/B 合并于 PR #3；M2-C1/C2/C3 分别合并于 PR #7/#8/#10，见第 12 节）；2026-11-24 用户决策 Phase 1 改为云端优先与完整在线分析（方案 B），M3 代码与云端部署配置已合并（PR #15，merge commit `a1829941`；部署文档修订 PR #16，merge commit `c1b918b`），但真实云端 Schema 尚未执行——云端资源创建按用户 2026-11-25 决定暂停于部署 Phase 2（创建 Artifact Registry）之前；第一份真实资料试点已选定（见第 4 节），下一项工程任务为 M4a Chunker；PDF Adapter/OCR 继续 deferred
> 如果本文与早期概念文档有差异，以本文的实施范围和验收标准为准。概念解释见 [Phase 1 实际运行架构](phase1-operating-model.md)。

## 1. 目标与最终交付

Phase 1 的最终产品是完整在线分析（2026-11-24 用户决策，方案 B）：用户在现有 HTML 页面录入或选择卦例并点击“分析”，云端自动检索知识库、构建证据上下文、调用生成模型，最后直接在 HTML 页面显示完整六爻分析报告和出处。

1. 用户继续在现有 HTML App 排卦、录入课堂案例、保存每日记录；Cloudflare Pages + Pages Functions + GitHub 流程保持不变。
2. 资料导入由运行在 Google Cloud Run Jobs 上的 Python Importer 执行（本地运行仅作开发便利，不依赖用户的固定 Mac），把经过选择的课程笔记、案例 JSON，以及独立 Source Collector 输出的标准 Reference Package 增量同步到 Neo4j AuraDB Free 云端图数据库。
3. Importer 对主要课程资料执行 Chunk、Embedding 和候选知识抽取；案例 JSON 由确定性的 Case Mapper 读取，不让 LLM 重新猜测卦盘。
4. 在线分析由 Google Cloud Run Service 承载：接收经认证的分析请求，搜索 Neo4j，组合向量检索、关键词检索和图关系扩展，构建内部 Evidence Context（即 Evidence Pack 的内部结构，不再要求用户手工复制给 ChatGPT）。
5. 生成模型在云端生成完整分析报告（结论、推理依据、相关课程与老师案例、原始来源出处、不确定性说明），返回 HTML 页面展示。

**Phase 1 完成时的可见成果：** 用户从浏览器发起分析，云端完成检索和生成，网页显示有来源依据的分析报告（M8 端到端验收）。

## 2. Phase 1 不做什么

- 云端运行环境只使用 Google Cloud Run（Service 承载在线分析 API、Jobs 承载批处理）；不自建其他在线 Backend、不自托管 Neo4j。Cloud Run 的实际部署分别在 M3（最小基础与 Schema Job）与 M7（分析 Service）完成；本文档描述的是目标架构，不代表已经部署。
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

  subgraph MAC["Google Cloud Run：Phase 1 执行（Jobs 导入 / Service 分析）"]
    I["Python Importer"]
    S["Source Scanner + Parser"]
    H["Hash / Revision / Chunker"]
    E["检索层（M7 起位于 Cloud Run Service）"]
    P["内部 Evidence Context"]
  end

  subgraph MODELS["模型服务（Vertex AI Gemini 优先评估，M5/M7 确定）"]
    EM["Embedding Model"]
    GL["Generative LLM：候选知识抽取"]
  end

  N[("Neo4j AuraDB Free：Document / Revision / Chunk / Case / Concept / RuleCandidate / Relationships / Vector Index")]

  subgraph HUMAN["最终分析（Cloud Run Service，M7）"]
    GEN["生成模型：Evidence Context + 卦盘事实"]
    REPORT["完整分析报告 → 返回 HTML 展示"]
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
  E --> P --> GEN --> REPORT
~~~

**部署位置：**

| 组件 | 运行位置 | Phase 1 部署方式 |
|---|---|---|
| HTML App | Cloudflare Pages | 保持现状 |
| Pages Functions | Cloudflare Workers Runtime | 保持现状 |
| GitHub 代码、整理笔记、每日记录 | GitHub | 保持现状 |
| Python Importer（批处理） | Google Cloud Run Jobs | M4 起部署；本地运行仅作开发便利 |
| 在线分析 API（检索 + 生成） | Google Cloud Run Service | M7 部署（FastAPI）；Evidence Pack 为其内部 Evidence Context |
| Embedding / 生成模型 | Google 托管（Vertex AI Gemini 优先评估） | 模型与生产维度在 M5/M7 确定；由 Cloud Run 运行时身份调用 |
| Neo4j AuraDB Free | Neo4j 托管云服务 | 本项目唯一知识图谱主库 |
| LLM Knowledge Graph Builder | Neo4j Labs 在线工具 | 可选试验，不依赖它运行 |
| Secret Manager | Google Cloud | 保存 Neo4j 凭据等秘密；Secret `neo4j-aura-credentials` 已创建，Version 4 已由临时 Cloud Run Job 实测读取并连接成功（2026-11-25）；只有 Cloud Run 运行时经文件挂载读取 |
| GitHub Actions + OIDC/WIF | GitHub / Google Cloud | 部署认证；不保存长期 Service Account JSON Key；WIF 所需三个 API（STS、IAM Service Account Credentials、Cloud Resource Manager）已于 2026-11-25 启用并回读确认；WIF Pool/Provider 与部署身份尚未创建（云端资源创建暂停中） |

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

### 当前资料状态（最近核对：2026-11-25，已含第十九课 case-003）

- liuyao-learning-app 有第 5～20 课整理笔记、外部参考文档和案例目录说明；正式课程笔记以 Markdown 为主。
- liuyao-learning-raw 有部分课程原始 ASR TXT；Raw ASR 默认不进入主要索引。
- 2026-11-19 的两个仓库 main 分支扫描均未发现 PDF；2026-11-21 的 ChatGPT Library PDF 清单也没有返回 PDF。当前没有已选定、准备导入的 PDF。
- 课堂案例相关资料目前有四种不同形式，必须区分处理（以下均已按 main 真实文件核对）：
  1. **课程案例 JSON**：`materials/class-cases/lesson-19/case-001.json`，`recordType=class-case`，独立案例 ID `L19-C01-work-transfer`，`lessonId=lesson-19`，并通过 `dailyRecord.recordId` 关联到 HTML 每日记录中的子记录 `9f89c47a-ba51-44d1-81b5-ffba16a30ca2`；其 `matchStatus=verified`，`verificationBasis` 记录了与第十九课 ASR 讲解的核对依据。
  2. **课堂案例 MD 表示**：`materials/class-cases/lesson-19/case-001-analysis.md` 是 case-001 这同一个课堂案例的配对 Markdown 资料，与案例 JSON 同属一个 `case_id`，是同一案例的另一份不同资料（可包含分析内容、来源链接与上下文，内容可与 JSON 不同），不是独立案例、不另立案例身份；它与下面第 4 项的每日记录生成 MD 是两类不同的 MD，不得混淆。文件内容中出现的老师课堂讲解、用户补充的卦盘、用户 memo、AI 计算仍须分别标明来源——同属一个案例不等于来源权威性相同。
  3. **HTML 每日记录 JSON**：`daily-records/2026/11/2026-11-21.json` 是每日记录容器，顶层不是案例；其 `additionalQuestions[]` 中有多个独立子记录（各有自己的 UUID、`recordType=additionalQuestion`、`isCase`、`caseSource`）。不得把整个每日记录容器当成一个 Case。注意该文件内两个子记录都带 `isCase=true`、`caseSource=classroom`，但只有 `9f89...` 被 case-001 显式关联——`isCase`/`caseSource` 只能用于分类，不能仅凭它们自动认定某条记录已匹配到具体课堂案例或已验证。
  4. **自动生成的记录 MD**：`daily-records/2026/11/markdown/2026-11-21--7e0a6b19-92f2-4f8c-b7b0-8771955ad45b.md` 是 HTML 按每日记录 JSON 与确定性排盘规则生成的可读呈现，对应子记录 `7e0a6b19-...`（与 case-001 关联的 `9f89...` 是两条不同记录，不得混淆）；其 `## 原始记录 JSON` 一节内嵌完整 JSON。它是该记录的另一种表示，不是第二个独立案例，不得重复创建 Case 节点或重复计数。
- **课堂案例身份原则（核心）**：Learning App 中的课堂案例是老师在实际课程中讲解过的教学案例（`classroom_case`），不是用户新创建的个人练习数据，不得归类为 `personal_practice`；个人练习是独立类别。每个课堂案例应尽可能连接五类来源：（1）老师原始课堂录音 / ASR 转录中的案例讲解位置；（2）对应课程整理笔记中的案例内容；（3）用户补充并核对的完整卦盘结构；（4）HTML 保存的 JSON 记录及其生成 MD 表达；（5）与案例 JSON 配对的课堂案例 MD 表示。课程笔记或 ASR 提到同一案例时，建立引用/提及关系并保留课程、文件、段落或时间定位；同一案例在笔记、ASR、案例 JSON、案例 MD 中重复出现，不产生多个案例。案例 JSON 与课堂案例 MD 都只是该案例的表示形式：在图模型中以 `ClassCase -[:HAS_REPRESENTATION]-> SourceDocument` 表达（关系上标明 format=json/markdown），不为 MD 另建案例身份。老师 ASR 的来源定位不依赖 Chunk：Raw ASR 默认不 Chunk，ClassCase 可以直接关联 ASR 的 SourceDocument / DocumentRevision，并在关系上保留 Locator（原始仓库与文件路径、课程 ID、转录段落序号、有可靠时间戳时的时间范围）与置信度/校正状态；未经音频校正的 ASR 只能标为当前可用的老师讲解线索，不得称为经音频验证的逐字原话。案例身份规则：保留稳定案例 ID；课程归属用 `lessonId` 与来源定位表达；HTML 原始记录 ID 只通过明确的 `dailyRecord.recordId` 关联；JSON 与课堂案例 MD 通过同一个稳定 `case_id` 关联到同一个 ClassCase；两者是同一案例的两份不同资料，不要求内容一致，关联依据是同目录文件约定与 case_id，而不是内容比对；两者内容冲突时保留各自来源并标记待核对，不静默合并；`matchStatus` / `verificationBasis` 说明与课堂原始教学资料的匹配程度；ASR 未经音频校正时保留低置信度说明；用户补充的卦盘结构、老师原话、AI 推算必须分开标记，不得混为一谈。此原则同时适用于 M2-C 的 Mapper、M3 的 Neo4j 数据模型与 M7 的 Evidence Pack 检索逻辑。
- **案例核对生命周期样本（2026-11-22，真实数据）**：`daily-records/2026/11/2026-11-22.json` 的子记录 `13e9c29a-cdbc-41e0-912d-5e02fa7c54d3` 最初只有 `isCase=true`、`caseSource=classroom` 标记，其生成 MD 标注“案例核对状态：待核对”，记录本身没有 case_id 或 matchStatus——按上列身份原则，它当时只是待核对的 CastRecord 候选：不创建已验证的 ClassCase、不建 BASED_ON_RECORD、不计入课堂案例数量。其后它被显式核对并配对为第十九课案例：`materials/class-cases/lesson-19/case-002.json`（稳定 case_id `L19-C02-shop-operation-transfer`，`matchStatus=matched`，附 `verificationBasis`）通过 `dailyRecord.recordId` 显式关联该子记录，ClassCase 身份自此才成立。注意：关联信息保存在案例 JSON 一侧，每日记录本身没有被回填 case_id；从待核对到成立案例，走的是显式核对与显式关联，不是分类标记的自动升级。
- **case-003（2026-11-24 新增，第十九课第三个已建档案例）**：`materials/class-cases/lesson-19/case-003.json`（稳定 case_id `L19-C03-female-marriage-multiple-guangui`，`matchStatus=verified`，案例身份由用户明确确认）通过 `dailyRecord.recordId` 关联 `daily-records/2026/11/2026-11-24.json` 的子记录 `518d525a-838e-479d-8d2c-815296358b5e`；该子记录有自动生成 MD（`daily-records/2026/11/markdown/2026-11-24--518d525a-838e-479d-8d2c-815296358b5e.md`），配对课堂案例 MD 为 `materials/class-cases/lesson-19/case-003-analysis.md`；第十九课整理稿第 7 节为其专节、第 10 节记录了完整关联链。至此第十九课共有三个已建档课堂案例（case-001 / case-002 / case-003）。
- **第一份真实资料试点（2026-11-25 选定）**：第十九课整理笔记（`docs/lessons/lesson-19-notes-v0.1.md`）+ case-003 为主案例 + case-002 为辅助案例（辅助目的是覆盖 `matched → verified` 归一化路径）。试点口径：每日记录容器 JSON 不单独建立 SourceDocument，容器路径与 recordId 作为 CastRecord 的来源信息保存；每日生成 MD 可作为 SourceDocument 并以 RENDERS 关联 CastRecord，但默认不作为课程 Embedding 输入。case-002 在课程笔记中的引用定位：以第 3 节解释段落为主要 REFERENCES 定位、第 10 节汇总表行为第二定位，均指向同一个 case_id、不重复创建 ClassCase；表格定位无法可靠解析时不得伪造 offset。**目前尚无任何真实课程 Chunk、Embedding、Neo4j 导入或检索的业务验收记录**——M2 的合并是解析/映射代码交付，不等于资料已进入知识库。
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
- Chunk 身份与定位分层（M4a 契约，2026-11-26）：Chunk 节点只保存跨 revision 稳定的内容属性（chunk_id、text、text_hash，以及 M5 的 embedding、embedding_model、embedding_dimensions）。某个 Chunk 在某个 revision 中的出现位置属于 revision-specific locator，保存在 `DocumentRevision -[:CONTAINS]-> Chunk` 的关系属性上：paragraph_ordinal、subchunk_index、heading_path（字符串数组）、start_offset、end_offset；revision_id 由 CONTAINS 的起点 DocumentRevision 节点表达，不得把会随 revision 变化的定位值写成共享 Chunk 节点的单一属性。节点目录中原有的 `ordinal`、`heading` 是本分层之前为同一批定位数据预留的名称（ordinal 对应段落序号、heading 对应标题信息）：按本契约改由 CONTAINS 关系承载，M4b 不得将其写到 Chunk 节点上；二者暂保留为目录中的历史名称，是否从 Schema 目录移除留待后续 Schema 修订单独决定（真实 Schema 尚未执行，无迁移问题；本条不修改 M3 Schema 代码）。`page` 对 Markdown 无意义，保持不写。关系属性不受数据库约束强制，由 Importer 在应用层校验（与既有约定一致）。
- 对 JSON 中嵌套的六爻字段，用原始 JSON 字符串或明确的扁平化属性保存；不要假设 Neo4j 节点属性可直接存任意嵌套 JSON 对象。
- ClassCase 与 CastRecord 是两个独立节点，各自保留唯一 ID（case_id 与 record_id）；不得把两者压成同一个节点或同一个 ID。只有 `dailyRecord.recordId` 明确匹配时才建立 BASED_ON_RECORD 关系；匹配不明确时不建关系，并保留 matchStatus 说明。
- 同一个课堂案例的 JSON 与 MD 是同一案例的两份不同资料（JSON 为结构化记录；MD 为可读资料，可包含自身分析内容、来源链接与上下文），不要求内容一致，不产生重复 ClassCase 节点或重复案例计数，也不为 MD 另立案例身份；两者各自保留来源、路径与版本，内容冲突时保留各自来源、标记待核对、不静默合并；MD 中的链接只登记引用信息，不自动抓取目标文件；老师分析、用户 Memo、AI 分析保留各自来源身份，不能互相转化为老师确认内容。M2-C1 只识别配对 MD 的路径、存在状态与 case_id 关联（不解析正文），M2-C3 负责解析 MD 正文。自动生成 MD（daily-records）与课堂案例 MD 是两类文件，不得共用身份模型：前者是 CastRecord 的呈现（RENDERS），其 Chunk 必须排除 `## 原始记录 JSON` 代码块，避免把内嵌 JSON 当作独立文本重复索引。
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
- chunk_id = document_id + chunker_version + paragraph_ordinal + subchunk_index + chunk_text_hash（M4a 修订：身份由段落序号 + 段内子块序号 + 正文哈希组成；不使用 revision_id 与绝对 offset 作为身份输入，保证只修改一个段落时其他段落的 chunk_id 不变、相同正文的不同段落不冲突；稳定性边界见 `tools/liuyao-kb/src/liuyao_kb/ids.py` 中 `make_chunk_id` 的说明）。
- Chunk 存储分层契约（M4b 实现依据，2026-11-26）：Chunker 的输出对象（Python `Chunk`）是一次切分运行的 occurrence DTO，同时携带稳定身份字段与 revision-specific locator 字段；M4b 写入 Neo4j 时必须拆开——身份字段（chunk_id、text、text_hash）进 Chunk 节点，locator 字段（paragraph_ordinal、subchunk_index、heading_path、start_offset、end_offset）进 CONTAINS 关系属性，revision_id 由 CONTAINS 起点节点表达。同一 chunk_id 在不同 revision 中以不同 locator 出现是正常形态，不是冲突。详见第 7 节实现约束。
- record_id = HTML 每日记录 JSON 中子记录的现有稳定 id（CastRecord 的身份）；不能只用日期或卦名当 ID。
- case_id = 课堂案例的稳定身份（ClassCase 的身份，如 `L19-C01-work-transfer`）。case_id 与 record_id 是两套 ID，不得混用；只有 `dailyRecord.recordId` 明确匹配时，才在 ClassCase 与 CastRecord 之间建立 BASED_ON_RECORD。

Chunker 首版规则（用户 2026-11-25 决定；本计划只记录，M4a 实现）：

- 一个非空 Markdown 正文段落原则上一个 Chunk；Heading 层级、标题、段落序号与字符 offset 全部保留（沿用 M2 的 MarkdownLocator）。
- 正文上限暂定 1,200 个 Unicode 字符；超长段落优先按句子边界拆分，仍过长时确定性地按字符边界拆分。
- 首版不使用 overlap；首版不合并短段落。
- `chunker_version` 必须明确记录（进入 chunk_id 公式与 DocumentRevision 属性）；此为首版工程配置，后续根据 M5 的真实检索效果评估调整。

同步行为：

| 情况 | 必须行为 |
|---|---|
| 新文件 | 创建 SourceDocument + DocumentRevision + Chunks |
| 相同文件再次运行 | 完全跳过；不得重复请求 Embedding/LLM |
| 文档修改 | 创建新 revision；仅对变化 Chunk 执行新处理；未变化 Chunk 尽量复用 |
| 文档删除/路径变化 | 目标行为：标记旧来源不再 active，不物理删除历史。**M4b 未实现（明确延期）**：冻结的 M3 属性目录中 SourceDocument 没有 active 类属性，本轮不擅自扩 Schema；当前行为是未被本轮计划扫描到的文档不删除、不标记（行为已由测试固定），待单独 Schema 设计决定标记方式后再实现 |
| Raw ASR v1 → v2 | 创建新 revision；不覆盖 v1，不自动提升为 Curated |
| 课堂案例内容修改（Memo、卦盘等） | 更新同一个 case_id 的 ClassCase 对应表示或 revision，并保留 audit 信息；案例身份（case_id）不变 |
| 每日记录修改 | 更新对应 record_id 的 CastRecord 当前内容；不因此创建或替换 ClassCase。**revision/audit 保留为已知缺口（明确延期）**：冻结目录中 CastRecord 没有 revision/audit 属性、容器又不是 SourceDocument，图内无法保留旧版本；M4b 已实现当前内容更新与未变化跳过，运行级审计由 IngestReport 的逐条 outcome（created/updated/unchanged）与 provenance（容器路径 + JSON Pointer，不含正文）承担，图内历史保留待单独 Schema 设计 |
| 规则候选重复抽取 | 使用稳定 candidate_id / MERGE 去重；始终保留来源 Chunk |

Importer 实现契约（M4b，2026-11-26 落地，`tools/liuyao-kb/src/liuyao_kb/neo4j/importer.py` 与 `ingest.py`）：

- 每个文档 revision 的写入是一个 Neo4j 写事务：先做 Chunk 冲突检查（已有 chunk_id 正文或 text_hash 不一致即报错终止，错误信息只含 id 与哈希、不含正文，事务回滚），再依次 MERGE 文档、revision、Chunk 节点与 CONTAINS 关系，`current_revision_id` 作为事务内最后一条语句更新——中途失败不可能留下指针超前于数据的状态。
- 未变化判定：revision 的 content_hash、parser_version、chunker_version 与导入一致且 status 为 `imported`（DocumentRevision.status 在完整写入后置为该值）时判定 unchanged，不执行任何写事务。内容变化生成新 revision，历史 revision 及其 CONTAINS 保留；同一内容更换 chunker/parser 版本时只删除并重写该 revision 自己的 CONTAINS 集合，Chunk 节点不删除（可被其他 revision 复用），且仅当该 revision 是当前 revision 时才移动 current_revision_id。
- 节点属性严格以第 7 节 NODE_SPECS 目录为准，不新增属性：CastRecord 的容器路径与 json_pointer 是来源 provenance，携带于导入 DTO 与运行报告，不写入节点；图内文件级锚点为生成 MD 的 SourceDocument（经 RENDERS）。ClassCase 的原始 matchStatus 拼写（如 `matched`）保存在 JSON 表示的 HAS_REPRESENTATION 关系属性 `match_status_raw` 上，节点保存归一化值。
- 案例到课程笔记的 REFERENCES 只由显式 CaseReferenceSpec（笔记 document_id + 章节标题前缀 + primary/secondary 角色）生成，指向整段 Chunk，不推断、不伪造行内 offset；目标 Chunk 不存在时报错，不静默丢弃。其可审查配置入口是 sources 配置的 `case_references`（case_id + notes_path + 章节前缀/角色列表，模板见 `sources.example.yaml`，含第十九课试点映射）；CLI 的 dry-run 与真实执行共用同一配置，编程式传入的 spec 按 case_id 覆盖配置项。
- 关系端点缺失一律是失败而非跳过：计划要求创建的 BASED_ON_RECORD / RENDERS 在任一端点缺失时抛 ImporterError 并进入运行报告 failures（CLI 非零退出）；HAS_REPRESENTATION 在案例导入事务内回读校验，目标文档未导入则整个案例事务回滚，不留半条关系。TAUGHT_IN 只 MATCH 已存在的 ClassCase 与 Lesson 再 MERGE 关系——Lesson 只能由 Lesson 导入路径创建，案例导入永不自动补建只有 lesson_id 的占位 Lesson；Lesson 未先导入时案例事务失败回滚。
- 显式 `case_references` 配置是 fail-closed（第二轮审查修订）：配置内重复 case_id、同一条目内重复 heading_prefix 在配置加载期即被拒绝；计划构建期逐项验证——case_id 必须在本次计划的案例中、notes 文档必须在本次计划中且已产生 Chunk、每个 heading_prefix 至少匹配一个 Chunk、重叠章节对同一 Chunk 的角色必须一致（冲突即配置错误，不以先到者静默决定）——任一不满足抛 IngestPlanError，collect_plan 失败，CLI 两种模式都在任何写入前以非零退出。编程式 reference_specs 的宽松跳过语义只保留给编程式调用方，与配置路径明确区分。
- CastRecord 导入返回逐条结果（created / updated / unchanged + 容器路径与 JSON Pointer），未变化不写、变化更新当前内容；图内历史版本保留是上表标注的延期缺口。生成 MD 与 CastRecord 的关联经 M2-C2 容器校验绑定（MD 的 record 必须是该容器在同一 allowlist 下实际映射出的 CastRecord——身份级校验；M2 Mapper 不提供嵌入 JSON 与容器子记录的全文内容比对，不声称已验证完整内容一致）。
- 编排层只复用 M2 文件级 Mapper 与 M4a Chunker；repository slug 是显式参数（与 Mapper 签名一致）。每日容器 JSON 不建 SourceDocument；生成 MD 默认不切分（如未来允许，必须以 M2-C2 的 body_sections 为输入）。Raw ASR 不进入本管线。

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
- M5 阶段它只做候选知识抽取，不生成最终报告；最终报告由 M7 的在线分析流程调用生成模型完成（同一模型层、不同用途，见第 11、12 节）。

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

Evidence Pack 是检索证据的结构定义。M7 起它作为 Cloud Run Service 内部的 Evidence Context 使用：由后端生成、供生成模型消费，最终以“分析报告 + 来源出处”的形式呈现给用户，不再要求用户手工复制给 ChatGPT；在此之前，本地 CLI 输出 Markdown 的形式可用于开发验证，默认不自动提交到 Public GitHub。其内容至少包含：

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
8. 附带生成指令要素（用户问题、卦盘事实引用、来源分区与不确定性标注要求），供 M7 的生成步骤直接消费；不再以“交给 ChatGPT 网页版”为交付形态。

Evidence Pack 不是最终断卦报告；它是有来源依据的“证据包”。涉及课堂案例时按 case_id 归并同一案例的多种表示与来源（课程笔记提及、ASR 定位、案例 JSON 与其 MD 表示、关联的每日记录），并分开标示老师讲解、用户补充与 AI 推算；同时按上面第 6 项的三档规则返回 ASR 来源元数据（文件定位、DocumentRevision、置信度与音频校正状态）——即使该 ASR 没有 Chunk，也不得丢失它作为课堂来源的引用；正文默认不返回，须用户明确启用后才可放入低置信度区域。

## 12. 里程碑与用户验收

> **第一轮执行顺序（用户 2026-11-23 决定，2026-11-24 按云端架构更新）**：第一轮主路径为 M3 → M4 → M5 → M7 → M8，只用现有课程笔记、课堂案例及每日记录完成端到端验收（M2-C 已完成）。M6（外部参考资料）是延期的非阻塞工作：M8 验收后再恢复，不作为 M7/M8 的前置条件或依赖；M6 不取消，其来源、版本与版权要求不变。

| Milestone | 交付物 | 用户验收标准 |
|---|---|---|
| M0：Aura 准备 | AuraDB Free 实例创建、连接与 Vector Index 验证（已完成，见 phase1-m0-validation.md）；现行实例为 `97d17d42`（Instance01 已被取代）；Secret Manager `neo4j-aura-credentials` Version 4 已接入并经临时 Cloud Run Job 实测（2026-11-25） | 已完成（连接性与凭据接入）；秘密不提交；真实 Schema 执行属于 M3 云端执行，不在本行范围 |
| M1：项目骨架 | Python CLI、配置、日志、单元测试 | doctor、sources list、ingest --dry-run 正常 |
| M2-A：来源模型 | 统一 ParsedDocument/Section、Locator、source identity | `approved_merged`；PR #3，merge commit `9505ce7` |
| M2-B：Markdown/TXT | Markdown 与 TXT Adapter | `approved_merged`；PR #3，merge commit `9505ce7`（验收：144 tests / 38 adapter tests 通过，用户接受等价复跑作为验收依据） |
| M2-C1：案例 JSON Mapping | class-case JSON 与每日记录容器中的独立子记录 Mapper | 支持 `recordType=class-case` 的课程案例 JSON，以及 HTML 每日记录容器中显式允许的子记录；保留原始字段、稳定 ID 与来源链；不把每日记录容器整体当成 Case；matchStatus 须显式处理真实历史值（`matched` 归一化为 `verified` 并保留原始值，未知值保留并标记待核对，不得静默丢弃或误判，见第 4 节）；实现须用户明确授权后启动 |
| M2-C2：自动生成 MD 伴随文件 | Generated Markdown companion | 支持 HTML 自动生成的记录 MD：校验文件名、MD 内嵌 JSON 的 ID 与原始 daily JSON 中子记录 ID 一致；MD 以 RENDERS 关系关联到 CastRecord，不创建第二个 Case；Chunk 时排除 `## 原始记录 JSON` 代码块 |
| M2-C3：课堂案例 MD 表示 | Classroom Case Markdown Representation | 处理与案例 JSON 配对的课堂案例 MD（如 `case-xxx-analysis.md`）：它是同一 ClassCase 的可读表示，以 HAS_REPRESENTATION（format=markdown）关联到同一 case_id，不建第二个 Case、不另立分析来源；内容中的老师讲解、用户补充、AI 计算仍分别标明来源 |
| M2-D：PDF | PDF 文本解析 / 页码 Locator | **deferred**；没有当前 PDF 输入，不纳入本轮 M2 |
| 外部参考包接收 | Reference Package Validator / Adapter | 首批采集验证后实施；知识库不负责爬网站 |
| M3：Neo4j Schema + 最小云端执行基础 | 节点/关系目录、唯一约束、Vector Index 管理；GCP Project、Secret Manager、最小权限身份、GitHub OIDC/WIF 与一次性 Cloud Run Schema Job 的最小基础 | 代码已合并（PR #15 `a1829941`、PR #16 `c1b918b`）；云端执行未开始：AR 仓库、两个 SA、WIF Pool/Provider、Schema Job 均未创建（用户 2026-11-25 决定暂停于部署 Phase 2 之前；三个 WIF API 已启用）；五项唯一约束与临时向量索引 smoke 的云端验收、真实业务验收均未进行 |
| M4：云端增量 Importer（Cloud Run Job） | Manifest、Hash、Chunk、MERGE、版本管理 | 第一次导入新增；第二次重复运行 0 个新 Chunk/Embedding；修改一个段落只处理变化部分；**M4a Chunker 已合并（PR #18）；M4b Importer 已合并（PR #19，merge commit `805c53b`；同步状态按第 8 节存于 Neo4j 节点，不另建本地同步库）；真实导入未执行——M4c（真实试点导入与验证）任务书已提出、未启动，待单独授权** |
| M5：云端 Embedding 与 AI 知识抽取（Cloud Run Job） | Embedding + 结构化候选抽取 | Chunk 有向量；候选知识能回到来源 Chunk；没有自动确认规则；Embedding/生成模型与生产向量维度在此确定（优先评估 Vertex AI Gemini）；**未开始：无 Embedding/抽取代码，模型与生产维度未定，无真实业务验收记录** |
| M6：外部参考资料 | 从 Source Catalog 选择并导入获准 Reference Package 中的古籍章节、网页文本、README/docs 或源码文件 | 来源/版本/版权/commit 完整；不混入老师课程来源；不在本仓库内爬取 |
| PDF 扩展 | 仅在将来用户明确指定 PDF 后单独立项 | 不属于当前 Phase 1 必需交付 |
| M7：在线分析 API + HTML 对接 | Cloud Run FastAPI 分析端点；向量 + 关键词 + 图关系检索；内部 Evidence Context；生成完整报告；Pages Function 同源代理（BFF 形态与服务间认证方式待设计确认） | 登录用户可从 HTML 触发分析并看到带出处的完整报告；未授权请求被拒绝；同一课堂案例无论出现在课程笔记、ASR、案例 JSON 还是案例 MD 中，都按同一 case_id 归并，不重复计数；Raw ASR 按第 11 节三档规则处理（默认只用来源元数据） |
| M8：端到端验收 | 浏览器到报告的完整在线流程（真实课程 + 真实课堂案例） | 从 HTML 登录、选择/录入卦例、点击分析，到云端检索/生成并在网页显示报告及出处全程通过；引用来源正确、分类明确；M6 外部资料与 PDF 均不是验收前提 |

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

## 13. Phase 2 边界（2026-11-24 修订）

在线分析已提前到 Phase 1（M7 在线分析 API、M8 端到端验收），不再属于 Phase 2。AuraDB 从 M0 起就是云端主库，Phase 2 不做数据库迁移，也不再负责第一次实现 Cloud Run 在线分析。

Phase 2 留给真正的扩展项：多用户与租户隔离、私人资料存储、分析报告历史与权限管理、异步任务/队列、通知、复杂工作流、生产级监控/备份/灾备、更多模型 Provider、规则引擎扩展，以及 AuraDB 付费层的容量与可用性优化。Phase 1 不提前引入这些复杂度。

## 14. 谁来实现、阶段审核与跨模型记忆

采用“Coding Agent 云端开发执行 + ChatGPT 阶段审核 + 用户验收”的协作方式；用户也可以在不同阶段切换 Claude 模型、Codex 或其他 coding agent。**模型可以切换，项目状态不能只留在某个聊天窗口。**

### 角色分工

- **Coding Agent（云端开发环境执行者）**：在与用户 Mac 独立的开发环境中实现当前 milestone、运行离线测试、提交分支并创建 Draft PR；开发环境不持有生产数据库密码。需要真实数据库或云端资源的验证步骤，由 Cloud Run Job 以其 runtime identity 执行，或由用户在控制台/本机执行并回传结果。
- **ChatGPT（架构审查与验收者）**：维护实施计划、检查 GitHub PR diff、审查数据模型/安全/来源追溯/增量逻辑、解释错误、给出修改要求；审核通过后由用户决定合并，或明确授权 ChatGPT 合并。
- **用户**：管理 AuraDB 与 Google Cloud 账户（凭据恢复、Project/Billing、把凭据录入 Secret Manager 等控制台操作由用户完成）、选择获准导入的外部来源/章节或文件、逐个验收里程碑。PDF 只有未来明确选定后才考虑。不要把数据库密码或 API Key 发给 ChatGPT 或任何 AI 对话；生产凭据只进入 Secret Manager，本机 m0.env 仅作开发便利。

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
