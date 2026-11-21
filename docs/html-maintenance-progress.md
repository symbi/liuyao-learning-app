# HTML 维护进度与交接记录

> 本文件只记录现有 HTML / 前端修复工作。跨窗口总览见 [workspace-handoff.md](workspace-handoff.md)。不要把 Neo4j / Phase 1 的里程碑状态写在这里。

## 当前状态

- Project: `symbi/liuyao-learning-app`
- Workstream: HTML maintenance
- Status: In review (Draft PR open)
- Current task: 课堂案例干支选择器改为完整选项、天干地支独立选择
- Target branch: `fix/trine-anchor-auto-xunkong`
- Active PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Last completed task: v85 修正课堂案例干支选择器交互
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



## 2026-11-20 — 课堂案例手动指定年月日干支

- Date: 2026-11-20
- Task: 课堂案例不能把录入/归档日期误当成老师给出的起卦日期；允许手动指定完整年月日干支。
- User acceptance criteria:
  - “记录日期”只用于保存和定位 GitHub 日记录文件；不能自动冒充老师案例的起卦日期。
  - 案例可以手动填写年柱、月柱、日柱的天干与地支，共六个字符。
  - 年柱可能未知，允许天干和地支都留空；月柱、日柱需填写完整。
  - 干支组合必须是合法六十甲子组合。
  - 手动柱必须参与月令、日辰、旬空、日干六神、暗动/日冲、月破和三合识别等实际计算。
  - 保存、重新打开、JSON 导出和 AI 复制都必须保留手动干支及其来源。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Base main SHA: `d34783bf05aa1db5af92e76f30e890e33133c1f0`
- Implementation commits:
  - `fe1bf9c1d765760ced47425abce17d538223d958` — branch-status marker and 六合 / 合中带克 analysis
  - `badc513fd3a4e58a7be6378c07f467b0e7aec3d1` — manual Gan-Zhi editor and schema v14 / snapshot v3
  - `f5c8aa9c324c8690d28c40e933b9555dc3bdaed9` — manual editor state refresh fix
  - `5c8c265e87ce46bfe76359d685edbfed71cfe530` — keep archive-date almanac separate from manual case pillars
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 进入新的课堂案例时，默认打开“手动指定案例年月日干支”；用户可以关闭，恢复按记录日期自动计算。
  - 年、月、日三组各有独立天干/地支选择器；选择器会互相约束，只允许合法的六十甲子组合。
  - 年柱允许两项都留空；月柱、日柱要求完整，保存前校验。
  - 手动干支成为实际计算上下文：月支驱动旺相休囚/月破，日支驱动日冲/暗动，完整日柱驱动旬空，日干驱动六神起神；三合识别也使用手动月、日支。
  - 保存记录时分开保存 `date`（归档日期）、`pillars`（实际使用的年月日柱）、`pillarSource` 和 `pillarOverride`。打开旧记录时继续用其既有日期自动干支；打开新手动案例时恢复手动干支。
  - 手动案例不把归档日期对应的建除、二十八宿保存成案例资料；AI 复制内容会注明“老师案例手动指定”及“年柱未知”。
  - 升级 record schema 到 14、analysisSnapshot 到 3；旧版快照在导出/AI 复制时会重建。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 合法干支检查：甲子、己亥、戊戌、丙午通过；甲丑、乙子、癸午拒绝。
  - 源码检查确认有六个独立的干支选择器、保存前校验、重新打开恢复逻辑、手动来源持久化及快照来源字段。
  - 尚未完成真实浏览器的完整交互验收；Cloudflare Pages 对提交 `f5c8aa9` 返回过一次 Deploy successful，但最后两次提交仍需确认最新预览部署结果。
- Manual browser checks: 待在 v84 Preview 中验证选择器、合法组合约束、保存/打开和旬空显示。
- Security and data-preservation checks:
  - 只修改 HTML 和维护日志；不改 GitHub OAuth、Cloudflare Functions、API 保存路由或生产配置。
  - 未写入或更改任何真实每日卦例；未合并 PR；未修改 `main` 或 Production。
- Status: Draft PR open; code committed, final Preview verification pending.
- Next step: 在 Preview 中新建课堂案例，检查年月日选择器和保存/打开后的计算结果。


## 2026-11-21 — 课堂案例干支选择器改为独立选择

- Date: 2026-11-21
- Task: 保留日常日期自动排干支；课堂案例手动输入时，天干与地支必须分别提供完整选择范围，不互相过滤或擅自清空。
- User acceptance criteria:
  - 日常每日记录仍以日本当天日期自动计算年、月、日干支。
  - 只有案例启用手动干支时，手动值才替代自动计算值；案例归档日期仍只用于定位和保存记录。
  - 年干下拉框始终提供完整十个天干；年支始终提供完整十二地支。月柱、日柱同样如此。
  - 选择一个天干不得缩小地支列表；选择一个地支不得缩小天干列表；系统不得因另一侧选择而清空用户当前选择。
  - 仍需校验六十甲子合法性；月柱、日柱必填，年柱可未知；无效组合必须提示并阻止保存，避免把错误干支用于正式排盘。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Implementation commits: `d19d265b9b346545ec53ac48ea1080f5dabab102`（独立选择逻辑）、`47b575236bb21a616bce727753f98e69533e2124`（版本标记 v85）
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 每日模式仍由 `updateCalendarForJapanToday()` 自动计算当前日本日期的年月日干支；未更改日期算法和自动刷新逻辑。
  - 案例模式仍由现有 `pillarOverride.enabled` 控制是否覆盖自动值；案例关闭手动输入时恢复日期自动值。
  - 重写 `syncPillarPairControls()`：每个干下拉框始终显示十个天干，每个支下拉框始终显示十二地支；两者独立，不再动态过滤、不再自动清除对侧选择。
  - 保留六十甲子校验和保存前校验；发现不合法组合时明确提示用户核对老师原文。
  - 调整手动输入说明，明确每日自动计算与案例手动覆盖的关系。
- Tests / exact checks:
  - 更新后的完整 HTML 内嵌 JavaScript 已通过 V8 语法编译（154 KB 脚本，无语法错误）。
  - 静态检查通过：年、月、日三组均通过完整 `GANZHI_STEMS` / `GANZHI_BRANCHES` 数组填充；控制函数不含 `.filter()`、配对联动清空或自动删除值的逻辑；保存前六十甲子合法性校验仍在。
  - 待完成：Cloudflare Pages 最新 Preview 部署与实际 UI 人工验收。
- Manual browser checks: 待用户在 Preview 中确认：日常页面仍自动显示当天年月日干支；标记课堂案例后，年/月/日每一柱的天干下拉框可看到完整十项，地支下拉框可看到完整十二项；选择一侧不会影响另一侧；非法组合有提示；合法组合可保存并重开。
- Security and data-preservation checks:
  - 只更改 `index.html` 和本维护日志；未改 GitHub OAuth、Cloudflare Functions、API 保存路由或 Production 配置。
  - 未写入或改动任何真实每日记录；未合并 PR，未修改 `main`。
- Status: Code committed to existing Draft PR; Preview deployment and visual acceptance pending.
- Next step: 验证构建结果并提供 Preview 地址给用户检查。
