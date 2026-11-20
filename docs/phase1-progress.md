# Phase 1 进度与跨模型交接记录

> 本文件是 Claude Code、Codex、ChatGPT 或其他模型之间的持久化项目记忆。切换模型时，以 GitHub 当前 main 分支中的本文件和引用文档为准，不依赖旧聊天窗口的记忆。

## 当前状态

- Project: symbi/liuyao-learning-app
- Phase: Phase 1 — Neo4j Knowledge Base + Incremental Importer + Evidence Pack
- Status: awaiting_chatgpt_review
- Current milestone: M1 — Python project skeleton and review fixes
- Phase 1 plan baseline commit: f5869ad643c94760e72e77f0bc3d747fa3b38652
- Implementation code status: implementation_complete_pending_chatgpt_review
- Active implementation branch: phase1/m1-python-skeleton
- Active PR: PR #2
- Last completed milestone: M0
- Next action: resolve review comments and request another review
- Last updated: 2026-11-20

## 已冻结的架构决定

1. Neo4j AuraDB Free 是 Phase 1 的云端知识图谱主数据库；Neo4j Desktop 可选用于本地学习，但不建立两份不同步的主库。
2. Phase 1 的 Importer 和 Query Tool 运行在用户 Mac；Python virtualenv 即可，不用 Docker。
3. Phase 1 不部署 Cloud Run Backend，不接 Supabase/PostgreSQL，不做 HTML 一键分析。
4. Phase 2 才把 Query / Evidence Pack / Rule Engine / LLM Orchestrator 整合为 Cloud Run FastAPI 服务；继续使用同一个 AuraDB，不重新导入。
5. Source A Raw：Private raw 中的录音和低准确率 ASR 默认只登记来源/版本，不进入主要 Chunk、Embedding 或规则抽取。
6. Source B Curated：Learning 中经过 ChatGPT 整理的课堂笔记，是主要课程 Chunk 来源。
7. 用户明确选择的 PDF、外部 GitHub README/docs 可以进入外部参考轨道；保留 URL、版本、License，不与课程来源混淆。源码按文件/类/函数边界处理，属于后续子阶段。
8. Chunk 之后并行执行 Embedding 和 Generative LLM 候选知识抽取。Generative LLM 是大语言模型；抽取结果永远是 candidate，不自动成为老师确认规则。
9. Neo4j 保存 Document、Revision、Chunk、Case、Concept、RuleCandidate、关系和向量。同步 Manifest 放在 Neo4j，不另建 SQLite 数据库。
10. HTML 的每日 JSON 继续由现有 Cloudflare Pages Functions 保存到 GitHub；Phase 1 Importer 另行增量同步，不做浏览器实时双写。
11. Phase 1 Query Tool 从 AuraDB 检索并输出带出处的 Evidence Pack；最终报告由 ChatGPT Web 完成，用户手动交接。
12. 用户不需要逐条审核节点；系统自动保留来源、课程、页码/段落、版本、模型和不确定性。

## 里程碑状态

| Milestone | 目标 | 状态 | Review PR / Merge commit | 备注 |
|---|---|---|---|---|
| M0 | 创建 AuraDB Free、保存本地凭据、连接与 Vector Index smoke test | completed | — | 用户环境验收完成；原始报告保留在用户本地，不虚构独立 PR 或 merge commit |
| M1 | Python 项目骨架、配置、CLI、日志、doctor、sources list、dry-run | awaiting_chatgpt_review | PR #2 / no merge commit | 当前分支已修复 URI 凭据、Gemini optional 和外部凭据文档问题，等待第二轮审核 |
| M2 | Markdown/TXT/PDF/JSON Source Adapters | not_started | — | PDF 真实样本需用户提供，先用 fixture |
| M3 | Neo4j Schema、唯一约束、Vector Index、稳定 IDs | not_started | — | 真实 AuraDB smoke test |
| M4 | 增量 Importer、Hash、Revision、Chunker、MERGE | not_started | — | 第二次相同导入不能触发模型调用 |
| M5 | Gemini Embedding + Generative LLM 双路径 | not_started | — | 先确认模型、维度、数据条款 |
| M6 | Allowlist 外部 PDF/GitHub 文档和后续代码参考 | not_started | — | 用户先确认来源与 License |
| M7 | Query Tool、向量/图关系检索、Evidence Pack | not_started | — | 不生成最终占卜报告 |
| M8 | 端到端验收 | not_started | — | 真实课程、真实案例、获准参考材料 |

允许状态值：not_started、in_progress、awaiting_chatgpt_review、changes_requested、completed、approved_merged、blocked。

## 每个里程碑的交接记录模板

完成一个里程碑后，由执行模型在该分支更新本文件：

- Milestone:
- Status: awaiting_chatgpt_review
- Branch:
- Draft PR URL:
- Base main SHA:
- Implementation commit SHA:
- Files changed:
- Tests run (exact commands):
- Test results:
- Manual checks performed:
- Known limitations / blockers:
- Secrets: confirm no secrets committed
- Next recommended milestone:
- Handoff summary for next model:

不得写入 API Key、Neo4j password、GitHub token、私密录音内容、私人记录全文或用户本机敏感路径。

## 最近一次交接

- 2026-11-19：用户明确选择先创建 AuraDB Free，再进行 M0 smoke test。Claude Code 已确认目前没有修改代码、没有创建分支、没有推进任何里程碑。跨窗口总览见 [docs/workspace-handoff.md](workspace-handoff.md)；HTML 维护进度单独记录在 [docs/html-maintenance-progress.md](html-maintenance-progress.md)。

当前还没有 Phase 1 代码实现提交。Phase 1 计划、Claude Code Prompt、通用 Agent 规则和本进度文件已提交到 main。下一位执行模型应先读取：

1. AGENTS.md
2. CLAUDE.md（若使用 Claude Code）
3. docs/phase1-progress.md（本文件）
4. docs/phase1-implementation-plan.md
5. docs/phase1-operating-model.md
6. docs/codex-phase1-implementation-prompt.md（技术细节参考）
7. docs/rules-status.md、docs/reference-research-plan.md

首次执行前检查本地 git status，不得覆盖用户已有改动。

## 2026-11-20 — M1 ChatGPT 第二轮审核交接

- Milestone: M1 — Python project skeleton, configuration, logging, and basic CLI
- Status: awaiting_chatgpt_review
- Branch: `phase1/m1-python-skeleton`
- Draft PR: https://github.com/symbi/liuyao-learning-app/pull/2
- M0 status: completed / actual AuraDB Free validation completed before M1; no independent M0 PR or merge commit is claimed
- M0 evidence: AuraDB Free / Neo4j `5.27-aura`; GCP Singapore; enterprise edition as reported by `dbms.components()`; Python `3.12.13`; neo4j driver `6.4.1`; Vector Index creation, ONLINE, query, and deletion passed; dimensions `128, 256, 384, 768, 1024, 1536, 3072` passed; `SEARCH` and direct `$vec` passed on the measured instance. The original report remains outside the repository.
- Implementation summary: the existing M1 skeleton remains in place. URI userinfo is rejected by the Neo4j validator for all accepted schemes, Pydantic validation hides URI inputs, `ConnectionProfile` stores only safe URI data, and doctor treats missing Gemini as skipped rather than a failure.
- Configuration precedence: OS environment variables > `~/.config/liuyao-kb/m0.env` and optional local env files > defaults. Credentials remain outside the repository.
- Test isolation: Neo4j doctor tests mock the driver; CLI tests use a temporary config directory and never open AuraDB.
- Tests: `.venv/bin/python -m pytest -q` — 72 passed; `.venv/bin/python -m pytest` — 72 passed in 0.86s.
- Lint: `.venv/bin/python -m ruff check .` — passed.
- Format: `.venv/bin/python -m ruff format --check .` — passed.
- Types: `.venv/bin/python -m mypy` — passed with no issues in 8 source files.
- Manual/security checks: `git diff --check` passed; no secret-like env file is tracked; only `.env.example` is tracked; no actual credentials or private `.env` values were copied into the repository or progress file.
- Known limitations: M1 remains a scaffold; ingestion, embeddings, LLM extraction, GraphRAG, and evidence retrieval remain for later milestones.
- Next step: resolve review comments only, update PR #2, and request another ChatGPT review. Do not merge or start M2.
