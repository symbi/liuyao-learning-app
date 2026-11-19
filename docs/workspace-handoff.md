# 工作区总览与跨窗口同步

> 本文件是不同 ChatGPT 窗口、Claude Code、Codex 之间的总入口。GitHub `main` 是已确认项目状态的共同来源；聊天窗口之间不会自动共享实时对话内容。

- Repository: `symbi/liuyao-learning-app`
- Last updated: 2026-11-19
- Shared memory rule: 每个工作流维护自己的进度文件；重要状态变化合并到 `main` 后，其他窗口才把它视为共同确认的最新状态。
- Security: 不在本文件或其他文档中保存任何密码、Token、私密录音、私密 Memo 或本机敏感路径。

## 当前并行工作流

| 工作流 | 负责内容 | 当前状态 | 当前分支 / PR | 权威进度文件 |
|---|---|---|---|---|
| HTML 窗口 | 修复现有 HTML 页面及用户明确指定的前端问题 | planned / 尚未开始；等待新窗口接收具体问题 | 无 | [html-maintenance-progress.md](html-maintenance-progress.md) |
| Phase 1 / Claude Code | AuraDB、Python Importer、知识库和 Evidence Pack | M0 等待用户创建 AuraDB Free；Claude 尚未修改代码或创建分支 | 无 | [phase1-progress.md](phase1-progress.md) |

## 工作流边界

### A. HTML 维护窗口

- 只处理用户明确提出的 HTML / UI 修复任务；开始前先检查最新 `main`、`git status` 和当前实现，不根据旧聊天截图推断当前代码。
- 使用独立分支，命名建议：`fix/html-<short-topic>`。
- 默认只修改实现该任务必需的前端文件。未经明确要求，不重构整页、不改 GitHub 保存 API、Cloudflare Pages Functions、数据结构或知识库架构。
- 修改前后保留现有每日记录和案例数据行为；不能用测试数据覆盖真实记录。
- 完成后提交 Draft PR，写明改动、测试和未验证事项；ChatGPT 审核，用户决定是否合并。
- 更新 `docs/html-maintenance-progress.md`，不要代替 Phase 1 窗口改写 `docs/phase1-progress.md`。

### B. Phase 1 / Claude Code 窗口

- 按 `AGENTS.md`、`CLAUDE.md` 和 `docs/phase1-progress.md` 执行。
- 当前用户选择先完成 Aura Console onboarding、创建 AuraDB Free，再运行 M0 smoke test；在用户通知之前不启动 M1、不创建实现分支、不修改代码。
- M0 验证 AuraDB 实际 Tier / Neo4j 版本、Python 连接、基础读写、Vector Index 创建/查询/删除及维度限制。
- 不因 Vector Index 失败而自行升级付费层或更换架构；先提交实测结果，由 ChatGPT 与用户决定。
- Claude 窗口维护 `docs/phase1-progress.md`，不修改 HTML，除非用户另外明确授权。

## 并行协作规则

1. **分支隔离**：两个工作流不能共用实现分支。HTML 分支使用 `fix/html-...`；知识库里程碑分支使用 `phase1/mX-...`。
2. **不直接提交实现代码到 main**：每个工作流都通过独立 Draft PR；除非用户明确授权，任何模型都不得合并。
3. **避免同时改同一文件**：HTML 窗口不改 Phase 1 Python / 架构文件；Claude Phase 1 不改 `index.html` 或前端功能。
4. **以 main 为同步点**：另一个窗口看不到尚未合并的 Draft PR 内容。PR 未合并时，跨窗口只能通过用户提供 PR URL / 摘要进行审查，不要假设其内容已经进入 main。
5. **开始新任务先同步**：每个窗口开始工作前先读本文件，再读自己工作流的进度文件；随后检查本地分支、工作区和 GitHub 最新 main。不要覆盖另一个窗口或用户的未提交改动。
6. **完成后更新自己的进度文件**：写明状态、分支、PR、提交、测试、阻塞点和下一步。只有已合并到 main 的内容才是所有窗口共同确认的项目状态。

## 新 HTML 窗口启动提示

把下面文字发给新窗口，然后补充具体 HTML 问题或截图：

> 我们在并行维护 `symbi/liuyao-learning-app`。请先读取 `docs/workspace-handoff.md`、`docs/html-maintenance-progress.md`、`AGENTS.md` 和相关 HTML 文档，再检查 GitHub 最新 main 与实际 `index.html`。这个窗口只负责我接下来明确提出的 HTML 修复；不要启动 Neo4j / Phase 1 工作，不要修改 Claude 的 Phase 1 进度。先复述当前页面结构和你准备修改的范围，再按独立 `fix/html-...` 分支、Draft PR 的流程执行。保留现有每日记录、案例和 GitHub 保存逻辑，不得把测试数据写入真实记录。完成后更新 `docs/html-maintenance-progress.md`，等待 ChatGPT 审查和用户决定是否合并。

## 新 Claude Code 窗口 / 继续执行提示

> 请先读取 `AGENTS.md`、`CLAUDE.md`、`docs/workspace-handoff.md`、`docs/phase1-progress.md` 和 Phase 1 实施计划。当前状态仍是 M0 等待用户在 Aura Console 创建 AuraDB Free；在收到用户“实例已创建”的明确通知前，不创建分支、不改代码、不启动 M1。收到通知后只执行 M0 smoke test，记录实际 Tier、Neo4j 版本、连接、基础读写和 Vector Index 能力；若 Vector Index 不可用，暂停并报告，不自行付费升级或改变架构。更新 Phase 1 进度文件后等待 ChatGPT 审核。

## 更新日志

- 2026-11-19：建立双工作流协作机制。HTML 修复与 Claude Code Phase 1 分开维护，分别使用独立进度文件、分支和 Draft PR。
