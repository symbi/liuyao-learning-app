# HTML 维护进度与交接记录

> 本文件只记录现有 HTML / 前端修复工作。跨窗口总览见 [workspace-handoff.md](workspace-handoff.md)。不要把 Neo4j / Phase 1 的里程碑状态写在这里。

## 当前状态

- Project: `symbi/liuyao-learning-app`
- Workstream: HTML maintenance
- Status: planned
- Current task: 等待用户在新 ChatGPT 窗口提供具体 HTML 问题 / 截图 / 复现步骤
- Target branch: none
- Active PR: none
- Last completed task: none
- Last updated: 2026-11-19

## 开始任务前

1. 读取 `docs/workspace-handoff.md` 与本文件。
2. 检查 GitHub 最新 `main`，确认当前 `index.html` 和相关脚本 / 样式的真实版本。
3. 检查 `git status --short`、当前分支和未提交改动；不得 reset、clean、stash 或覆盖用户文件。
4. 明确本次用户要求修复的问题、验收标准和涉及文件，再开始修改。

## 修改边界

- 当前运行页面以仓库里的最新实现为准；不要把旧的 V80 等版本描述当作当前代码版本。
- 默认采用最小必要改动，不顺手重写整个页面。
- 未经明确授权，不更改 Cloudflare Pages Functions、GitHub OAuth、GitHub JSON 保存协议、每日记录 schema 或 Neo4j / Python Importer。
- 不删除、覆盖或清空现有每日 Memo、课堂案例和历史记录。
- 测试必须使用临时 / fixture 数据，不能写入真实每日记录。
- 不在日志、截图、提交中暴露凭据、Token 或私人记录。

## 分支与审查

- 每项独立 HTML 修复使用自己的分支，建议：`fix/html-<short-topic>`。
- 从最新已批准的 `main` 创建分支。
- 完成后运行适用的检查，至少执行 `git diff --check`，并进行实际页面验证；未执行的检查不能声称通过。
- 更新本文件，提交分支并创建 Draft PR 到 `main`。
- 不直接提交实现代码到 `main`，不自动合并；等待 ChatGPT 审查和用户决定。
- 若 Phase 1 另一个分支同时变更同一文件或共享文档，先报告冲突，不自行覆盖或合并。

## 任务记录模板

每次修复追加一节：

- Date:
- Task:
- User acceptance criteria:
- Branch:
- Draft PR:
- Base main SHA:
- Commit SHA:
- Files changed:
- Implementation summary:
- Tests / exact commands:
- Manual browser checks:
- Before / after evidence:
- Known issues / unverified behavior:
- Security and data-preservation checks:
- Status:
- Next step:

## 最近任务

目前尚无 HTML 修复任务开始。新窗口收到用户具体要求后，在此记录任务范围与进展。
