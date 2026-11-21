# HTML 维护进度与交接记录

> 本文件只记录现有 HTML / 前端修复工作。跨窗口总览见 [workspace-handoff.md](workspace-handoff.md)。不要把 Neo4j / Phase 1 的里程碑状态写在这里。

## 当前状态

- Project: `symbi/liuyao-learning-app`
- Workstream: HTML maintenance
- Status: In review (Draft PR open)
- Current task: 在原 HTML 模板中加入明确录入模式与天干/地支拖拽式课堂案例输入
- Target branch: `fix/trine-anchor-auto-xunkong`
- Active PR: [#1](https://github.com/symbi/liuyao-learning-app/pull/1)
- Last completed task: v87 原模板录入模式切换与干支拖拽输入
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
- Status: Code committed to the existing PR branch; Preview build / real browser acceptance pending.
- Next step: 等待当前 Preview 构建成功后，在原模板上检查模式切换与拖拽操作。
  

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
