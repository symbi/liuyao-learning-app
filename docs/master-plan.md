# 六爻起卦与排盘网页：项目主计划

> 六爻规则以课程资料和 `docs/rules-status.md` 为准；未核实内容不得被模型或程序静默补齐。

## 1. 产品目标

制作一个轻量的六爻学习与排盘工具。核心用途包括：正确生成和保存卦盘；按用户课堂所学检索相关规则和老师案例；辅助分析每日卦例；通过 Memo 记录实际情况并事后复盘。

## 2. 仓库与资料分工

- Public Learning：`symbi/liuyao-learning-app`，保存网页代码、整理好的课程笔记、规则状态、课堂案例、参考资料，以及 Phase 1 每日卦例 JSON。
- Private raw：`symbi/liuyao-learning-raw`，保存课堂原始录音、ASR 转录、原始 PDF 和未整理来源资料。
- 原始 ASR 可能有术语识别错误，只作为回查老师讲解的参考；整理后的课堂总结和独立案例放在 Public Learning。
- 课堂总结、案例、原始 ASR 用相同课次编号 `lesson-XX` 关联。
- Phase 1 每日卦例公开保存在 Public Learning 的 `daily-records/`。数据可能被查看、复制或 Fork，不写入敏感信息。

## 3. Phase 1：验证每日排卦与记录流程

- 当前基线：V80 单页 HTML 原型，排盘规则和 UI 先保持不动。
- 默认 Category 为「今日运势（每日卦）」，问题栏留空；按日本当地日期 `Asia/Tokyo` 读取和保存。
- 每个日期只有一条 `dailyFortune`，重复保存更新同一条，不重复创建。
- Memo 保存在日期文件顶层；同一天额外问事作为 `additionalQuestions` 中的独立记录。
- 每天一个 JSON：`daily-records/YYYY/MM/YYYY-MM-DD.json`。
- HTML 通过 `/api/records/:date` 读写；GitHub 是 Phase 1 持久化位置。
- Cloudflare Pages 托管静态页面和同源 Pages Functions；Pages Functions 负责 GitHub App OAuth 与 GitHub Contents API。
- GitHub App 只安装到 `symbi/liuyao-learning-app`，只授予 Contents Read and write / Metadata Read-only。前端不保存 Token。
- 写入时核对 GitHub blob SHA；冲突时不静默覆盖。
- ChatGPT 在用户提出分析请求时，通过 GitHub 连接器读取当天文件，再关联 Public Learning 的课程笔记和案例。

## 4. Phase 2：把知识辅助分析在线化

Phase 2 的主要目的不是迁移 Phase 1 数据库，而是把 Mac 本地已经验证过的 Query / Evidence Pack 流程部署成在线服务，让 HTML 可以一键分析。

- 在 Google Cloud Run 部署一个 Python FastAPI Service（初期一个 Service / 一个 Container）。
- 内部模块包括 Case/Record 读取适配、GraphRAG Retriever、确定性 Rule Engine、LLM Orchestrator。
- Backend 连接 **同一个 Neo4j AuraDB**，继续使用 Phase 1 已有 Document、Chunk、Embedding、Case 和关系；不重新 Chunk、不重新 Embedding、不重建知识库。
- 后端以 Gemini 或 OpenAI API 的 Generative LLM 生成最终分析报告，再返回 HTML。
- 当前 HTML 的每日 JSON 仍可继续保存在 GitHub；不因为上 Cloud Run 就必须迁移记录数据。
- Supabase/PostgreSQL 仅在未来真正需要多用户身份、私人数据隔离或关系型业务数据时重新评估；不是 Phase 2 的必需组件。

## 5. ChatGPT 辅助分析流程

当用户请求分析当天或指定日期的卦时：

1. 使用已连接的 GitHub 连接读取 Public Learning 对应日期的 JSON。
2. 核对每日运势或指定额外问题的卦盘事实；不凭模型记忆重算或覆盖盘面。
3. 按 Category / Real Question 检索相关课程笔记、规则状态和课堂案例。
4. 外部六爻项目仅作交叉参考；如与老师课程不一致，明确指出分歧。
5. 输出时区分课程明确、课堂案例、外部参考和 AI 综合推理。
6. 用户补充 Memo 或实际情况后，再读取同一日期记录进行复盘。

GitHub 文件更新不会自行启动 ChatGPT 分析；用户提出分析请求时再检索。

## 6. 通用工程原则

- 先读现有 README、规则状态、课程笔记、案例与外部参考，再修改项目。
- 排盘计算必须确定性、可测试；AI 分析和排盘事实分层。
- 课程明确、外部参考、推断、有分歧分别标记。
- 不提交未授权原始课程材料、秘密、令牌、个人隐私或公司资料到 Public。
- 所有记录保留原始日期、时区、规则快照和来源信息，以便复核。