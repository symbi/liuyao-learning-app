# HTML 维护进度与交接记录

> 本文件只记录现有 HTML / 前端修复工作。跨窗口总览见 [workspace-handoff.md](workspace-handoff.md)。不要把 Neo4j / Phase 1 的里程碑状态写在这里。

## 当前状态

- Project: `symbi/liuyao-learning-app`
- Workstream: HTML maintenance
- Status: In review (Draft PR open)
- Current task: 把课堂案例的年月日干支拖拽框直接放入原日历三柱位置，移除独立输入区
- Target branch: `fix/trine-anchor-auto-xunkong`
- Active PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Last completed task: v88 原三柱位置直接切换为课堂案例拖拽框
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

## 2026-11-21 — 原三柱位置直接变成课堂案例拖拽框（v88）

- Date: 2026-11-21
- Task: 按用户最新确认的设计，不在日期卡片下面另放一整块「课堂案例年月日干支」；直接复用原本显示自动年月日干支的三个位置作为课堂案例的干支拖拽框。
- User acceptance criteria:
  - 原 HTML 模板、日期卡片、问事分类、六爻 worksheet、Memo、底部六亲/六神/地支六合拖拽区和八宫卦序保持不变。
  - 每日排卦模式：原来的年、月、日三柱照常显示自动计算的日期干支。
  - 输入课堂案例模式：原来的年、月、日三柱值位置本身变为手动拖拽区域；每柱上下两格，分别拖入天干和地支，格子右侧直接标注「天干」「地支」。
  - 不显示额外独立案例年月日输入面板；不显示长篇模式提示、手动干支来源说明。
  - 天干从底部十干 palette 拖入；地支从原有六合地支 palette 拖入；仍可点击 palette 项后点击目标格。
  - 年柱允许未知（两格留空）；月柱、日柱必须填完整合法六十甲子；保存、打开、导出和 AI copy 继续使用原有 `pillarOverride` 持久化结构。
- Branch: `fix/trine-anchor-auto-xunkong`
- PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Implementation commits:
  - `b84e64902e6c9d6462595eba4993705f03e7581d` — 在原三柱显示位置加入六个内联拖拽框，移除独立输入区和说明
  - `e6f637578a3cfd9e264847ace8058b5b39b12828` — 修正原干支显示与拖拽框显隐，避免 CSS 覆盖 hidden
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 在原 `year-pillar`、`month-pillar`、`day-pillar` 三个 `.cal-cell` 内增加两个小目标：stem 和 branch；右侧标签分别为「天干」「地支」。
  - 每日模式隐藏内联目标、显示原 `.calendar-value`；课堂案例模式隐藏自动字符，显示这三组内联目标。没有添加第二套柱区。
  - 删除旧 `case-pillar-editor`、`manual-pillar-grid`、`pillar-source-indicator` 和模式说明句；保留简洁的两个模式按钮。
  - 底部 palette 保留原有六合地支组，在天干 palette 中只标「天干」，地支区只标「地支」。
  - 原有拖拽事件将字符直接写入原三柱的目标格；每格支持清除；六十甲子保存校验及 record `pillarOverride` schema 均保持不变。
- Tests / exact checks:
  - 完整内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认只有六个课堂案例目标格，全部位于原 year/month/day pillar cells 内；旧独立案例输入容器、来源说明和长篇操作说明均已移除。
  - 静态检查确认原十干 palette、六合地支 palette、问事分类、六爻 rows、八宫参考区仍存在。
  - 使用最小 DOM 模拟环境执行切换/拖拽：每日模式启动日期为 `2026.11.21`、日期字段为 `2026-11-21`；课堂模式显示原三柱内的六个拖拽目标。
  - 模拟拖入年柱丙午、月柱己亥、日柱戊戌后，六个原位目标都显示相应字符，月柱/日柱校验无错误；切回每日模式会隐藏拖拽区并恢复原自动值显示。
  - 真实浏览器鼠标/触控拖放、记录保存/重开仍待 Preview 上人工验收。
- Manual browser checks: 待最新 v88 Preview 部署成功并让用户确认原三柱位置、天干/地支标签与底部 palette 拖放体验。
- Security and data-preservation checks:
  - 只修改 `index.html` 和维护日志；未修改每日记录 JSON、GitHub OAuth、Cloudflare Functions、API 保存路由、`main` 或 Production。
  - 未合并 PR，未写入真实卦例。
- Status: Code committed on existing PR branch; static and simulated UI checks passed; latest Preview deployment pending.
- Next step: 验证 v88 Preview 构建成功后，邀请用户检查原三柱位置的拖拽交互。
  

## 2026-11-21 — 原模板加入录入模式切换与干支拖拽（v87）

- Date: 2026-11-21
- Task: 不另做一套页面，直接在原 HTML 模板基础上增加清楚的「每日排卦 / 输入课堂案例」入口；复用原有底部拖拽方式，让课堂案例年月日干支直接从天干、地支素材区拖入。
- User acceptance criteria:
  - 保留原页面 date-card、今日日期和建除/二十八宿区域、问事分类、六爻 worksheet、Memo、底部六亲/六神/地支六合拖拽区、八宫卦序等现有模板。
  - 顶部新增清楚的「每日排卦」与「输入课堂案例」模式按钮；问事分类仍只负责选择占问主题，不承载录入模式。
  - 默认每日排卦模式继续根据日本当天日期自动显示年月日干支；原有纳甲地支/六亲等下方区域继续存在。
  - 选择「输入课堂案例」后，在原日期卡片内展开年、月、日的天干/地支各自拖拽目标格，不再使用此前隐藏的下拉列表。
  - 复用既有六合地支 palette；在其上方新增十天干 tile palette；支持拖动，也保留点击 tile 后点击目标格的回退交互。
  - 每个 pillar 的干/支独立放置、不自动过滤或清除另一边；年柱可两项留空，月柱和日柱须完整、合法六十甲子后才能保存。
  - 手动柱继续使用原有 `pillarOverride` / `pillarSource` 保存结构，并参与月令、日辰、旬空、六神和卦例分析；归档日期仍独立。
- Branch: `fix/trine-anchor-auto-xunkong`
- PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Implementation commits:
  - `330b9eeb84d089745cc55ba7da46735a48697b67` — 新增录入模式、课堂干支拖拽目标和十干 palette
  - `1fbae07f143ecb8bf017b8c32d11a8542406f42d` — 拖拽/点击放入后清除选中态，避免重复落点
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 在原 date-card 顶部日历控制行下新增两个模式按钮；问事分类 dropdown 原样保留，不把录入模式混入占问分类。
  - 保留旧 `toggle-case` DOM 入口为隐藏兼容元素，显示入口改为 `mode-daily` / `mode-classroom`；模式切换更新 `isCaseRecord` 与现有 `pillarOverride.enabled`。
  - 将原手动六个 select 改为六个 `drop-slot` 目标：年干/年支、月干/月支、日干/日支。
  - 在原六个六合配对地支区域上方新增十天干 tile 区；地支仍沿用原 branch-pairs，不复制一套新的地支 palette。
  - 扩展现有 pointer-based drag handler，将天干/地支 token 分别写入指定 pillar；并为目标格保留点击选中后点击落点的操作方式。
  - 每个目标格显示已放入的字符，提供单项清除按钮；保存时继续校验月/日完整、干支有效及年柱完整或未知。
  - 保留原有历史记录字段与分析流程；无新增记录 schema 字段。
- Tests / exact checks:
  - 完整内嵌 JavaScript 通过 V8 语法编译（约 156 KB 脚本）。
  - 静态检查通过：顶部两个 mode buttons、六个 case drop targets、十天干 palette、原 branch-pairs、原 question-category、原 worksheet rows 均存在。
  - 使用最小 DOM 模拟环境执行到 palette 初始化：默认日期显示 `2026.11.21`，日期字段 `2026-11-21`；顶部模式初始为每日模式。
  - 在模拟环境中点击「输入课堂案例」，六个目标格和面板正确显示；天干 palette 有 10 项，原地支 palette 有 12 项。
  - 模拟点击回退流程，将 `己` + `亥` 放入月柱、`戊` + `戌` 放入日柱后，顶端即时显示 `己亥` / `戊戌`，校验提示为空；年柱保持未知可接受。
  - 指针拖拽路由静态检查通过：case pillar target 在普通爻位 assignToken 之前分流到 `assignManualPillarToken`；drop type 不匹配仍会被拒绝。
  - 手动保存校验及 `pillarOverride` / `pillarSource` 原有持久化字段保留。
  - 尚未完成真实浏览器拖放验收；需检查鼠标拖动、点选回退、清除、保存、重开。
- Manual browser checks: 待 v87 Preview 部署后，验证默认每日模式日期干支与原模板、切到课堂案例后六个目标格、底部十干与原六合地支拖拽区、问事分类、六爻 worksheet 和保存/重开。
- Security and data-preservation checks:
  - 仅改 `index.html` 与维护日志；未改 GitHub OAuth、Cloudflare Functions、API 保存路由、每日记录 JSON、`main` 或 Production。
  - 未合并 PR，未写入真实卦例。
- Preview: Cloudflare Pages 部署成功，commit `0ce3532`；独立 Preview `https://bd382961.liuyao-learning-app.pages.dev`，Branch Preview `https://fix-trine-anchor-auto-xunkon.liuyao-learning-app.pages.dev`。
- Status: Code committed to the existing PR branch; Preview build succeeded; actual browser interaction / visual acceptance still awaits user confirmation.
- Next step: 用户打开 v87 Preview，确认顶部模式按钮、年月日干支拖拽目标和底部天干/地支 palette；再按反馈微调原模板。
  

## 2026-11-21 — 修复日历与手动干支控件初始化中断（v86）

- Date: 2026-11-21
- Task: v85 Preview 打开后日本当天日期、年月日干支、手动选择器选项均未初始化；修复前端启动阶段的 JavaScript 异常。
- User acceptance criteria:
  - 页面打开即自动使用 Asia/Tokyo 当天日期，显示年月日干支；日期输入框也显示对应当天日期。
  - 每日记录界面的纳甲/六亲等原有下方区域正常初始化和显示。
  - 手动干支选项正确填充完整十干/十二支，但只有标记案例并启用手动覆盖后才参与计算。
  - 无须合并 PR 或操作 Production 即可通过 Preview 验收。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Fix commits:
  - `a22aa8a6fafe6f0763e7e5ce76ca6432558b694e` — 修正初始化顺序并延迟 worksheet sidecar 渲染
  - `22d2d3834bd04f47dde68060406add81c2b51fc3` — 标记页面版本 v86
- Root cause:
  - `PILLAR_KEYS.forEach(...)` 的事件绑定代码位于 `const PILLAR_KEYS=['year','month','day']` 声明之前。脚本运行到此处会触发 JavaScript temporal-dead-zone ReferenceError，导致整个 IIFE 中断，日期、干支显示和动态选项填充均未执行。
  - 初始日期计算还会调用 `applyPillarContext()`；该流程在 `dateBranchSidecar` 这个 worksheet DOM 节点创建之前调用 `renderDateBranchSidecar()`，同样会读取尚未初始化的 const 并引发异常。
- Implementation summary:
  - 将年月日六个选择器的 change 事件绑定移动到 `PILLAR_KEYS` 声明之后。
  - 只在 `worksheetReady` 为 true 时，才刷新依赖 worksheet 节点的侧栏、爻线指示和分支状态；初始日期计算仍照常写入年月日干支和日期字段。
  - 保留 v85 的完整十干/十二支独立选择逻辑与六十甲子保存校验。
  - 每日模式仍按日本当天日期自动计算；课堂案例的手动干支只在明确启用 override 时覆盖日期自动值。
- Tests / exact checks:
  - 完整内嵌 JavaScript 通过 V8 语法编译。
  - 静态初始化顺序检查通过：`PILLAR_KEYS` 的声明位置早于所有选择器事件绑定。
  - 使用最小 DOM 模拟环境执行日历启动流程，未发生运行时异常；模拟输出日期 `2026.11.21`、年柱 `丙午`、月柱 `己亥`、日柱 `己亥`；六组选择器均填充 10 个天干与 12 个地支选项。
  - worksheet sidecar 调用已置于 `worksheetReady` 分支中，避免在 DOM 尚未创建时读取 `dateBranchSidecar`。
  - 仍需最新 Preview 上的真实浏览器验收：页面日期显示、年月日干支、日历下方纳甲/六亲区域、完整手动选择器、案例保存/重开。
- Manual browser checks: 修复后待 Preview 部署成功并由用户确认；不可把 V8 编译通过等同于浏览器交互验收。
- Security and data-preservation checks:
  - 仅修改 `index.html` 和本维护日志；未更改每日记录数据、GitHub OAuth、Cloudflare Functions、保存 API、main 或 Production。
  - 未合并 PR。
- Status: Code committed to existing Draft PR; syntax and simulated startup checks passed; latest v86 Preview deployment pending and visual/browser acceptance remains.
- Next step: 验证 Cloudflare 最新构建成功后，请用户重新打开独立 Preview 地址进行页面验收。


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
  - Cloudflare Pages Preview 已构建成功：commit `564804d`，独立预览 `https://13cbb327.liuyao-learning-app.pages.dev`；Branch Preview `https://fix-trine-anchor-auto-xunkon.liuyao-learning-app.pages.dev`。
- Manual browser checks: 待用户在 Preview 中确认：日常页面仍自动显示当天年月日干支；标记课堂案例后，年/月/日每一柱的天干下拉框可看到完整十项，地支下拉框可看到完整十二项；选择一侧不会影响另一侧；非法组合有提示；合法组合可保存并重开。
- Security and data-preservation checks:
  - 只更改 `index.html` 和本维护日志；未改 GitHub OAuth、Cloudflare Functions、API 保存路由或 Production 配置。
  - 未写入或改动任何真实每日记录；未合并 PR，未修改 `main`。
- Status: Code committed to existing Draft PR; Cloudflare Preview deployment succeeded; actual browser interaction / visual acceptance remains pending.
- Next step: 用户打开 Branch Preview，检查每日自动干支与课堂案例完整选择器；确认后再处理可能的视觉微调。


## 2026-11-21 — 课堂案例干支拖放布局微调（v89）

- Task: 按用户检查 v88 后的反馈，恢复案例干支目标框的正常尺寸，并调整十天干来源区的位置。
- User acceptance criteria:
  - 年、月、日每柱的两个目标框均恢复为与每日干支单字相同的 36×36 尺寸。
  - 目标框内不再重复显示“天干 / 地支”小标签；用两个上下排列的空框表示一柱的天干、地支。
  - 十天干拖拽来源移动到顶部年月日时间区域右侧；底部选择区只保留原有六合地支配对，不再重复增加天干。
  - 每日模式不显示课堂案例十天干来源；课堂案例模式才显示。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 三组案例干支目标框改为上下排列，每格 36×36；移除目标框旁边的“天干 / 地支”文字。
  - 十天干项目仍由原来的 `#stem-tiles` 容器和原拖拽逻辑生成，但容器移至顶部日历年月日区域右侧，标题简化为“放入天干”。
  - 底部调色板只保留原有地支六合配对与六亲、六神项目。
  - 案例模式显示顶部天干拖拽区；每日模式隐藏它。六十甲子校验、`pillarOverride` 保存/恢复和计算逻辑未改。
- Tests / exact checks:
  - 内嵌 JavaScript 全部通过 V8 语法编译。
  - 静态检查确认六个目标框仍在年、月、日柱内；每个目标框 36×36；目标框无重复小标签；底部只有地支入口；顶部仅有一个十天干来源容器。
  - 待用户在 Preview 中实际确认拖拽位置、视觉尺寸，以及保存/重开。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API、记录 schema 或真实记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 天干与地支拖拽区合并到年月日输入框旁（v90）

- Task: 按用户检查 v89 后的反馈，移除天干/地支文字标题，并把两组拖拽来源集中到年月日手动输入框旁。
- User acceptance criteria:
  - 不再显示“放入天干”或单独的“地支”提示字。
  - 十天干排在第一行，六合配对地支紧接着排在第二行。
  - 两行来源区域靠左，紧挨年、月、日干支输入框，便于拖动到目标格。
  - 页面底部不再单独保留地支拖拽区；六亲、六神区域继续保留。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 将 `#stem-tiles` 与 `#branch-pairs` 两个原有拖拽来源都放进顶部同一个容器，按天干行、地支行上下排列。
  - 容器按年月日输入区域左侧的自然顺序紧接日柱目标框，不再通过 `margin-left:auto` 推到右下角。
  - 删除“放入天干”和底部“地支”标题；底部仅保留六亲、六神拖拽项。
  - 拖拽 token、六合配对样式、六十甲子校验和 `pillarOverride` 数据逻辑均沿用原实现。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认十天干与六合地支各只有一个容器，且均位于日柱输入框之后、旬空组件之前；两个来源行上下排列，均无可见标题。
  - 待用户在 Preview 中检查桌面布局与窄屏换行，并实际测试拖拽、保存和重开。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API、记录 schema 或真实记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 保留底部地支并复制顶部干支来源（v91）

- Task: 修正 v90 对拖拽来源位置的误解。
- User acceptance criteria:
  - 年、月、日输入框之后，原有旬空/六神的三个框保持连续成组，不被天干或地支来源打断。
  - 旬空三个框的右侧紧接一个两行拖拽区：第一行十天干，第二行六合地支。
  - 底部原有六合地支区必须保留在原位置，作为第二份地支拖拽来源，方便从下往上拖。
  - 两处地支都无文字标签；顶部不显示“放入天干”等提示。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 将日干六神与旬空组件整体放在年月日柱之后，保持 day-god + 两个旬空格连续。
  - 将顶部天干、地支来源容器放到旬空组件右侧，地支使用独立的 `#branch-pairs-top`。
  - 恢复底部原位置的 `#branch-pairs` 六合地支来源，不加“地支”标题。
  - 两套地支项目均由同一六合配对定义生成；各自都是真实可拖拽 tile，点击选择状态同步高亮。
  - 六十甲子校验、手动干支存储、记录 schema 和日常排卦逻辑不变。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认旬空三个框连续且位于两排拖拽来源之前；顶部与底部各有一份地支容器；天干只有顶部一份；两份地支均由代码填充。
  - 待用户在 Preview 中实际检查布局与拖拽行为。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API、记录 schema 或真实记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 放大顶部干支来源并加强悬停/选中反馈（v92）

- Task: 按用户反馈，顶部天干、地支项目应与原底部地支来源大小接近，并清楚显示当前选中状态。
- User acceptance criteria:
  - 顶部十天干恢复标准拖拽 tile 尺寸（28×30），不再比原调色板小。
  - 顶部六合地支使用与原底部六合地支相同的配对格和 tile 尺寸（桌面 29×29；窄屏沿用原有 27×28 / 25×27 响应式尺寸）。
  - 鼠标悬停时 tile 轻微上浮/放大；点选后保持更明显的轻微放大、高亮和阴影，确认选中项更直观。
  - 拖动时仍显示 grabbing 手势，原有拖拽和点击回退行为不变。
- Branch: `fix/trine-anchor-auto-xunkong`
- Draft PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Files changed: `index.html`, `docs/html-maintenance-progress.md`
- Implementation summary:
  - 移除顶部地支专用的缩小覆盖样式，改为继承底部六合配对的原始尺寸和窄屏规则。
  - 顶部天干恢复标准 28×30 tile。
  - 全部 tile 悬停轻微上浮放大；选中状态使用更明显的 1.08 倍放大、金色外框和柔和阴影；六合配对中的地支也明确保留相同选中动画。
  - 维持 cursor:grab / grabbing 的拖拽手势反馈；转换仅影响视觉，不改变拖拽状态或数据。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认顶部十天干为标准尺寸，顶部地支不再有小尺寸覆盖且沿用与底部相同的响应式规则；悬停/选中/拖动光标反馈均存在。
  - 待用户在 Preview 中确认实际大小手感和选中动画。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API、记录 schema 或真实记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 加强干支拖拽项目的悬停与选中动画（v93）

- Task: 用户认为 v92 的上浮和放大比例仍不够明显。
- User acceptance criteria:
  - 悬停状态比 v92 更明显，能看见项目上浮和放大。
  - 选中状态比悬停再突出一档，便于确认当前选择。
  - 动画过渡平滑；鼠标抓取/拖动光标反馈保留。
  - 不改变干支项目本身的布局尺寸和数据/拖拽逻辑。
- Implementation summary:
  - 普通悬停改为上浮 4px、放大 1.12 倍，并增加柔和阴影。
  - 点击选中改为上浮 6px、放大 1.18 倍，金色边框和阴影更明显。
  - 六合地支项目使用相同的悬停及选中动画；增加选中且悬停时的覆盖规则，避免原有六合 hover 样式覆盖选中效果。
  - 过渡时间由 0.14s 调为 0.2s 缓动；保留 grab / grabbing 光标。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认悬停 translateY(-4px)/scale(1.12)、选中 translateY(-6px)/scale(1.18)、六合地支覆盖规则和鼠标抓取光标均存在。
  - 顶部干支基础格子尺寸没有变化。
  - 待用户在 Preview 中实际确认动画幅度。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API、记录 schema 或真实记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 课堂案例 Memo 简化为纯输入框（v94）

- Task: 根据用户反馈，课堂案例记录只需要直接输入老师的分析内容，不需要“课堂案例 Memo”、案例类型、核对状态或说明文案。
- User acceptance criteria:
  - 课堂案例模式下不显示 Memo 标题。
  - 不显示“案例类型”及其选项；课堂案例默认沿用课堂来源。
  - 不显示“核对状态”及待核对/已核实/存在分歧选项。
  - 不显示案例说明文字或输入框 placeholder，只保留直接输入老师分析的 textarea。
  - 每日排卦模式的“每日记录 Memo”标题与日常记录 placeholder 保持原样。
  - 课堂案例分析仍保存到 `caseMemo`，重新打开时恢复内容。
- Implementation summary:
  - 课堂案例模式隐藏 memo header 和 legacy case metadata 区；textarea 不显示标题或 placeholder。
  - 通过 textarea 的无障碍标签标识“老师的分析”，视觉上没有额外文案。
  - 继续保留隐藏的旧 metadata DOM/读取兼容字段，避免影响旧记录载入；新保存记录不再写入 `caseReviewStatus`。
  - 课堂案例的 `caseMemo` 存储和重新打开恢复逻辑保持不变；每日记录 Memo 不变。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认案例模式隐藏标题和 metadata、空 placeholder、保留 caseMemo 写入/读取、每日模式原有标题仍保留。
  - 待用户在 Preview 中确认视觉效果和保存/重开。
- Security and data-preservation checks:
  - 仅修改 HTML 和本维护日志；未更改 OAuth、Cloudflare Functions、API 或历史记录内容。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.


## 2026-11-21 — 修复指针拖拽跟随与案例干支颜色（v95）

- Task: 用户反馈实际拖动时没有跟随鼠标的视觉效果；点击后放入虽成功，但案例干支目标框内文字没有沿用原项目的五行色样式。
- Root causes found:
  - 拖拽影子克隆是在 `updateSelectedTiles()` 之后创建的，克隆本身带有 `.tile.selected`。该规则把 `position:fixed` 覆盖成 `position:relative`，导致影子无法按视口坐标跟随鼠标。
  - `renderManualPillarInputs()` 拼接类名时漏掉空格，将 `drop-token` 和 `element-wood` 合成了 `drop-tokenelement-wood` 等无效类名，故五行颜色规则未生效。
- Implementation summary:
  - 拖拽开始时克隆来源项目后移除 `.selected` 类，再赋予独立 `.drag-ghost` 类。
  - 对拖拽影子的 `position:fixed` 和居中 transform 使用高优先级规则；创建时同时设置宽、高、left、top，后续每次 pointermove 更新到指针坐标。
  - pointerdown 时调用 `setPointerCapture(pointerId)`，让源项目在拖动越过其他元素后仍持续接收指针事件。
  - 修复案例年月日输入框 token 的 className 分隔符，使天干、地支正确附加 `element-wood / element-fire / element-earth / element-metal / element-water` 等五行类。
  - 案例干支显示字号调整为 16px、加粗，匹配 36px 目标格；点击选择回退和数据存储逻辑不变。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认拖拽影子移除 selected 冲突类、固定定位与 translate 居中规则存在、pointer capture 已启用，left/top 随 pointermove 更新。
  - 静态检查确认案例 token 类名正确包含空格，五行 CSS 类可生效，字体 16px/850 weight。
  - 尚未通过用户真实鼠标操作完成视觉验收；请在 Preview 里测试直接拖动是否跟随鼠标，并检查木属性干支是否显示绿色。
- Security and data-preservation checks:
  - 仅修改 HTML 与维护日志；未改 OAuth、Cloudflare Functions、API、记录 schema 或历史记录。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on the existing PR branch; Preview deployment pending.

## 2026-11-21 — 自动识别伏神并独立保存老师结论（v96）

- Task: 用户希望课堂案例在主要用神不上卦时能显示伏神，并把老师分析过程与最终结论分开记录。
- User acceptance criteria:
  - 不增加第七爻；伏神显示在本卦对应飞神的同爻位下方。
  - 当主要用神属于六亲、且本卦六爻均没有该六亲时，从本宫首卦同爻位取伏神。
  - 显示伏神六亲、纳甲地支、五行，以及飞神与伏神之间的五行关系；保存并进入 AI 导出。
  - 若用神已在本卦出现，不重复添加伏神；主要用神不是六亲或资料不完整时，不假装得出结果。
  - 课堂案例保留原老师分析文本框，并新增独立「老师结论」输入框；支持保存、重新打开、JSON 导出和 AI 复制。
  - 每日记录模式不显示课堂结论框；旧记录缺少结论字段时按空值兼容，不覆盖原案例分析。
- Implementation summary:
  - 新增八宫首卦纳甲地支表（自初爻至上爻），按卦宫五行计算六亲；主要用神在本卦缺失时，从本宫首卦对应爻位取伏神。
  - 新增结构化 `analysisSnapshot.hiddenSpirits`，包含伏神爻位、六亲、地支、五行、本宫首卦来源、同位飞神及飞伏五行关系。
  - 伏神只在有对应数据时显示在原爻行下方，不增加第七爻、不改变现有爻位和纳甲输入布局。
  - 课堂案例新增「老师结论」框；原有 `caseMemo` 保存分析过程，新字段 `caseConclusion` 独立保存。
  - 保存、重新打开、未保存修改检测、记录列表摘要、JSON 导出及 AI 复制均包含新结论；AI 复制也包含伏神/飞神可读分析和 JSON 结构。
  - 记录 schema 更新为 v15，analysisSnapshot 更新为 v4；旧 v14 / snapshot v3 仍可读取，旧快照在 AI 复制时会补算伏神。
- Tests / exact checks:
  - HTML 内嵌 JavaScript 通过 V8 语法编译。
  - 天水讼（离宫）fixture：离为火本宫纳甲为卯、丑、亥、酉、未、巳；六亲依次父母、子孙、官鬼、妻财、子孙、兄弟；官鬼亥水落第三爻。
  - 本案例第三爻飞神为兄弟午火，伏神为官鬼亥水；五行关系为「伏克飞」。
  - 静态检查确认 v96、结论保存与 AI 导出、八宫首卦纳甲表、hiddenSpirits 快照、六爻下方显示及 schema v15 / snapshot v4。
  - 尚未执行真实浏览器视觉验收；需在 Cloudflare Preview 中检查伏神显示、结论框显示/隐藏、保存后重开与 AI 复制。
- Security and data-preservation checks:
  - 仅更新 `index.html` 与本维护日志，没有修改任何既有 daily-records JSON 或老师原始分析内容。
  - 保留旧 `caseMemo` 字段和旧记录兼容；无 OAuth、Cloudflare Functions、API 或凭据逻辑变更。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on existing HTML maintenance PR #1 branch; Preview deployment and browser acceptance pending.
- Next step: 用户在 Branch Preview 检查 v96 伏神显示及老师结论输入框，并核对保存/重开和 AI 复制。
- v96 follow-up check: switching the question category now refreshes the displayed hidden spirit immediately; automatic lookup now waits until all six line-relative values can be determined, preventing an incomplete row from being mistaken for a missing use god.

## 2026-11-21 — 将自动伏神长说明改为逐爻手动伏藏标记（v97）

- Task: 用户认为 v96 自动显示的伏神/飞神细节文字太多，也不希望页面擅自判断伏神落点；改为每爻保留紧凑、可拖拽的伏藏六亲标记位。
- User acceptance criteria:
  - 删除自动产生的「伏」「官鬼亥水」「伏克飞」「飞神兄弟午火」「明动」等长说明。
  - 每一爻本卦纳甲地支左侧放一个小型可选框；可从下方既有六亲调色板拖入父母、兄弟、子孙、妻财或官鬼。
  - 填入后仅显示所选六亲名称，例如「官鬼」；空白表示没有人工录入伏藏标记。
  - 不新增第七爻，不要求程序自行判断伏神位置。
  - 保留 v96 的「老师结论」框及其保存、重开和 AI 导出。
- Implementation summary:
  - 移除 v96 自动推导伏神的八宫纳甲表、自动推导/显示逻辑及详细飞伏文字。
  - 每爻纳甲地支左侧新增 21px 紧凑六亲标记槽；直接复用现有六亲项目的拖拽和点击后放入机制。
  - 标记写入每条 line 的 `hiddenRelation`，支持清除、保存到 GitHub、重新打开、JSON 导入导出和 AI 复制。
  - AI 输出增加「伏藏六亲（人工标注）」；若六爻六亲已全部填写、主要用神却未出现且没有伏藏标记，提示需要人工核对，不会擅自断定用神已上卦。
  - 记录 schema 升级为 v16，analysisSnapshot 升级为 v5；保留旧记录与老师结论字段兼容。
- Tests / exact checks:
  - HTML 内嵌 JavaScript 通过 V8 语法编译。
  - 静态检查确认每爻迷你标记槽位、拖拽监听、render/save/restore、AI 人工标注输出、schema v16 / snapshot v5 已写入。
  - 人工标记数据 fixture 验证「官鬼」可保存并恢复。
  - 尚未进行真实浏览器视觉、拖拽、保存重开和 AI 复制验收。
- Security and data-preservation checks:
  - 仅修改 HTML 与维护日志，不触碰任何既有课堂案例 JSON 或每日记录。
  - v96 新增的老师结论字段继续保留；旧 `caseMemo` 不变。
  - 未合并 PR，未修改 `main` 或 Production。
- Status: Updated on existing HTML maintenance PR #1 branch; Cloudflare Preview and user browser acceptance pending.
- Next step: 在 Preview 检查小格位置与宽度、拖入/清除六亲、保存重开和 AI 复制。
- v97 final polish: the compact tag text now uses 9px so the two-character 六亲 fits the 21px slot; its hover-clear control is scaled down. The AI consistency warning is limited to 六亲 use gods and checks whether the matching 六亲 itself was marked.


## 2026-11-21 — 自动装卦与只读检查（v98）

- Task: 在保留 v97 手动拖拽学习方式的基础上，增加「自动装卦」和「检查卦盘」两个独立入口。
- User acceptance criteria:
  - 自动装卦按本卦上下卦的纳甲规则计算六爻地支，并按本卦卦宫五行装六亲。
  - 按起卦日干确定初爻起始六神，再由初爻向上依次排列六神。
  - 明动爻按变卦上下卦重新计算对应变爻纳甲地支和六亲。
  - 年、月、日柱的六亲标记可按同一卦宫五行计算；六神起神对应日干。
  - 自动装卦只补空白项；已有内容（包括错误值）不覆盖，只报告差异。
  - 「检查卦盘」只核对，不写入、不改动数据；错误槽位用红色标记，未填写项用黄色标记，并显示当前值/正确值。
  - 伏藏六亲仍完全由用户手动标记；暗动的变卦纳甲不在未核实规则前自动生成。
- Implementation:
  - 页面标题更新为 v98；在六爻区域增加「自动装卦」「检查卦盘」按钮及检查结果面板。
  - 以底部到顶部的六爻阴阳 pattern 分别识别下卦/上卦；下卦使用内卦纳甲，上卦使用外卦纳甲。
  - 新增八卦内外卦纳甲地支表；六亲以本卦宫五行为基准，变爻六亲也沿用本卦宫五行。
  - 六神使用第八课确认的日干起神表及青龙→朱雀→勾陈→螣蛇→白虎→玄武顺序。
  - 变卦先翻转明动爻阴阳，再按变后的上下卦重新取纳甲；只向现有明动爻变卦槽位填入对应数据。
  - 自动装卦只补空值，不调用手动拖拽覆盖逻辑；检查按钮不会写入任何字段。
  - 修改日期、摇卦阴阳、拖拽/清除字段或重新打开记录时，清除旧检查提示，避免标记过期。
  - 复用现有记录字段（branch / relation / shen / changeBranch / changeRelation / calendarAssignments），不增加记录 schema 字段。
- Tests / exact checks:
  - 内嵌 JavaScript 通过 V8 语法解析。
  - 八宫纯卦纳甲 fixture 全部通过：乾、坎、艮、震、巽、离、坤、兑的初爻至上爻顺序均与仓库课堂笔记一致。
  - 第十九课案例 fixture：天水讼本卦纳甲为寅辰午午申戌；第三爻明动后，天风姤变卦纳甲为丑亥酉午申戌，第三爻为酉金。
  - 已静态检查自动填入、非破坏式检查、错误/缺失高亮、输入变更后清除旧提示等关键代码路径。
  - 尚未完成真实浏览器操作验收：须在 Preview 上点击两按钮，检查手动错误不会被覆盖、检查按钮完全不修改、保存/重开保留结果。
- Rule boundaries:
  - 本卦和变卦六亲均按本卦卦宫五行计算。
  - 旬空沿用当前日柱自动计算；不把旬空拖拽槽当作用户可编辑项目。
  - 伏藏六亲不自动推导，也不把人工伏藏标记当作原六亲计算结果。
  - 暗动仅按现有第十一课逻辑识别；由于课程笔记将暗动是否在所有情形下生成变爻纳甲列为待核实，v98 暂不自动填写暗动的变卦纳甲。
- Security and data-preservation checks:
  - 只修改 index.html 和本维护日志；不修改 daily-records JSON、课程原始资料、OAuth、Cloudflare Functions、API 或凭据。
  - 未修改 main、未合并 PR #1、未部署 Production。
- Status: Implemented on existing PR #1 branch; browser Preview verification pending.
- Next step: 检查 Cloudflare Preview 部署后实际交互与保存/重新打开行为，再按反馈调整。


## 2026-11-21 — 自动装卦反馈文案与 AI 文字卦盘补全（v98 follow-up）

- User feedback: 自动装卦从全空白卦盘开始时，不应把程序刚填写的字段报告成「正确 24 项」；只有用户原本手工填写的内容存在错误时才列出错误。用户还要求复制给 AI 的文字能逐爻完整说明月令状态、月破、旬空等信息。
- Auto-fill / checker changes:
  - 点击自动装卦前先保存一份原始字段快照；仅将原来为空的字段自动补上。
  - 自动补上的值不再进入「用户填写正确/错误」统计；汇总只说补了多少空白字段，不列正确数。
  - 对原来已经手工填写的值逐项核对：错误会标明当前值、正确值并保留原值；检查按钮只列错误与缺失项，不列正确项目。
  - 如果没有空白项，显示「没有需要自动填写的空白项目」，避免显示自动填写 0 项。
- AI-readable text export changes:
  - 增加本卦上卦、下卦、卦宫五行、卦宫世次，以及世爻/应爻的纳甲五行关系。
  - 每爻逐一输出阴阳摇卦标记、纳甲地支与五行、月令旺相休囚死、旬空/不旬空、月破/不月破、月建对本爻的五行生克/六冲/六合、日辰对本爻的五行生克/六冲/六合、六亲、六神、世应身份、动静状态和人工伏藏标记。
  - 动爻若缺少变卦纳甲或变爻六亲，会明确写「未填写」；全卦皆静时明确写「无明动或暗动，未形成变卦」。
  - 明确输出年/月/日柱、日干起六神、旬空地支、三合/六合识别、老师分析 Memo、老师结论，并继续附上原始 JSON / analysisSnapshot。
- Factory modification case reviewed from the user's saved main-branch record:
  - Record ID: `7e0a6b19-92f2-4f8c-b7b0-8771955ad45b`; question: 厂房改造是否可以成功，能否中标。
  - Saved chart: 火风鼎，离宫火，二世；上离、下巽；乙卯月、戊午日；旬空子丑；二爻世、五爻应；应克世。
  - Lines from 初爻 to 上爻: 丑土子孙勾陈（囚、旬空）；亥水官鬼螣蛇（休、世）；酉金妻财白虎（死、月破）；酉金妻财玄武（死、月破）；未土子孙青龙（囚、应）；巳火兄弟朱雀（相）。六爻皆静。
  - The export now spells out that 午火克酉金; the two 酉金妻财 lines are both 静爻、卯月月破, not旬空. It also spells out all other lines' month/day interactions.
  - User memo has the parenthetical phrase「日克（用神克日建）」. From the saved 戊午日 and 酉金用神 branches, the computed direction is 日支午火克爻支酉金; the original Memo is preserved verbatim and not rewritten.
- Tests / exact checks:
  - Inline JavaScript passed V8 syntax compilation after each follow-up change.
  - Auto-fill logic now compares only fields that were non-empty before automatic filling; no success count is generated for newly auto-filled values.
  - Static inspection confirms full line-level month/day relations and seasonal states are included in AI-readable text.
  - Actual browser click-through and copied-text clipboard review still need user-side Preview acceptance; no claim of end-to-end browser interaction testing.
- Security and data-preservation:
  - Only `index.html` and this maintenance log are changed on PR #1 branch. The saved factory case JSON and original Memo/conclusion were not modified.
  - `main`, Production, Pages Functions, OAuth, credentials and original course records remain untouched.
- Status: Updated on existing PR #1 branch; Preview deployment and user's browser acceptance pending.


### v98 follow-up fixture verification — 2026-11-21

- Executed the actual AI formatter function against saved factory-case JSON `7e0a6b19-92f2-4f8c-b7b0-8771955ad45b` in an isolated JavaScript harness. The generated readable text explicitly contains: 火风鼎、离宫火、上离下巽、二世、二爻世/五爻应、应克世、乙卯月戊午日、旬空子丑、六神起勾陈、all six line coin/yin-yang states, six branches/elements/kins/gods, per-line monthly status, per-line day/month five-element relations, month-break, void status, moving/static state, manual hidden-spirit state, case memo and conclusion.
- Assertions passed: palace and upper/lower trigram present; two 妻财 lines present; both 酉金 lines show 月破 and 日支午火克爻支酉金; 旬空子丑 present; all six static lines explicitly described; 世应 relation and teacher conclusion present.
- Executed the actual `runAutoAssembly` function with mocked UI callbacks for three cases:
  - All blank → fills the 3 blanks and reports only「已自动填写 3 个原本空白的项目。」; no「正确」count.
  - Two wrong + one blank → fills only the blank, reports the two pre-existing manual errors, and preserves both wrong values untouched.
  - Check-only with one correct, one wrong, one blank → reports one error and one missing item, lists neither correct item, and writes nothing.
- These are isolated function tests, not full browser interaction tests. Preview click-through and record save/reopen remain for user acceptance.
