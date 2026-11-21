# 六爻学习与排卦 Web App

一个以课程学习为基础、规则可追溯的六爻学习网页项目。当前 Phase 1 使用轻量单页 HTML 原型验证手动排卦、每日记录、GitHub 保存和 AI 分析工作流。

## 当前项目状态

- `index.html`：手动排卦页面，包含六爻输入、盘面展示、每日 Memo 和卦例记录；以当前 `main` 中的实际实现为准。
- `functions/api/[[path]].js`：Cloudflare Pages Functions，负责 GitHub App 授权与每日 JSON 读写。
- `daily-records/`：Phase 1 每日卦例 JSON，位于本 Public 仓库；数据对所有人公开。
- `docs/ui-mockup.html`：早期 UI 设计稿，不是当前运行页面。

## 仓库与数据边界

- **本仓库（Public，Learning）**：放应用代码、项目文档、整理好的课程摘要、术语表、规则索引、老师课堂案例，以及 Phase 1 每日卦例。
- **现有 raw 仓库（Private）**：继续存放原始课程录音、未经整理的转录稿和未整理来源资料；如将来有获准的原始 PDF，再单独登记和决定存放位置。
- **每日卦例**：Phase 1 暂存在本 Public 仓库的 `daily-records/YYYY/MM/YYYY-MM-DD.json`。卦例和 Memo 公开可见，可能被复制或 Fork；不要写入敏感信息。
- **Phase 1 知识库（待实施）**：计划用 Mac 本地 Python Importer 增量同步到 Neo4j AuraDB；工程步骤、里程碑和验收标准见 [Phase 1 实施计划](docs/phase1-implementation-plan.md)。
- **Phase 2**：未来若要在 HTML 内直接检索知识并生成 AI 报告，再部署一个 Python Backend API；Supabase 仅在需要多用户身份或关系型用户数据时才考虑，不是必选数据库。

## Phase 1 部署

应用通过 Cloudflare Pages 托管，Pages Functions 与页面同源。首次部署需要配置 GitHub App、KV Session binding 和环境变量。完整步骤见 [Phase 1 部署说明](docs/phase1-deployment.md)。

## 文档导航

### 跨窗口与工作区

- [工作区总览与跨窗口交接](docs/workspace-handoff.md)
- [HTML 维护进度与交接记录](docs/html-maintenance-progress.md)
- [Phase 1 跨模型进度与交接记录](docs/phase1-progress.md)

### 产品与架构

- [项目主计划](docs/master-plan.md)
- [Phase 1 数据模型与每日卦例保存方案](docs/data-model-and-storage.md)
- [Phase 1 知识库与课堂案例架构规划](docs/phase1-knowledge-base-architecture.md)
- [Phase 1 实际运行架构、Importer、Neo4j、Gemini、GraphRAG 与分析流程](docs/phase1-operating-model.md)
- [Phase 1 工程实施计划与验收标准](docs/phase1-implementation-plan.md)

### Coding Agent 与部署

- [Claude Code Phase 1 执行 Prompt](docs/claude-code-phase1-execution-prompt.md)
- [所有 Coding Agent 通用规则](AGENTS.md)
- [Claude Code 项目指令](CLAUDE.md)
- [Codex 备用实施 Prompt](docs/codex-phase1-implementation-prompt.md)
- [Phase 1 部署说明](docs/phase1-deployment.md)

### 六爻学习资料

- [历法引擎方案与验证计划](docs/calendar-engine-plan.md)
- [开源项目与古籍参考资料调查计划](docs/reference-research-plan.md)
- [六爻外部参考资料来源目录与双仓库采集/导入方案](docs/reference-source-catalog.md)
- [开源项目分类目录、二十八宿与择日研究备忘录](docs/references/github-project-catalog-and-28-mansions.md)
- [课程笔记总览](docs/lessons/README.md)
- [规则状态与待核实项](docs/rules-status.md)
- [课堂案例目录](materials/class-cases/README.md)

## 安全提醒

不要把密码、访问令牌、GitHub App Secret、个人隐私或公司资料提交到 Public 仓库。Phase 1 的每日卦例和 Memo 是公开数据。

## 免责声明

本项目用于个人学习与规则整理。输出内容不应被视为确定的预测或专业建议。
