# 六爻学习与排卦 Web App

一个以课程学习为基础、规则可追溯的六爻学习网页项目。当前 Phase 1 使用轻量单页 HTML 原型验证手动排卦、每日记录、GitHub 保存和 AI 分析工作流。

## 当前项目状态

- `index.html`：V80 手动排卦页面，包含六爻输入、盘面展示、每日 Memo 和卦例记录。
- `functions/api/[[path]].js`：Cloudflare Pages Functions，负责 GitHub App 授权与每日 JSON 读写。
- `daily-records/`：Phase 1 每日卦例 JSON，位于本 Public 仓库；数据对所有人公开。
- `docs/ui-mockup.html`：早期 UI 设计稿，不是当前运行页面。

## 仓库与数据边界

- **本仓库（Public，Learning）**：放应用代码、项目文档、整理好的课程摘要、术语表、规则索引、老师课堂案例，以及 Phase 1 每日卦例。
- **现有 raw 仓库（Private）**：继续存放原始课程录音、未经整理的转录稿、原始 PDF 和未整理来源资料。
- **每日卦例**：Phase 1 暂存在本 Public 仓库的 `daily-records/YYYY/MM/YYYY-MM-DD.json`。卦例和 Memo 公开可见，可能被复制或 Fork；不要写入敏感信息。
- **Phase 2**：流程验证后再引入 Login 和数据库（例如 Supabase），届时把每日记录迁移到按用户隔离的存储。

## Phase 1 部署

应用通过 Cloudflare Pages 托管，Pages Functions 与页面同源。首次部署需要配置 GitHub App、KV Session binding 和环境变量。完整步骤见 [Phase 1 部署说明](docs/phase1-deployment.md)。

## 文档导航

- [项目主计划](docs/master-plan.md)
- [Phase 1 数据模型与每日卦例保存方案](docs/data-model-and-storage.md)
- [Phase 1 知识库与课堂案例架构规划](docs/phase1-knowledge-base-architecture.md)
- [Phase 1 部署说明](docs/phase1-deployment.md)
- [历法引擎方案与验证计划](docs/calendar-engine-plan.md)
- [开源项目与古籍参考资料调查计划](docs/reference-research-plan.md)
- [开源项目分类目录、二十八宿与择日研究备忘录](docs/references/github-project-catalog-and-28-mansions.md)
- [课程笔记总览](docs/lessons/README.md)
- [规则状态与待核实项](docs/rules-status.md)
- [课堂案例目录](materials/class-cases/README.md)

## 安全提醒

不要把密码、访问令牌、GitHub App Secret、个人隐私或公司资料提交到 Public 仓库。Phase 1 的每日卦例和 Memo 是公开数据。

## 免责声明

本项目用于个人学习与规则整理。输出内容不应被视为确定的预测或专业建议。
