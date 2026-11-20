# HTML 维护进度与交接记录

> 本文件只记录现有 HTML / 前端修复工作。跨窗口总览见 [workspace-handoff.md](workspace-handoff.md)。不要把 Neo4j / Phase 1 的里程碑状态写在这里。

## 当前状态

- Project: `symbi/liuyao-learning-app`
- Workstream: HTML maintenance
- Status: In review (Draft PR open)
- Current task: 三合发动支点优先级与旬空自动识别
- Target branch: `fix/trine-anchor-auto-xunkong`
- Active PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Last completed task: HTML v81 source repair and focused logic checks
- Last updated: 2026-11-20

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

## 2026-11-20 — 三合发动支点优先级与旬空自动识别

- Date: 2026-11-20
- Task: 修复日月三合的首选爻位，并依据完整日柱自动计算旬空。
- User acceptance criteria:
  - 当同一条动爻的本卦地支与变卦地支组成三合中的两支时，必须优先选这条动爻；日支/月支补第三支。示例：卯木发动、变未土、月支亥，首选亥卯未。
  - 不得为了形成三角形而改选另一条动爻；已有同爻本支→变支优先组合时，抑制同一三合局的替代组合。
  - 根据完整日柱自动算出旬空；拖入纳甲地支后即时显示旬空。
  - 休囚灰底保留，旬空另加点状圆环；本卦与变卦地支都适用。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1 Fix date-trine priority and calculate xunkong automatically](https://github.com/symbi/liuyao-learning-app/pull/1)
- Base main SHA: `d34783bf05aa1db5af92e76f30e890e33133c1f0`
- HTML implementation commit SHA: `285b1b8ccda43aa4eb396ae6a1009d6c3af08e66`
- Progress log commit SHA: `06b98e18a8dd5193ce4e14ea1b3d1535ba1d8a79`
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 新增 Mode C：同一条动爻的本卦地支 + 变卦地支 + 日/月支组成三合；候选排序为 C > A > B。
  - 若同一三合局已有 Mode C，则不再绘制该局的 A/B 替代组合，并抑制该动爻对应的同局“另找第三爻”本卦内三角形。
  - 新增完整日柱→六十甲子旬→旬空两支的计算；旬空日历槽改为自动显示、只读。
  - 旬空状态由自动计算值驱动，同时作用于本卦与变卦纳甲地支；虚线外圈改为点状外圈，保留休囚底色和月破叠加显示。
  - 保存快照中的旬空字段写入自动计算结果；打开历史记录时按该记录日期重新计算。
- Tests / exact checks:
  - 远程读取 PR 分支 HTML 后，整个内嵌 JavaScript 在 V8 中完成语法编译（未执行依赖浏览器 DOM 的页面脚本）。
  - 旬空 fixtures：甲子→戌亥、乙亥→申酉、戊戌→辰巳、甲寅→子丑。
  - 三合 fixture：卯木明动、变未土、月支亥，同时存在另一条动爻未土时，候选仍只优先返回 Mode C，锚点是同一条卯木动爻。
  - 源码替换执行唯一匹配检查；更新后确认旧的旬空 dashed 边框规则已不存在。
  - Cloudflare Pages PR Preview 已成功部署；随后实际点击「连接 GitHub」时，预览域名 `/api/auth/login` 返回 Cloudflare Error 1101（Worker threw exception）。`functions/api/[[path]].js` 在 main 与修复分支 blob SHA 相同；部署文档只记录 Production 的 KV/变量。高度怀疑 Preview 环境缺少 `SESSIONS` KV binding，尚未读取 Cloudflare Runtime Logs 验证。
- Manual browser checks: Cloudflare Preview 构建成功；交互式截图复现/人工目测仍待用户打开预览确认
- Before / after evidence: PR diff available at [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Known issues / unverified behavior:
  - 预览部署地址：`https://fix-trine-anchor-auto-xunkon.liuyao-learning-app.pages.dev`（branch preview）。页面可打开，但 `/api/auth/login` 发生 Error 1101；高度怀疑 Preview 未配置 `SESSIONS` KV binding / OAuth 环境变量。登录 Function 代码未在本 PR 中修改，main 与分支文件 SHA 相同。待 Cloudflare Preview 环境配置完成后再测 OAuth。尚未在可交互浏览器中用完整截图数据逐项目测。课程资料对跨卦体/动静成局的全部细则仍有待核实；本次只落实用户明确指定的“同一动爻本支→变支优先”。
- Security and data-preservation checks:
  - 仅更改 `index.html`；未改 GitHub OAuth、Cloudflare Functions、每日记录 schema、记录存储协议或历史数据文件。
  - 未写入任何真实每日记录。
- Status: Draft PR opened; awaiting visual/browser review.
- Next step: 用户打开 Branch Preview，按这张卦例核对卯→未 + 月亥的三角光轨，以及旬空申的灰底+点状外圈；反馈视觉位置/大小后再微调。

