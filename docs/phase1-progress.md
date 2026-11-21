# Phase 1 进度与跨模型交接记录

> 本文件是 Claude Code、Codex、ChatGPT 或其他模型之间的持久化项目记忆。切换模型时，以 GitHub 当前 main 分支中的本文件和引用文档为准，不依赖旧聊天窗口的记忆。

## 当前状态

- Project: symbi/liuyao-learning-app
- Phase: Phase 1 — Neo4j Knowledge Base + Incremental Importer + Evidence Pack
- Status: in_progress
- Current milestone: M2-A — Common Models and Source Provenance
- Phase 1 plan baseline commit: f5869ad643c94760e72e77f0bc3d747fa3b38652
- Implementation code status: M1 approved_merged; M2-A implementation in progress
- Active implementation branch: phase1/m2-source-adapters
- Active PR: none yet
- Last completed milestone: M1
- Next action: 等待 M2-A 最终审核；M2-B 尚未开始
- Latest M2 implementation commit: 3b89bbc
- Active M2 PR: none
- Last updated: 2026-11-21

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
| M1 | Python 项目骨架、配置、CLI、日志、doctor、sources list、dry-run | approved_merged | [PR #2](https://github.com/symbi/liuyao-learning-app/pull/2) / `df7bc3fe0a568dc89fe9875d87e653d9eca026fb` | 2026-11-20 已合并；M1 代码审查通过 |
| M2 | Markdown/TXT/PDF/JSON Source Adapters | in_progress | No Draft PR | M2-A common models/provenance implemented on `phase1/m2-source-adapters`; awaiting ChatGPT review of commit `3b89bbc`; M2-B not started; daily JSON excluded from classroom-case ingestion |
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

- **历史记录（2026-11-19）：** 当时用户明确选择先创建 AuraDB Free，再进行 M0 smoke test。Claude Code 记录当时没有修改代码、没有创建分支、没有推进任何里程碑；这是旧状态快照，不是 2026-11-20 的当前状态。跨窗口总览见 [docs/workspace-handoff.md](workspace-handoff.md)；HTML 维护进度单独记录在 [docs/html-maintenance-progress.md](html-maintenance-progress.md)。

截至 2026-11-20，M1 已通过审核并合并到 main（PR #2；merge commit `df7bc3fe0a568dc89fe9875d87e653d9eca026fb`）。以上旧交接记录仅保留作历史背景。下一位执行模型应先读取：

1. AGENTS.md
2. CLAUDE.md（若使用 Claude Code）
3. docs/phase1-progress.md（本文件）
4. docs/phase1-implementation-plan.md
5. docs/phase1-operating-model.md
6. docs/codex-phase1-implementation-prompt.md（技术细节参考）
7. docs/rules-status.md、docs/reference-research-plan.md

首次执行前检查本地 `git status`，不得覆盖用户已有改动。M2 已是下一项待启动工作；只有在读取本文件和实施计划、确认工作区状态后，才可开始 M2。

## 2026-11-20 — 历史记录：M1 ChatGPT 第二轮审核交接

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
- Next step: resolve review comments only, update PR #2, and request another ChatGPT review.

## 2026-11-20 — M1 第三轮小修与最终审核准备

- Milestone: M1 — Python project skeleton and review fixes
- Status: awaiting_chatgpt_review
- Branch: `phase1/m1-python-skeleton`
- Draft PR: https://github.com/symbi/liuyao-learning-app/pull/2
- Latest reviewed checkpoint before this pass: `5d0e8e8`
- Third-round implementation commit: `ceea60b`
- Small fixes: expanded `*.env` ignore coverage; strengthened quoted/space redaction tests; corrected README links and doctor credential guidance; qualified M0-only driver observations; clarified instance-ID documentation; marked old 2026-11-19 handoff as historical.
- Branch synchronization: rebased onto latest `origin/main` after fetching without resetting or overwriting the daily-record commit.
- Secrets: no real credentials were read, printed, or committed; TLS certificate verification remains enabled.
- Tests: `.venv/bin/python -m pytest` — 74 passed in 0.59s.
- Lint: `.venv/bin/python -m ruff check .` — passed.
- Format: `.venv/bin/python -m ruff format --check .` — passed; 13 files already formatted.
- Types: `.venv/bin/python -m mypy` — passed with no issues in 8 source files.
- Gitignore: `m0.env`, `local.env`, `production.env`, `.env`, and `.env.local` matched ignore rules; `.env.example` and `sources.example.yaml` remained tracked.
- Final pre-confirmation fixes: clarified M0-only username/database naming, made m0.env 初始化非破坏性, relabeled second-round history, and added unterminated env quote rejection with variable-name/line-only warnings.
- Final verification: 75 tests passed; Ruff check passed; Ruff format check passed; Mypy passed; `git diff --check` passed.
- Next step: update PR #2 and wait for ChatGPT final approval. Do not merge or start M2.


## 2026-11-20 — M1 合并完成与 M2 跨模型交接

- Milestone: M1 — Python project skeleton, configuration, logging, and basic CLI
- Status: approved_merged
- PR: https://github.com/symbi/liuyao-learning-app/pull/2
- Branch: `phase1/m1-python-skeleton`
- Reviewed implementation head: `48edf7ccd4b07c7635bc9d398d9da79a8240b408`
- Merge commit on main: `df7bc3fe0a568dc89fe9875d87e653d9eca026fb`
- Merge verified: PR #2 state closed, merged=true; main points to the merge commit at the time of this update.
- Final review: ChatGPT code review found no blocking issue. Local test report from the VS Code Agent: 75 pytest tests passed; Ruff check, Ruff format check, Mypy, and `git diff --check` passed. ChatGPT inspected GitHub code but did not independently rerun those local commands.
- M1 code and tests are merged. Do not reopen M1 unless a concrete defect is found.

### Next milestone: M2 — Source Adapters

- Status: not_started
- Suggested branch: `phase1/m2-source-adapters`
- Base: latest `origin/main`; do not assume a stale local checkout is current.
- Scope: implement source parsing/adapters for curated Markdown lesson notes, TXT text, selected PDF files, and structured classroom-case JSON. The adapters should produce a consistent, source-aware parsed-document representation with provenance such as source type, repository-relative path/source URI, stable source identity where available, heading/paragraph or page location, and the original structured case fields required by the schema.
- Before implementation, inspect actual existing lesson Markdown, relevant TXT examples, PDF handling requirements, and current HTML/classroom-case JSON schema in the repositories. Use small synthetic fixtures for tests; do not expose private raw ASR or personal records in fixtures.
- M2 does not include Neo4j schema/writes, Embedding, Gemini calls, generative LLM extraction, incremental synchronization, Evidence Pack, Cloud Run, or changes to the deployed HTML app. Those belong to later milestones or separate workstreams.
- PDF real-world sample acceptance can be deferred until the adapter and fixture tests exist; do not block initial implementation waiting for a real PDF.
- Expected result: adapters preserve source provenance and content faithfully; tests cover parser behavior, page/heading locations, malformed/unsupported inputs, and structured JSON field preservation. Do not silently discard unparseable content.
- At completion: run tests/lint/type checks, inspect diff and secret scan, update this progress file with exact commands/results, push the M2 branch, and open a Draft PR. Stop for ChatGPT review; do not merge or begin M3.

### M2-A checkpoint (2026-11-21)

- Status: implementation_complete_pending_checkpoint
- Branch: `phase1/m2-source-adapters`
- Implemented: common ParsedDocument/ParsedSection models, type-specific locators, source identity/URI helpers, SHA-256 helpers, revision_ref and parser_version.
- Privacy: no Neo4j, Gemini, Raw ASR, dailyMemo, or HTML behavior.
- Tests: source models plus source config passed (24 tests); focused Ruff check and format check passed.
- Next: commit/push M2-A, then begin M2-B Markdown/TXT adapters.

### Cross-model execution protocol

1. Any available VS Code Agent/model, Claude Code, Codex, or other coding agent may execute the task. Model identity and quota do not define project state.
2. Before starting, read `AGENTS.md`, `docs/workspace-handoff.md`, this file, `docs/phase1-implementation-plan.md`, and `docs/phase1-operating-model.md`. Read `CLAUDE.md` only when using Claude Code; other agent-specific prompts are optional references.
3. Inspect `git status --short --branch`, current branch, latest `origin/main`, and local changes. Never reset, clean, stash, overwrite, or discard uncommitted user work without explicit permission.
4. Work on one milestone branch only. Commit and push small checkpoints regularly. A checkpoint report must include the branch, commit SHA, completed work, exact tests/results, known limitations, and next action. Update this file before handoff.
5. If an agent hits quota or must stop, it must stop safely at a checkpoint: save working changes, run applicable checks, commit on the existing milestone branch when safe, push the branch, and update this file. If it cannot push, record the exact local branch/commit and unfinished changes; never claim they are backed up on GitHub.
6. The replacement model must first inspect GitHub and local Git state. It must continue the same M2 branch and inspect existing diffs before editing; it must not recreate completed work or start a second competing branch.
7. No model may merge the Draft PR, approve its own work, or begin M3. ChatGPT reviews the PR; the user controls merge authorization.

Secrets, credentials, private audio/transcripts, and personal records must never be copied into this progress file.

### M2-A final pre-review fix (2026-11-21)

- Status: in_progress / awaiting ChatGPT review
- Branch: `phase1/m2-source-adapters`
- Implementation checkpoint: `3b89bbc`
- Earlier M2-A review fixes: `1372db6` and `9d12245`.
- Metadata fix: `Field(default_factory=dict, validate_default=True)` validates and deep-freezes default empty metadata.
- Default metadata test: omission, immutable assignment, `model_dump()`, `model_dump(mode="json")`, and `model_dump_json()` pass.
- M2-A model: source identity/URI, SHA-256, revision/ref locator, parser version, JSON-compatible deep metadata, and RFC 6901 JSON Pointer support.
- Actual verification:
  - `.venv/bin/python -m pytest tests/test_source_models.py -q` — 31 passed.
  - `.venv/bin/python -m pytest -q` — 106 passed.
  - `.venv/bin/python -m pytest` — 106 passed in 0.68s.
  - `.venv/bin/python -m ruff check .` — passed.
  - `.venv/bin/python -m ruff format --check .` — passed; 15 files already formatted.
  - `.venv/bin/python -m mypy` — passed; no issues in 9 source files.
  - `git diff --check` — passed.
- No Draft PR exists. M2-B has not started.
- M2-B identity requirement: source identity must include repository/source namespace so `docs/lesson-05.md` in two repositories remains distinct. M2-A does not need large restructuring now; this requirement will be implemented and tested in M2-B.