# Source Collector 独立项目章程与 Muse 启动说明

> Target repository: `symbi/liuyao-source-collector`  
> Initial visibility: **Private**（首批网站适配与版权边界未核实前先保持私有；稳定后再由用户决定是否公开）  
> Status: 设计已确认，远端 repository 尚未创建。  
> Last updated: 2026-11-21
> 执行归属：建仓与实现由独立的 Source Collector 窗口负责（见第 8 节）。本文件保存在 Learning App 仓库仅作为交接契约与决策记录；Learning App 侧的 Agent 不执行第 8 节指令、不在本仓库实现采集器。

## 1. 项目使命

建立一个独立、可复用的外部资料采集工具，把经用户选择、允许获取的公开资料转换为带完整来源信息的 Reference Package，交给 `symbi/liuyao-learning-app` 导入知识库。

它是上游资料获取工具，不是六爻知识库本身。

### 做什么
- 从允许访问的公开网页读取文字内容，支持目录、章节、分页和 SPA 阅读器的适配器。
- 从公开 GitHub 仓库按 allowlist 获取指定 README、docs、规则文件、源码和测试文件，固定 commit SHA。
- 对允许下载的文件保留原文件和基础元数据；未来可增加 PDF 下载，但 PDF 解析/Chunk 不属于本项目职责。
- 记录 canonical URL、item URL、作者/组织、版本/commit、取得时间、内容哈希、页码/章节/路径定位、来源状态和版权/许可依据。
- 支持断点续采、缓存、速率限制、顺序完整性检查、重复检测、失败清单和 package 校验。
- 输出版本化 Reference Package（目录或 ZIP），供知识库导入。

### 明确不做
- 不做 Chunk、Embedding、向量检索、LLM 规则抽取或最终卦象分析。
- 不连接 Neo4j AuraDB，不写入 `liuyao-learning-app` 的数据库。
- 不把抓取到的第三方全文提交到这个代码 repository。
- 不绕过登录、付费墙、验证码、访问控制、反爬措施或网站明确禁止的自动化访问。
- 不默认爬取整个站点、整个 GitHub 仓库或整本书；只采集用户 allowlist 指定的范围。

## 2. 与现有项目的接口

| 项目 | 负责 | 不负责 |
|---|---|---|
| `symbi/liuyao-source-collector` | 来源发现、访问适配、合规采集、快照与 Reference Package 输出 | Chunk、Embedding、Neo4j、规则抽取 |
| `symbi/liuyao-learning-app` | Source Catalog、来源审核、Package 验证、Parser、Chunk、Embedding、Neo4j、Evidence Pack | 网页爬取、自动翻页、下载 |

Source Catalog 的权威目录目前放在 `symbi/liuyao-learning-app/docs/reference-source-catalog.md`。Collector 可通过用户指定的 source_id 和采集范围执行任务，但不能自行将候选来源升为 approved。

## 3. 初始技术结构（建议，不要求一次实现全部）

```text
liuyao-source-collector/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── config/
│   └── sources.example.yaml
├── schemas/
│   ├── package-manifest.schema.json
│   └── source-record.schema.json
├── src/liuyao_source_collector/
│   ├── cli.py
│   ├── models.py
│   ├── policy.py
│   ├── adapters/
│   │   ├── base.py
│   │   ├── static_html.py
│   │   ├── github_repo.py
│   │   └── askwen_reader.py
│   ├── discovery/
│   │   ├── sitemap.py
│   │   ├── links.py
│   │   └── pagination.py
│   ├── collection/
│   │   ├── fetch.py
│   │   ├── checkpoint.py
│   │   ├── normalize.py
│   │   └── package.py
│   └── validation/
│       ├── manifest.py
│       └── integrity.py
└── tests/
    ├── fixtures/
    └── test_*.py
```

建议 Python 3.12、Typer 或 argparse、Pydantic、httpx/标准 HTTP client、BeautifulSoup 或 lxml。依赖选择以最小化为原则，先检查许可证与维护状态。

`askwen_reader.py` 只是未来的站点专用 adapter 位置。必须先完成站点结构、正文来源、分页、条款与版权核验，不能先写一个绕过网站限制的爬虫。

## 4. CLI 目标（名称可调整）

```bash
collector doctor
collector sources inspect --source-id ASKWEN-BOOK-001
collector discover --source-id ASKWEN-BOOK-001 --dry-run
collector collect --source-id <approved-source-id> --scope <approved-scope>
collector package validate <package-dir>
collector package export <package-dir> --format zip
```

`discover` 与 `collect` 默认必须 dry-run 或明确指定 allowlist 范围；不得扫描用户整个浏览历史或任意本机目录。

## 5. Reference Package v1 交付契约

```text
reference-package/
  package-manifest.json
  sources/<source-id>/
    source.json
    documents/<stable-document-id>.md
```

字段名称与层级以 Learning App 的 [reference-package-v1.schema.json](reference-package-v1.schema.json) 为唯一准据，不另设第二套格式：

- 包级（`package-manifest.json`）：`schema_version`、`package_id`、`collector_name`、`collector_version`、`created_at`、`sources`。
- 来源级（`source.json`）：`source_id`、`title`、`creator`、`source_kind`、`canonical_url`、`edition`、`revision`、`collected_at`、`license_status`、`rights_basis`、`allow_fetch`、`allow_local_copy`、`allow_cloud_processing`、`allow_redistribution`、`provenance`、`documents`。
- 文档级（document record）：`document_id`、`order`（来源内顺序）、`chapter_title`、`item_url`、`content_path`、`content_hash`、`media_type`、`locator`。

注意：采集时间统一为 `collected_at`（不使用 `retrieved_at`）；文档标题统一为 `chapter_title`（文档记录没有单独的 `title` 字段，`title` 只属于来源级）；`item_url` 属于文档级，不属于来源级。本节与 schema 不一致时以 schema 和 [来源目录第 5 节](reference-source-catalog.md) 为准。

只交付原文/规范化文档和来源元数据，不交付 Chunk 或 Embedding。资料包不得包含凭据、cookies、session tokens 或用户个人 memo。

## 6. 数据安全、访问与合规

- 所有来源必须有 explicit allowlist；保存最小必要的访问范围。
- 对域名和重定向做基本校验，禁止 SSRF 到 localhost、私网 IP、云元数据地址和非预期协议。
- 对外请求设置合理 User-Agent、超时、并发和速率限制；支持尊重网站 robots/条款，不将 robots 规则作为绕过许可的理由。
- 不抓取登录后/会员/付费内容，不破解前端参数或访问控制；遇到验证码/防爬即停止并报告。
- 将 `allow_fetch`、`allow_local_copy`、`allow_cloud_processing`、`allow_redistribution` 分别记录，不能把网站可读等同于可复制或可上传给 Gemini。
- 未核实权限时只登记书目和链接，不下载、不批量采集、不发送给模型。
- 原始采集全文与输出包放用户指定的本地目录或获准的私有存储；不推送到代码仓库。
- `.env`、Cookies、登录状态、Token、API Key、本地缓存、下载资料包均排除在 Git 之外。

## 7. 里程碑

| 阶段 | 内容 | 完成标准 |
|---|---|---|
| S0 | 建 repository 与工程骨架 | Private repo、README/AGENTS/pyproject、测试、CI/格式检查；无第三方正文 |
| S1 | 公共网页可行性检查 | 用合成 HTML fixture 验证静态正文、目录链接、分页、重复和断点逻辑 |
| S2 | 问真阅读器调查 | 不做批量爬取；先确认目录、正文获取方式、分页/API、使用条款和版权。拿不到/不允许时停止并报告 |
| S3 | 获准来源的第一个站点 Adapter | 只实现已批准范围，导出 package，抽样检查无漏页/错序/乱码 |
| S4 | GitHub 来源 Adapter | 固定 commit SHA，按 allowlist 下载选定 docs/源码，保留 License 和路径 |
| S5 | 与 Knowledge Base 契约验收 | Package schema、hash、locator、rights 字段与知识库 validator 对接 |

## 8. 可直接交给 Muse 的执行指令

请在你可访问的 GitHub/终端环境中创建并初始化独立 repository `symbi/liuyao-source-collector`，初始设为 Private。先检查 `gh auth status` 和同名仓库是否已存在；若已存在，不要覆盖或重置。创建后 clone 到独立目录，不要把它放在 `liuyao-learning-app` 仓库内部。

先只完成 S0：创建 README.md、AGENTS.md、pyproject.toml、.gitignore、空模块目录、Reference Package v1 JSON Schema（先按本章程草案实现）、合成 fixture 和单元测试；不要提交任何抓取到的第三方书籍全文、PDF、Cookie、Token 或私有课程资料。不要实现问真网站批量爬取，不要调用登录态或绕过防护。完成后运行 lint/type/test，push 主分支并把 repository URL、commit SHA、可见性和测试结果交还 ChatGPT 审查。

在 S0 审核通过前，不开始 S1/S2 的实际网络采集。在调查问真网站前，先核验站点使用条款、版权/授权和技术访问方式；不允许自动采集时，只登记来源链接，停止爬取。

当前 M2-B PR #3 尚待用户 Mac 本机验收与合并；Source Collector 的 S0 可以独立准备，但不要擅自启动现有知识库的 M2-C JSON Adapter，也不要修改 HTML App。
