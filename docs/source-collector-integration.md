# Source Collector ↔ Learning App 集成协调记录

> 本文件记录 `symbi/liuyao-source-collector`（上游采集）与 `symbi/liuyao-learning-app`（下游知识库）两个独立仓库之间的跨项目事实、交接契约与待协调事项。
> 两边只通过标准文件包（Reference Package）和共同 Schema 对接：不共享代码，不互相直接操作对方的仓库或数据库。
> 本文件只记录协调状态，不构成对任何来源的批准（approved / import_ready），也不启动 M6 导入。

- 记录日期：2026-11-23
- 记录方：Learning App 侧窗口
- 本文件所在分支：`docs/source-collector-integration`（基于 Learning App 最新 main，见下）

## 1. 双方仓库与职责

| 项目 | 仓库 | 可见性 | 职责 |
|---|---|---|---|
| Source Collector | `symbi/liuyao-source-collector` | Private | 合法获取与标准化资料：书籍发现、目录解析（含层级）、正文采集、自动校验、Reference Package 生成 |
| Learning App | `symbi/liuyao-learning-app` | Public | 接收获准的 Reference Package，负责解析（Parser）、Chunk、Embedding、Neo4j 知识图谱与 Evidence Pack |

边界：

- Learning App 不实现网页爬虫或网站采集代码；Collector 不实现 Chunk、Embedding、Neo4j 或知识检索。
- Collector 负责其 Native Book Package 的生成与校验；向 Learning App 交付时，必须经 Exporter 转换为 Reference Package v1 格式（见第 3 节）。

## 2. 基线状态（2026-11-23 核实）

### Learning App（下游）

- 仓库：`symbi/liuyao-learning-app`
- 最新 main：`51a0476da6b8986e44fbe0d6fa0a5779cf5dbad2`（Merge PR #7，M2-C1）
- 活跃 PR：[PR #8](https://github.com/symbi/liuyao-learning-app/pull/8)（Draft，M2-C2，分支 `phase1/m2c2-daily-markdown-adapter`，head `04e76cf982d7d77a6c174b76dfd6042d10cb332c`，2026-11-23 更新核实；初版记录时为 `4f2b03622fbf2168f406be00f87fb8aef56fb083`，属历史快照）——本协调工作不修改该分支及其文件，不干扰 M2-C2 复审。
- 里程碑：M2-A/M2-B 已合并；M2-C1 已合并（PR #7）；M2-C2 在 PR #8 待复审；M2-C3 未启动；M3/M4/M5/M7/M8 未启动。
- 注意：main 上的 `docs/phase1-progress.md` 尚未反映 PR #7 合并与 PR #8 的状态（仍记为 2026-11-22 的状态），最新进度在 PR #8 分支上；以 GitHub PR 状态为准。

### Source Collector（上游）

- 仓库：`symbi/liuyao-source-collector`（Private）
- 最新 main：`4ff9c1834adad5a5c920315c1cf28ccf67815f14`（"Require filtered extraction metadata when resuming chapters"，2026-11-23）
- 多书采集 Workflow 分支：`feature/wenzhen-multibook-workflow`（本地提交 `c94a91e` 基线镜像、`14bf521` 工作流实现、`6c3278e` 测试）。
  - 状态说明：该分支截至本记录时尚未推送到远端（推送曾因 GitHub 写入批准超时未完成），远端 PR 尚不存在。此条以 Collector 侧窗口的最新确认为准，如有变化应更新本文件。
- 第一本书的成品包目前只存在于用户本地（Mac），不在 Collector 远端仓库中；不得在任何一侧重造或覆盖它。

## 3. 交接契约：Reference Package v1

- 权威 Schema：Learning App main 上的 `docs/reference-package-v1.schema.json`，契约版本 `schema_version = "1.0"`（JSON Schema draft 2020-12）；字段说明见 `docs/reference-source-catalog.md` 第 5 节。
- 包结构：`package-manifest.json` → 每来源一份 `source.json`（含 `source_id`、`license_status`、四项独立权限 `allow_fetch` / `allow_local_copy` / `allow_cloud_processing` / `allow_redistribution`、`rights_basis`、`provenance`）→ 来源内扁平 `documents[]`（`document_id`、`order`、`chapter_title`、`item_url`、`content_path`、`content_hash`、`media_type`、`locator`）。
- **Collector Native Book Package 与 Reference Package v1 不是同一种格式**（Native 包为 `book.json` / `catalog.json` / `acquisition.json` / `chapters/<chapter>/chapter.json + content.md` 等）。Collector 必须提供 Exporter，把 Native 包转换为符合 v1 Schema 的 Reference Package 后再交付；交付标准是输出能通过 v1 Schema 校验。
- **Learning App 当前尚无 Reference Package Importer/Validator 代码**（只有契约，没有导入实现；见 Source Catalog 第 8 节）。将来新建 Importer 时，直接以 Exporter 输出的 v1 包为输入，不适配 Native Package 格式。

## 4. Section / Chapter / NEXT 层级表达（待双方约定）

- v1 的 `documents[]` 是扁平列表；document 记录为 `additionalProperties: false`，**不得**在 document 层擅自新增 `section_id` / `parent` 等字段，否则无法通过 v1 校验。
- v1 现有能力：`order`（从 1 开始）保留全书阅读顺序，章节间 NEXT 关系可由导入方按 `order` 相邻关系推导；`chapter_title` 保留章节标题。
- 嵌套目录层级（问真目录存在 Section 与嵌套子篇）可通过 `locator` 承载：`locator` 是 v1 中唯一开放对象（`additionalProperties: true`）。拟议约定字段（待 Collector 侧确认后生效）：

  ```json
  "locator": {
    "section_id": "稳定 Section ID",
    "section_title": "章节（Section）标题",
    "section_order": 1,
    "depth": 1,
    "parent_section_id": "父 Section ID，顶层为 null"
  }
  ```

- 上述 locator 约定不改变 v1 Schema 本身，不破坏 v1 兼容性；但层级完整性（如父子对应、Section 顺序）无法由 v1 Schema 校验，只能由将来的 Importer 按约定校验。
- 后续可共同讨论 v1.1：在 source 层增加可选 `sections[]` 结构、document 增加可选 `section_id`，以可校验方式表达层级，并保持向后兼容（v1.0 包仍合法）。**任何一方不得单方面修改 v1 Schema 或版本号**；v1.1 提案须双方确认 Collector 的目录模型可一一映射后再定稿。

## 5. 来源登记与权限状态

- 问真《基础知识》对应 Collector 侧 `source_book_id = 3_1`（问真入口 `https://pcbz.iwzwh.com/#/book/index?id=3_1&bookId=1&isBase=true`）。
- Learning App Source Catalog 中现有登记 `ASKWEN-BOOK-001`（`docs/reference-source-catalog.md` 第 2 节）记为“问真网站用户提供的第一本书（书名待确认）”，状态 `candidate / acquisition_test_pending`。待协调：与 `3_1` / 《基础知识》核对并补全书名与 ID 映射（Catalog 的 `source_id` 与 Collector 的 `source_book_id` 的对应关系需在本文件中登记，见待协调事项）。
- **采集成功不等于 approved / import_ready。** 状态提升按 Source Catalog 的四阶段流程（登记 Registration → 采集 Acquisition → 导入 Ingestion → 检索 Retrieval）单独决定；发现新书或采集完成不得擅自提升状态。
- Collector 对 `3_1` 的授权确认（用户已确认，允许下载、本地存储与私有云存储）**只适用于该实际授权范围，不自动涵盖问真网站的其他书籍**；其他书籍在权利范围明确前只做元数据/目录层面的处理，全文采集须另行确认。
- Source Catalog 的 `source_id` 与权限状态以 Learning App 的正式登记和双方约定为准。

## 6. 存储与交接红线

- 第三方书籍全文只保存在用户指定、访问受控的本地或私有存储（含 Private 的 Collector 仓库）中，**不得提交到 Public 的 Learning App 仓库**。
- 将来的交接方式：Importer 从本地或受控私有路径读取 Reference Package；Public 仓库只保留契约（Schema）、来源登记、协调记录与导入代码，不复制全文。
- 原始内容必须随包交付并保留；Chunk 不能替代原始文档；每个 Chunk 必须能回溯到原始文档与精确出处（沿用 v1 契约既有规定）。

## 7. 里程碑关系

- M6（外部 Reference Package 导入）按 2026-11-23 第一轮路线决定**仍然延后、未取消**：先用现有知识（课程笔记、课堂案例、每日记录）完成 M2-C、M3、M4、M5、M7、M8 的端到端验收，再引入外部参考资料。
- 本次工作只做接口协商与契约准备：不提前启动 M6，不实现 Importer，不做 Neo4j 导入。

## 8. 待协调事项

| # | 事项 | 负责侧 | 状态 |
|---|---|---|---|
| 1 | Collector 分支 `feature/wenzhen-multibook-workflow` 推送到远端并开启 PR；完成后把 PR URL 与 head SHA 回填本文件 | Collector | 待完成（截至 2026-11-23 远端无此分支/PR） |
| 2 | Exporter：Native Book Package → Reference Package v1，输出须通过 `docs/reference-package-v1.schema.json`（v1.0）校验 | Collector | 未启动 |
| 3 | `locator` 层级约定字段（第 4 节）确认：字段名、Section ID 生成规则、顶层 `parent_section_id` 取值 | 双方 | 待确认 |
| 4 | v1.1 `sections[]` 提案：是否立项、何时定稿；定稿前不改 v1 Schema | 双方 | 待讨论 |
| 5 | `ASKWEN-BOOK-001` 与 `source_book_id=3_1` / 《基础知识》的登记核对与书名补全；`source_id` 映射规则 | Learning App（登记）+ Collector（提供书目信息） | 待核对 |
| 6 | `ASKWEN-BOOK-001` 的 Catalog 状态是否、何时从 `candidate / acquisition_test_pending` 提升 | 用户决定 | 未决定（默认不提升） |
| 7 | 第一本书成品包从用户 Mac 转移进 Collector Private 仓库，成为回归基准包 | 用户 / Collector | 待转移 |
| 8 | Reference Package Importer 的实现时机（M6）与读取路径约定（本地/受控私有路径） | Learning App | 延后（M6） |
| 9 | main 上 `docs/phase1-progress.md` 与 PR #8 合并后的状态同步（含本协调记录的引用） | Learning App | 待 PR #8 合并时一并处理 |

## 9. 接口变更记录

| 日期 | 变更 | 版本影响 |
|---|---|---|
| 2026-11-23 | 建立本协调记录；确认 v1.0 为当前唯一交接契约；提出 `locator` 层级约定（拟议，未生效）与 v1.1 讨论意向 | 无（不改 Schema） |
| 2026-11-23 | 按 PR #9 审查意见更新 PR #8 基线 head 至 `04e76cf982d7d77a6c174b76dfd6042d10cb332c`（初版所记 `4f2b036…` 为记录时快照，已在正文注明） | 无（仅状态同步） |
