# 工作区总览与跨窗口同步

> 本文件是不同 ChatGPT 窗口、Claude Code、Codex、Muse 之间的总入口。GitHub main 是已确认项目状态的共同来源；尚未合并的 Draft PR 不自动成为 main 的共同状态。

- Repository: symbi/liuyao-learning-app
- Last updated: 2026-11-21
- Shared memory rule: 每个工作流维护自己的进度文件；重要状态变化合并到 main 后，其他窗口才把它视为共同确认的最新状态。
- Security: 不在本文件或其他文档中保存密码、Token、私密录音、私密 Memo 或本机敏感路径。

## 当前并行工作流

| 工作流 | 负责内容 | 当前状态 | 当前分支 / PR | 权威进度文件 |
|---|---|---|---|---|
| HTML 窗口 | 修复现有 HTML 页面及用户明确指定的前端问题 | 独立工作流；按具体任务启动 | 具体任务分支 / Draft PR | [html-maintenance-progress.md](html-maintenance-progress.md) |
| Phase 1 / Knowledge Base | AuraDB、Python Importer、课程/案例解析、Chunk、Embedding、检索和 Evidence Pack | M1、M2-A/M2-B 已合并（PR #3）；双仓库架构与来源目录已合并（PR #4，merge commit `65fb501`）；当前为 M2-C 规划更新（PR #5，docs-only Draft）；M2-C1/C2/C3 尚未实施 | [PR #5](https://github.com/symbi/liuyao-learning-app/pull/5)，phase1/m2c-planning（Draft） | [phase1-progress.md](phase1-progress.md)、[phase1-implementation-plan.md](phase1-implementation-plan.md) |
| Source Collector（独立项目） | 外部古籍网站/网页/GitHub 文档的合规采集与 Reference Package 输出；不做 Chunk/Embedding/Neo4j | 仓库 `symbi/liuyao-source-collector` 已创建且为 Private，由独立窗口维护；架构与启动章程已随 PR #4 合并进入 main | [symbi/liuyao-source-collector](https://github.com/symbi/liuyao-source-collector)（Private） | [reference-source-catalog.md](reference-source-catalog.md)、[source-collector-project-charter.md](source-collector-project-charter.md) |

## 工作流边界

### A. HTML 维护窗口

- 只处理用户明确提出的 HTML / UI 修复任务；开始前先检查最新 main、git status 和当前实现，不根据旧聊天截图推断当前代码。
- 使用独立分支，命名建议：fix/html-<short-topic>。
- 默认只修改实现该任务必需的前端文件。未经明确要求，不重构整页、不改 GitHub 保存 API、Cloudflare Pages Functions、数据结构或知识库架构。
- 修改前后保留现有每日记录和案例数据行为；不能用测试数据覆盖真实记录。
- 完成后提交 Draft PR，写明改动、测试和未验证事项；ChatGPT 审核，用户决定是否合并。
- 更新 docs/html-maintenance-progress.md，不要代替 Phase 1 窗口改写 docs/phase1-progress.md。

### B. Phase 1 / Knowledge Base 窗口

- 按 AGENTS.md、CLAUDE.md、docs/phase1-progress.md 和 Phase 1 实施计划执行。
- M0 已完成实际 AuraDB Free 验证；M1 已合并到 main。
- M2-A（来源模型）与 M2-B（Markdown/TXT）已通过复审并合并：PR #3 以 Merge Commit 合并，merge commit 为 `9505ce70e38b729bfb4d7dd36924a25229389194`。验收依据为执行 Agent 在与 PR head `e09ae71` 逐字一致的代码上复跑的 144 passed、38 adapter tests 及 Ruff/Mypy 全通过；用户已豁免手动 Mac 复跑并确认接受该验收依据（详见 phase1-progress.md 的合并记录）。
- PR #4（双仓库架构、Reference Catalog 与 Reference Package 契约）已合并（merge commit `65fb501`），main 已包含 Reference Source Catalog、Reference Package Schema 与双仓库架构。当前活跃的 Draft PR 是 PR #5（M2-C 规划更新，docs-only）。
- M2-C 已拆为 C1（案例 JSON Mapping）、C2（自动生成 MD 伴随文件）、C3（人工分析 MD 关系）；PR #4 合并这一前置条件已满足，但三项实现均尚未启动，须用户明确授权后才开始。不开发 PDF Adapter/OCR。
- Knowledge Base 只读取显式批准的本地资料或 Reference Package，不负责爬网站。
- 维护 docs/phase1-progress.md；不修改 HTML 页面或 Cloudflare Functions。

### C. Source Collector 独立窗口 / repository

- 目标 repository：symbi/liuyao-source-collector，已创建且为 Private，由独立窗口维护；启动章程和 Muse 指令在 source-collector-project-charter.md。
- 只负责合规采集、分页/章节完整性检查、版本/哈希和 Reference Package 输出；不 Chunk、不生成 Embedding、不连接 Neo4j。
- 工程步骤由独立窗口按其计划推进。没有经过站点条款/版权/访问权限核验前，不对问真阅读器进行批量采集；不得绕过登录、付费墙、验证码或反爬措施。
- 不把第三方全文、下载 PDF、Cookies、Token 或本机缓存提交到代码 repository。
- Source Catalog 的权威登记仍在 liuyao-learning-app/docs/reference-source-catalog.md；Collector 只处理获准的 source_id 和 scope。

## 并行协作规则

1. **仓库/分支隔离**：HTML 使用 fix/html-...；Knowledge Base 使用 phase1/mX-...；Source Collector 在独立 repository 开发，不能把爬虫或采集器代码放进 liuyao-learning-app。
2. **不直接提交实现代码到 main**：每个工作流都通过独立 Draft PR；除非用户明确授权，任何模型都不得合并。
3. **避免同时改同一文件**：HTML 窗口不改 Phase 1 Python / 架构文件；Knowledge Base 不改 index.html 或前端功能；Collector 不修改现有 HTML App。
4. **以 main 为同步点**：另一个窗口看不到尚未合并的 Draft PR 内容。PR 未合并时，跨窗口只能通过用户提供 PR URL / 摘要进行审查，不要假设其内容已经进入 main。
5. **开始新任务先同步**：每个窗口开始工作前先读本文件，再读自己工作流的进度文件；随后检查本地分支、工作区和 GitHub 最新 main。不要覆盖另一个窗口或用户的未提交改动。
6. **完成后更新自己的进度文件**：写明状态、分支、PR、提交、测试、阻塞点和下一步。只有已合并到 main 的内容才是所有窗口共同确认的项目状态。
7. **规划 PR 状态**：PR #4 的来源目录/Collector 规划已合并进入 main；当前规划类 Draft 是 PR #5（M2-C 规划）。未合并的 Draft PR 内容仍不自动成为 main 的共同状态。

## 新 HTML 窗口启动提示

把下面文字发给新窗口，然后补充具体 HTML 问题或截图：

> 我们在并行维护 symbi/liuyao-learning-app。请先读取 docs/workspace-handoff.md、docs/html-maintenance-progress.md、AGENTS.md 和相关 HTML 文档，再检查 GitHub 最新 main 与实际 index.html。这个窗口只负责我接下来明确提出的 HTML 修复；不要启动 Neo4j / Phase 1 工作，不要修改 Phase 1 进度。先复述当前页面结构和你准备修改的范围，再按独立 fix/html-... 分支、Draft PR 的流程执行。保留现有每日记录、案例和 GitHub 保存逻辑，不得把测试数据写入真实记录。完成后更新 docs/html-maintenance-progress.md，等待 ChatGPT 审查和用户决定是否合并。

## 新 Source Collector 窗口 / Muse 启动提示

> symbi/liuyao-source-collector 已创建且为 Private，请在该仓库内按独立窗口的既有计划继续；先阅读 liuyao-learning-app/docs/source-collector-project-charter.md 与 docs/reference-source-catalog.md（已随 PR #4 合并进入 main）。不得把采集全文提交到公共仓库，不要先批量爬取问真站点；先核验使用条款、版权、目录/分页/正文获取方式。Collector 不做 Chunk/Embedding/Neo4j，只输出标准 Reference Package。完成后给 ChatGPT commit SHA 和测试结果。

## 新 Claude Code / Knowledge Base 窗口继续执行提示

> 请先读取 AGENTS.md、CLAUDE.md、docs/workspace-handoff.md、docs/phase1-progress.md 和 Phase 1 实施计划。M0 已完成，M1 已合并，M2-A/M2-B 已合并（PR #3），双仓库架构与来源目录已合并（PR #4，merge commit 65fb501）。当前是 M2-C 规划阶段（PR #5，docs-only）：M2-C 已拆为 C1/C2/C3，前置条件已满足，但不要开始任何一项实现，须等用户明确授权；PDF Adapter/OCR 暂缓。课堂案例是老师讲解过的教学案例，不是个人练习，JSON 与对应 MD 是同一案例的两种表示（详见实施计划第 4、7 节）。知识库只负责批准来源的解析/Chunk/Embedding/Neo4j，不承担外部网页采集；Source Collector 已创建（Private）且是独立窗口的工作，不属于本仓库实现任务。

## 更新日志

- 2026-11-19：建立 HTML 与知识库双工作流协作机制。
- 2026-11-21：补充 Source Collector 独立 repository 规划；明确两个项目通过 Reference Package 交接。PR #4 尚未合并。
- 2026-11-21：PR #3 以 Merge Commit 合并（`9505ce7`），M2-A/M2-B 完成；PR #4 同步到新 main 并成为当前唯一活跃 Draft PR；M2-C 等待 PR #4 合并与用户授权后再启动。
- 2026-11-22：PR #4 已合并（merge commit `65fb501`），main 包含 Reference Source Catalog、Reference Package Schema 与双仓库架构；`symbi/liuyao-source-collector` 已创建且为 Private（独立窗口维护）。
- 2026-11-22：开启 PR #5（docs-only）更新 M2-C 规划：按真实文件拆分 C1/C2/C3，确立课堂案例身份原则与 ClassCase/CastRecord 独立身份模型；M2-C 实现仍待用户明确授权。
