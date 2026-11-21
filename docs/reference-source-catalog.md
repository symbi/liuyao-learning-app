# 六爻外部参考资料来源目录

> 本目录是外部参考来源的登记与审核入口，不是课程规则本身。它只记录来源、使用边界和导入状态；原文采集与 Chunk 导入分开管理。
> 最近整理：2026-11-21。来源状态均为候选/待核验，除非明确标为已批准；链接可访问不等于允许批量复制或再分发。

## 1. 目的与边界

本项目长期积累三类知识证据：老师课程与案例、古籍/现代文献、开源项目与技术资料。它们可以在同一个 Neo4j 中检索，但必须保留不同的 source type、trust level 和 provenance，不能把外部规则说成老师课堂口径。

外部资料处理采用三层流程：
1. **Source Catalog**：登记书目、网站、GitHub 项目、具体章节/文件、作者、版本、许可证/版权状态、用途、审核状态。
2. **Acquisition & Snapshot**：独立仓库 `symbi/liuyao-source-collector` 负责网站/平台适配、合法下载、分页/章节采集和校验。原始文件落到用户本机或获准的私有存储；不把第三方全文放进公共代码仓库。
3. **Knowledge Ingestion**：本仓库只接收经筛选且许可状态明确的标准资料包，执行 Parser、Chunk、Embedding、结构化抽取和 Neo4j 入库。

GitHub 集成当前不提供直接创建新 repository 的操作。因此 `symbi/liuyao-source-collector` 是已确定的仓库名称与架构决策，但远端仓库仍需通过 GitHub UI 或 `gh repo create` 建立；不要把它描述成已经创建。

## 2. 当前登记来源

### 2.1 古籍与在线数字文本

| Source ID | 书名/资源 | 当前登记入口 | 当前已掌握内容 | 状态 / 限制 |
|---|---|---|---|---|
| `CLASSIC-ZSBY` | 《增删卜易》 | [维基文库](https://zh.wikisource.org/zh-hans/增删卜易)；[日辰章第十七](https://zh.wikisource.org/zh-hans/增删卜易/17)；[识典古籍·暗动章](https://www.shidianguji.com/book/XYXZSBY/chapter/1lzxsnhvbt0re) | 已登记日辰、暗动、月建、月破、求财、用神、六冲、三合等章节链接；有第三方 GitHub TXT 录文线索 | `candidate`；核验版本、文本完整性、站点条款和版权；不是已下载的 PDF |
| `CLASSIC-BSZ` | 《卜筮正宗》 | [识典古籍·用神分类](https://www.shidianguji.com/book/HY0057/chapter/1lpdfpdr8oqhb)；[全书/卷三相关文本](https://www.shidianguji.com/book/AMNL0060/chapter/1ma05ao3rvqqy) | 已登记十八论用神、伏神、世应、旺相休囚、婚姻、产育等章节线索 | `candidate`；不同网站可能是不同整理/版本，需建立版本记录 |
| `CLASSIC-YM` | 《易冒》 | [识典古籍·卷五](https://www.shidianguji.com/book/NA06416/chapter/1m7f91wiutn38)；[中国哲学书电子化计划](https://ctext.org/wiki.pl?chapter=966762&if=gb&remap=gb) | 已登记年运章、身命章相关入口 | `candidate`；待核对版本及章节正文 |
| `CLASSIC-BSQ` | 《卜筮全书》 | [识典古籍·求名](https://www.shidianguji.com/book/HY1394/chapter/1l3wdpl9z8njc) | 已登记求名篇，作为课堂求学/求名议题的外部对照 | `candidate`；只登记特定章节，不代表已有全书文本 |
| `CLASSIC-ZZSY` | 《增注周易神应六亲百章海底眼前集》 | [识典古籍相关段落](https://www.shidianguji.com/zh/mid-page/7592368347519909898) | 已有旺相休囚等段落的研究链接 | `candidate`；作者、版本、校注及文本权利待查 |
| `CLASSIC-YXST` | 《易学四同别录》 | [识典古籍·浑天六位图](https://www.shidianguji.com/zh/book/7398438943139561524/chapter/1kbmc0gwj4mxn) | 已登记五行旺衰、浑天六位图相关入口 | `candidate`；版本、卷次和文本授权待查 |
| `ASKWEN-BOOK-001` | 问真网站用户提供的第一本书（书名待确认） | [问真学习课堂示例阅读页](https://pcbz.iwzwh.com/#/book/index?id=3_1&bookId=1&isBase=true) | 用户确认该网站内有多本已转成网页文字的书，采用目录/逐页阅读体验 | `candidate / acquisition_test_pending`；尚未确认正文加载方式、批量导出能力、站点条款和版权；不得假定可爬取 |

说明：上表是来源登记，不代表这些书已经全部下载或进入 Neo4j。当前掌握的多为章节链接和我们自己撰写的摘要，不是 PDF 文件。

### 2.2 六爻开源项目与技术参考

| Source ID | 项目 | 仓库 | 主要研究方向 | 状态 / 限制 |
|---|---|---|---|---|
| `GH-LIUYAO-JJ` | Johnson-Jia/liuyao-divination | https://github.com/Johnson-Jia/liuyao-divination | 六爻排盘、规则文档、案例测试、纳甲/六亲/世应结构 | `candidate`；逐文件检查许可证、代码和规则差异 |
| `GH-NAJIA` | bopo/najia | https://github.com/bopo/najia | 纳甲、六亲、六神、世应、卦宫、旬空基础库 | `candidate`；检查变卦六亲基准和测试口径 |
| `GH-YAOMANCY` | yaomancy/liuyao-engine | https://github.com/yaomancy/liuyao-engine | Python 引擎、四柱、纳甲、六亲、世应、结构化数据 | `candidate`；README 声明的许可证/能力仍需实际复核 |
| `GH-WOAICHJI` | woaichiji/liuyao | https://github.com/woaichiji/liuyao | 章节式 Markdown 六爻基础文字（如纳甲、六亲、动静变爻） | `candidate`；按选定文件登记，确认许可后再采集 |
| `GH-SHOUZHANG` | ShousenZHANG/chinese-fortune | https://github.com/ShousenZHANG/chinese-fortune | 六爻算法说明、纳甲脚本、术语说明 | `candidate`；区分说明文档与可复制代码，检查 License |
| `GH-LYTOOL` | 1eakkkk/liuyao-tool | https://github.com/1eakkkk/liuyao-tool | Vite/JavaScript 起卦工具与 UI 数据组织 | `candidate`；重点借鉴结构，复制代码/素材前复核 License |
| `GH-DIVINATION` | SmallTeddyGames/divination-liuyao | https://github.com/SmallTeddyGames/divination-liuyao | 在线六爻及 AI 解读产品结构 | `candidate`；不自动采纳其断语逻辑 |
| `GH-LUNAR-TS` | 6tail/lunar-typescript | https://github.com/6tail/lunar-typescript | 农历、干支、节气与前端历法实现 | `candidate`；时区和节气边界须单独测试 |
| `GH-LUNAR-JS` | 6tail/lunar-javascript | https://github.com/6tail/lunar-javascript | 另一个 JavaScript 历法实现，用于交叉比对 | `candidate`；与 TypeScript 版本属于同生态，不算完全独立证据 |

以上项目当前是参考候选清单，不代表已经 clone、下载或导入全部代码。

## 3. Source Catalog 必须记录的字段

每个来源及其可采集的具体条目至少登记：

| 字段 | 含义 |
|---|---|
| `source_id` | 稳定、唯一的来源 ID |
| `title` / `creator` | 书名/项目/网站名称及作者、维护者或机构 |
| `source_kind` | `classical_text`、`modern_book`、`web_text`、`github_project`、`github_doc`、`source_code`、`pdf` 等 |
| `canonical_url` | 书目/项目主页；避免只存临时分页 URL |
| `item_url` / `path` | 实际章节 URL 或仓库内选定路径 |
| `edition` / `version` / `commit_sha` | 版本、版次或固定源码提交 |
| `scope_selected` | 实际允许采集的章节、页码、目录或文件清单 |
| `license_status` / `rights_basis` | License、版权和复制依据；不明确时必须标记 |
| `allow_fetch` / `allow_local_copy` / `allow_cloud_processing` / `allow_redistribution` | 分别描述获取、本地保存、发给模型和再分发的权限，不得混为一个许可开关 |
| `provenance` | 站点、原始 URL、采集时间、页码/章节/commit/路径 |
| `content_hash` | 原始快照哈希，用于检测更新 |
| `checked_at` / `checked_by` | 最近核查日期与核查人/工具 |
| `status` | `discovered`、`candidate`、`rights_pending`、`approved`、`captured`、`import_ready`、`imported`、`excluded`、`superseded` |
| `trust_level` / `school_or_scope` | 课程/传统文本/现代整理/项目代码/AI 推断等来源分级及流派口径 |

来源主页登记与具体章节/文件登记应分开。一本书可以只有少数章节获准采集，不意味着全书已获准。

## 4. 采集和导入的双项目边界

### Project A — `symbi/liuyao-source-collector`（独立新仓库，远端创建待完成）

职责：
- 连接公开网页或公共 GitHub 来源，识别书目目录、章节、分页和文档结构。
- 对每种网站/平台实现独立 Adapter；例如普通 HTML 正文、SPA 阅读器、GitHub 文档/源码、获准下载的 PDF。
- 只在网站条款、版权、访问权限和允许的速率范围内采集；不绕过登录、付费墙、验证码、访问控制或反爬措施。
- 对分页采集提供页码/章节顺序检查、断点续采、重复检测、失败清单和原文哈希。
- 输出版本化的标准 Reference Package；不负责 Chunk、Embedding、LLM 抽取或 Neo4j 写入。
- 代码仓库只保存采集程序和合成测试夹具；第三方书籍全文、网站快照和下载 PDF 不提交到 Public code repo。

### Project B — `symbi/liuyao-learning-app`（现有知识库仓库）

职责：
- 维护 Source Catalog 与 allowlist，决定哪些来源、哪些章节/文件可进入知识库。
- 接收 Reference Package 或用户明确选择的本地资料。
- 验证 manifest、来源字段、文件哈希和许可元数据。
- 使用 Parser/Case Mapper、Chunker、Embedding 和 Neo4j 管线。
- 查询时保留课程、古籍、现代整理、GitHub 文档/源码、个人案例之间的来源差异。

两个项目通过文件包和稳定的 `source_id` 交接；不通过共享数据库或彼此导入代码耦合。采集器不能直接访问 AuraDB，知识库 Importer 不负责爬网页。

## 5. Reference Package 交接格式 v1（拟定）

采集器每次输出一个本地目录或 ZIP 包，结构如下：

```text
reference-package/
  package-manifest.json
  sources/
    CLASSIC-ZSBY/
      source.json
      documents/
        chapter-017-ri-chen.md
        chapter-022-an-dong.md
    GH-WOAICHJI/
      source.json
      documents/
        2-03-najia.md
```

`package-manifest.json` 至少包含 `schema_version`、`package_id`、`collector_name`、`collector_version`、`created_at` 和来源清单。

每个来源记录至少包含 `source_id`、标题/作者、`source_kind`、canonical URL、具体章节/文件 URL、版本/commit、采集时间、版权状态、云端处理/再分发权限、内容哈希，以及 documents 的路径、标题、章节/页码/代码符号 locator。

文档正文使用 UTF-8 Markdown 或保留原格式的文件；**不能只交付 Chunk，必须能回到原始章节/网页/文件。**

知识库接收前执行 Package Validator：路径安全、schema 版本、必需字段、哈希、重复 document ID、缺失文件、许可状态。未获准云端处理的内容不得发送给 Gemini。

## 6. 处理策略：不是所有资源都 Chunk

| 资料 | 进入知识库的方式 |
|---|---|
| 古籍/网页长文/课程 Markdown/TXT | 保留章节和段落层级后 Chunk；保留原始文档和精确 locator |
| GitHub README/docs | 按标题、段落和代码块分段 |
| GitHub 源码 | 先登记仓库、commit、License；按文件、类、函数/符号边界切分，不随机截断 |
| 课堂/个人案例 JSON | 使用确定性 Case Mapper 结构化入库，不把 JSON 简单当成长文本 |
| PDF | 当前不实施 PDF Adapter；只有选定实际文件并确认权利后再规划文字提取/页码定位；扫描件 OCR 另作决策 |
| 来源目录、版本、License、package manifest | 作为结构化元数据，不需要 Chunk |
| 图片、卦图、复杂表格 | 先保存来源与视觉定位；需要时单独设计图像/表格抽取，不默默丢弃 |

Chunk 适用于需要语义检索的文本，不是每种数据的强制格式。所有 Chunk 都必须连回 SourceDocument/Revision 和原始 locator。

## 7. 检索与证据使用原则

1. 搜索知识库优先检索课程整理笔记和已核实课堂案例；外部古籍和开源项目作为单独分区的佐证/对照。
2. 外部资料不自动提升为课程规则；若冲突，保留不同观点、原文与适用口径。
3. 引用必须保留书名/作者/版次/卷章/页码或网页 URL/仓库 commit/path。
4. 同一作品多个数字化版本不可混成一个 SourceDocument；版本变更产生新 revision。
5. 不要求每次分析都重新搜索网络。已经导入且未变化的资料可从 Neo4j 检索；需要最新版本、核实争议或寻找新资料时再按需联网检查，并记录核查时间。
6. 检索不到合适证据时明确报告缺失，不因某个关键词相似就假装来源支持。

## 8. 当前状态与下一步

- [x] 已建立课程外部参考文件，登记《增删卜易》《卜筮正宗》《易冒》《卜筮全书》等多本书的在线章节入口。
- [x] 已建立开源项目参考目录，覆盖六爻引擎、纳甲、前端六爻工具和历法库。
- [x] 已确认现有知识库项目与独立采集器应分为两个 repository。
- [x] 已决定当前 Phase 1 不开发 PDF Adapter；当前没有已确认的 PDF 输入文件或指定 PDF 版次。
- [ ] 创建 `symbi/liuyao-source-collector` 独立 GitHub repository（建议先 Private；当前连接不支持直接创建 repository，需 GitHub UI 或 `gh repo create`）。
- [ ] 在采集器中先验证用户提供的问真阅读器：目录、章节 URL、正文获取方式、分页顺序、站点条款和版权；未经确认不进行批量采集。
- [ ] 对现有古籍和 GitHub 候选进行来源核验，选择少量章节/文档作为首批批准条目。
- [ ] 固化 Reference Package v1 JSON Schema，并为知识库增加只读校验/导入入口。
- [ ] 首批采集包通过人工抽样检查后，再进入 Chunk/Embedding/Neo4j。

## 9. 相关资料

- [开源项目与古籍调查计划](reference-research-plan.md)
- [六爻开源项目、历法与二十八宿目录](references/github-project-catalog-and-28-mansions.md)
- [六爻基础外部参考](references/liuyao-basics-external-sources.md)
- [第十一课外部参考：日辰、暗动与日破](references/lesson-11-external-sources.md)
- [Phase 1 实施计划](phase1-implementation-plan.md)
- [Phase 1 实际运行架构](phase1-operating-model.md)