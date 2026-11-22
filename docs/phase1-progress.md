# Phase 1 进度与跨模型交接记录

> 本文件是 Claude Code、Codex、ChatGPT 或其他模型之间的持久化项目记忆。切换模型时，以 GitHub 当前 main 分支中的本文件和引用文档为准，不依赖旧聊天窗口的记忆。

## 当前状态

- Project: symbi/liuyao-learning-app
- Phase: Phase 1 — Neo4j Knowledge Base + Incremental Importer + Evidence Pack
- Status: in_progress
- Current milestone: M2 — Source Adapters（M2-A/M2-B 已合并；M2-C 已按真实文件拆为 C1/C2/C3，当前为规划更新阶段 PR #5，实现待用户授权；PDF Adapter/OCR 已暂缓）
- Phase 1 plan baseline commit: f5869ad643c94760e72e77f0bc3d747fa3b38652
- Implementation code status: M1 approved_merged; M2-A/M2-B approved_merged（PR #3，merge commit `9505ce70e38b729bfb4d7dd36924a25229389194`）; M2 整体 in_progress（剩 M2-C）
- Active implementation branch: none（M2-C 尚未启动）；规划分支 `phase1/m2c-planning`（PR #5，仅文档）
- Active PR: Draft PR #5（M2-C 规划更新：案例资料分类、C1/C2/C3 拆分、课堂案例身份原则与数据模型修订；仅文档）
- Last completed milestone: M2-A/M2-B（经 PR #3 合并）；M1 已合并
- Next action: ChatGPT 审查 PR #5，用户决定是否合并；之后由用户明确授权才启动 M2-C1 实现。不开发 PDF Adapter/OCR；外部资料经独立仓库 Source Collector 输出 Reference Package 后再由本仓库接收
- Latest M2 implementation commit: 38b4e09（PR #3 分支 head `e09ae71` 已合并）
- Merged M2 PR: https://github.com/symbi/liuyao-learning-app/pull/3（merge commit `9505ce7`）
- Last updated: 2026-11-22

## 已冻结的架构决定

1. Neo4j AuraDB Free 是 Phase 1 的云端知识图谱主数据库；Neo4j Desktop 可选用于本地学习，但不建立两份不同步的主库。
2. Phase 1 的 Importer 和 Query Tool 运行在用户 Mac；Python virtualenv 即可，不用 Docker。
3. Phase 1 不部署 Cloud Run Backend，不接 Supabase/PostgreSQL，不做 HTML 一键分析。
4. Phase 2 才把 Query / Evidence Pack / Rule Engine / LLM Orchestrator 整合为 Cloud Run FastAPI 服务；继续使用同一个 AuraDB，不重新导入。
5. Source A Raw：Private raw 中的录音和低准确率 ASR 默认只登记来源/版本，不进入主要 Chunk、Embedding 或规则抽取。
6. Source B Curated：Learning 中经过 ChatGPT 整理的课堂笔记，是主要课程 Chunk 来源。
7. 外部 GitHub README/docs 等外部参考资料进入外部参考轨道；保留 URL、版本、License，不与课程来源混淆。源码按文件/类/函数边界处理，属于后续子阶段。外部资料统一经独立仓库 Source Collector 采集并输出 Reference Package 后再导入（见决定 13）。PDF 已暂缓：当前没有明确准备导入的 PDF 文件，不为 PDF 增加开发依赖；将来选定具体 PDF 后再单独评估（2026-11-21 决定，取代早期“用户明确选择的 PDF 可进入参考轨道”的表述）。
8. Chunk 之后并行执行 Embedding 和 Generative LLM 候选知识抽取。Generative LLM 是大语言模型；抽取结果永远是 candidate，不自动成为老师确认规则。
9. Neo4j 保存 Document、Revision、Chunk、Case、Concept、RuleCandidate、关系和向量。同步 Manifest 放在 Neo4j，不另建 SQLite 数据库。
10. HTML 的每日 JSON 继续由现有 Cloudflare Pages Functions 保存到 GitHub；Phase 1 Importer 另行增量同步，不做浏览器实时双写。
11. Phase 1 Query Tool 从 AuraDB 检索并输出带出处的 Evidence Pack；最终报告由 ChatGPT Web 完成，用户手动交接。
12. 用户不需要逐条审核节点；系统自动保留来源、课程、页码/段落、版本、模型和不确定性。
13. 系统拆分为两个独立 Repository（2026-11-21 决定）：`symbi/liuyao-source-collector`（独立新仓库，由单独窗口负责；远端尚未创建）负责外部古籍网站/GitHub 资料的合规采集并输出标准化 Reference Package；本仓库 `symbi/liuyao-learning-app` 负责课程 Markdown/TXT、课堂案例 JSON、Reference Package 的接收与验证、解析、Chunk、Embedding、Neo4j 与 Evidence Pack。两边只通过 Reference Package 文件交接；本仓库不实现爬虫或网站采集器。来源登记见 [reference-source-catalog.md](reference-source-catalog.md)。（状态更新 2026-11-22：`symbi/liuyao-source-collector` 已创建且为 Private，由独立窗口维护；本仓库只记录这一事实，不接管其工作。）
14. 课堂案例身份原则（2026-11-22 决定）：课堂案例是老师在实际课程中讲解过的教学案例（classroom_case），不是用户个人练习数据，不得归类为 personal_practice。每个课堂案例保留稳定案例 ID，并尽可能连接老师 ASR/录音讲解位置、课程整理笔记、用户核对的卦盘结构、HTML JSON 记录及其 MD 表达、人工分析资料；课程笔记/ASR 对同一案例的提及建立引用关系并保留定位。同一案例的 JSON 与 MD 是同一案例的两种表示，不产生重复 Case 节点或重复计数。ClassCase 与 CastRecord 保留独立身份和唯一 ID，仅当 `dailyRecord.recordId` 明确匹配时建立 BASED_ON_RECORD；自动生成 MD 以 RENDERS 关联 CastRecord；人工分析 MD 以 ANALYZES_CASE 关联 ClassCase。老师原话、用户补充、AI 推算必须分开标记；ASR 未经音频校正时保留低置信度说明。

## 里程碑状态

| Milestone | 目标 | 状态 | Review PR / Merge commit | 备注 |
|---|---|---|---|---|
| M0 | 创建 AuraDB Free、保存本地凭据、连接与 Vector Index smoke test | completed | — | 用户环境验收完成；原始报告保留在用户本地，不虚构独立 PR 或 merge commit |
| M1 | Python 项目骨架、配置、CLI、日志、doctor、sources list、dry-run | approved_merged | [PR #2](https://github.com/symbi/liuyao-learning-app/pull/2) / `df7bc3fe0a568dc89fe9875d87e653d9eca026fb` | 2026-11-20 已合并；M1 代码审查通过 |
| M2 | Markdown/TXT/JSON Source Adapters（PDF 已暂缓，不属于当前 M2） | in_progress | [PR #3](https://github.com/symbi/liuyao-learning-app/pull/3) / merge commit `9505ce7`；M2-C 规划 [PR #5](https://github.com/symbi/liuyao-learning-app/pull/5) | M2-A/M2-B 已合并；M2-C 按真实文件拆为 C1（案例 JSON Mapping）、C2（自动生成 MD 伴随文件）、C3（人工分析 MD 关系），规划见 PR #5，实现待用户授权；每日记录默认不全量导入，只有显式允许的记录 ID 才进入 |
| M3 | Neo4j Schema、唯一约束、Vector Index、稳定 IDs | not_started | — | 真实 AuraDB smoke test |
| M4 | 增量 Importer、Hash、Revision、Chunker、MERGE | not_started | — | 第二次相同导入不能触发模型调用 |
| M5 | Gemini Embedding + Generative LLM 双路径 | not_started | — | 先确认模型、维度、数据条款 |
| M6 | 经 Source Catalog 批准、由 Source Collector 输出 Reference Package 的外部文档与代码参考 | not_started | — | 用户先确认来源与 License；本仓库不直接爬取网站；PDF 不在当前范围 |
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

> **Superseded / 历史 checkpoint：** 本节是 M2-A 的早期快照，已被本文件后面的
> 《M2-A final pre-review fix (2026-11-21)》和《M2-A 审查通过与 M2-B 启动
> (2026-11-21)》取代。本节中的 Status 与 “Next: commit/push M2-A, then begin
> M2-B” 是当时的状态与计划，不是当前事实；当前事实以本文件顶部「当前状态」
> 和最新交接记录为准，请勿按本节判断进度。

- Status: implementation_complete_pending_checkpoint（历史值，见上方说明）
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

### M2-A 审查通过与 M2-B 启动 (2026-11-21)

- Status: in_progress
- Branch: `phase1/m2-source-adapters`
- M2-A: 已通过 ChatGPT 代码审查。最近提交：`3b89bbc`（默认 metadata 验证和深度冻结修复）、`d4d55fb`（进度文档更新）。
- 整体 M2: in_progress，未合并，没有 Draft PR。
- 历史状态处理：较早的《M2-A checkpoint (2026-11-21)》已明确标记为 superseded / 历史 checkpoint；其“准备开始 M2-B”是当时的计划记录，不再与最新状态冲突。
- M2-B: 准备开始。本阶段只做 Markdown/TXT Adapters，使用 M2-A 的 ParsedDocument、ParsedSection 和 Locator 模型；source_uri 必须包含稳定 source namespace（例如 `repo://symbi/liuyao-learning-app/docs/lessons/lesson-05.md`），不同 repository 的相同相对路径必须得到不同 source_identity；revision_ref 与 source identity 分离。
- M2-B 完成后：更新本文件、创建 Draft PR（目标 main），等待 ChatGPT 审核；不合并、不开始 M2 后续阶段（PDF/JSON）。

### M2-B checkpoint (2026-11-21) — Markdown/TXT Adapters

- Milestone: M2-B — Markdown/TXT Source Adapters（M2 整体仍为 in_progress）
- Status: awaiting_chatgpt_review
- Branch: `phase1/m2-source-adapters`
- Draft PR URL: https://github.com/symbi/liuyao-learning-app/pull/3
- Base main SHA: `eefa2b23786db88c5535612695b3f08d361b0b18`（本分支起点；main 未被修改）
- Implementation commits: `db20421`（docs: 标记旧 M2-A checkpoint 为 superseded 并同步当前状态）、`dc222bd`（feat: Markdown/TXT adapters）
- Files changed:
  - `tools/liuyao-kb/src/liuyao_kb/sources/adapters.py`（新增：MarkdownAdapter、TextAdapter、EmptySourceError、InvalidSourceEncodingError）
  - `tools/liuyao-kb/src/liuyao_kb/sources/models.py`（仅新增：`repository_source_uri`、`source_identity_from_repository` 及校验；M2-A 模型未重构）
  - `tools/liuyao-kb/src/liuyao_kb/sources/__init__.py`（导出）
  - `tools/liuyao-kb/tests/test_source_adapters.py`（新增 31 个测试，全部使用 synthetic fixtures）
  - `docs/phase1-progress.md`（本文件）
- 实现要点:
  - 统一 URI 约定 `repo://<owner>/<repo>/<relative-path>`；source_identity 为 `<source_type>:<source_uri>`，因此两个 repository 中相同相对路径的 identity 不同（有测试证明，包括从两个不同本地 checkout 目录用 `parse_file` 读取的情形）。机器绝对路径和临时目录名不写入 source_uri / source_identity；绝对路径 URI 被显式拒绝。`revision_ref` 只记录 Git commit / 来源版本，与 identity 分离（有测试证明）。
  - 原始文本逐字保留；content_hash 为原始 UTF-8 bytes 的 SHA-256；每个 section 满足 `text[start_offset:end_offset] == section.text`（测试逐 section 验证）。
  - Markdown：ATX heading 保留层级与文本；正文段落记录所属（最近）heading、全局 1-based paragraph 序号和 offset；文档 title 取第一个 H1；fenced code block 逐字保留，内部不识别 heading、空行不分段。
  - TXT：段落保留全局 1-based paragraph 序号和 offset。
  - 空文件 / 只有空白字符显式抛 `EmptySourceError`；无效 UTF-8 显式抛 `InvalidSourceEncodingError`（含 byte offset）；错误输入类型抛 `TypeError`；不静默丢失空白段落之外的有效内容。
  - 不调用 Neo4j、Gemini 或任何外部服务；未做 PDF/JSON。
- Tests run (exact commands, in `tools/liuyao-kb`):
  - `.venv/bin/python -m pytest` — 137 passed in 0.70s（M2-B 前为 106，新增 31）
  - `.venv/bin/python -m pytest tests/test_source_adapters.py` — 31 passed
  - `.venv/bin/python -m ruff check .` — passed (All checks passed)
  - `.venv/bin/python -m ruff format --check .` — passed (17 files already formatted)
  - `.venv/bin/python -m mypy` — passed (no issues in 10 source files)
  - `git diff --check` — passed
- Manual checks performed: 每次推送前后核对远端分支 head 与本地记录一致；确认未触碰 HTML、Cloudflare Functions、daily-records 等其他工作流文件；Draft PR #3 已核对为 draft、head 为本分支、base 为 main。
- Known limitations / blockers:
  - Markdown 只支持 ATX heading；Setext heading 按普通段落文本保留。
  - paragraph 所属 heading 只记录最近的一个 heading（Locator 模型只有一个 heading 字段）。
  - 空 / 纯空白来源是显式错误，而不是零 section 的文档；后续 Importer 不得将其报告为导入成功。
  - 执行环境说明：本 checkpoint 由 Cooper 在其自有计算机上的该分支克隆中实现并运行全部测试，再通过 GitHub 推送到同一分支；用户 Mac 上的本地 checkout 未被改动，Mac 上复跑测试仍建议作为验收的一部分。
- Secrets: confirm no secrets committed — 未提交任何 .env、凭据、Raw ASR、私人 Memo 或真实课程内容；fixtures 均为小型合成字符串。
- Next recommended milestone: 无（等待审查）。ChatGPT 审查 Draft PR #3 通过后，由用户决定是否合并；不得自行开始 PDF/JSON 或其他 M2 后续阶段。
- Handoff summary for next model: M2-A 已审查通过；M2-B 已完成并进入 Draft PR #3 等待 ChatGPT 审查。接手者先读 AGENTS.md、本文件和 PR #3，不要创建第二个 M2 分支，不要合并，不要开始 PDF/JSON。

### M2-B 围栏修复 (2026-11-21) — 回应 PR #3 ChatGPT 审查

- Status: awaiting_chatgpt_review（复审）
- Branch: `phase1/m2-source-adapters`
- Draft PR URL: https://github.com/symbi/liuyao-learning-app/pull/3
- Review source: PR #3 评论 https://github.com/symbi/liuyao-learning-app/pull/3#issuecomment-7058611732（ChatGPT 首轮审查：整体通过，仅 fenced code block 关闭围栏识别一项必须修复，未批准合并）
- Fix commit: `38b4e09`（fix(m2): validate Markdown closing fences by char, length and trailing text）
- 问题：旧逻辑只保存围栏字符、不保存长度，且对关闭行不检查尾随文字；四反引号代码块内的三反引号行或 ` ```python ` 行会被误判为关闭围栏，其后的 `# ...` 代码行被误识别为 Markdown 标题，污染标题归属和段落定位。
- 修复（只改 `tools/liuyao-kb/src/liuyao_kb/sources/adapters.py` 的围栏识别，未引入完整 CommonMark 解析器，未改动其他逻辑）:
  1. 开启围栏同时记录字符和长度（`fence_char` + `fence_length`）。
  2. 关闭围栏必须与开启字符相同，且长度不小于开启长度。
  3. 关闭围栏后只能有空格或 Tab；带 `python` 等 info text 的围栏形行只是代码内容。
  4. 开启和关闭围栏都遵守最多三个前导空格：围栏行按原始行匹配 `^ {0,3}`，四个前导空格的行不是围栏（开启侧按普通段落处理，关闭侧按代码内容处理）。
  5. 补充 CommonMark 一致性细节：反引号围栏的 info string 若含反引号则不构成开启围栏。
- 回归测试（`tools/liuyao-kb/tests/test_source_adapters.py` 新增 `TestMarkdownFences`，7 个测试）:
  - 较短围栏：审查复现原文（四反引号块内含 ` ```python ` 和 `# 这行仍是代码`）不再提前关闭、不再误判标题。
  - 带 info text 的非关闭行：等长 ` ```python ` 不关闭代码块。
  - 不同围栏字符：反引号块内的 `~~~` 行、波浪线块内的 ` ``` ` 行都不关闭。
  - 合法关闭围栏：更长的关闭围栏加尾随空格/Tab 可以关闭，其后的 `# 真标题` 恢复为真实标题。
  - 缩进规则：四空格缩进的围栏形行既不开启也不关闭；不超过三空格的围栏仍正常工作。
  - 所有新测试都逐 section 验证 locator offset 切片与原文一致，代码块内标题、空行和文本不丢失。
- Tests run (exact commands, in `tools/liuyao-kb`):
  - `.venv/bin/python -m pytest` — 144 passed in 1.44s（此前 137，新增 7）
  - `.venv/bin/python -m pytest tests/test_source_adapters.py` — 38 passed
  - `.venv/bin/python -m ruff check .` — passed (All checks passed)
  - `.venv/bin/python -m ruff format --check .` — passed (17 files already formatted)
  - `.venv/bin/python -m mypy` — passed (no issues in 10 source files)
  - `git diff --check` — passed
- Files changed: `tools/liuyao-kb/src/liuyao_kb/sources/adapters.py`、`tools/liuyao-kb/tests/test_source_adapters.py`、`docs/phase1-progress.md`（本节）。未改动 PDF/JSON，未重构无关代码，未触碰其他工作流文件。
- Secrets: confirm no secrets committed — 无新增凭据或私人内容；测试仍全部使用 synthetic fixtures。
- Next step: 保持 Draft PR #3 为 Draft，等待 ChatGPT 复审；不合并，不开始 PDF/JSON。

## 2026-11-21 — PR #3 合并完成与 PR #4 同步记录

本节是当前最新状态，取代上文各 checkpoint 中关于“等待 PR #3 复审/不合并”的 Next step 表述；上文 M2-A/M2-B 的 checkpoint 记录原文保留，不作改写。

- Milestone: M2-A / M2-B 合并完成；PR #4 规划文档同步到新 main
- PR #3: https://github.com/symbi/liuyao-learning-app/pull/3 — **已合并**（closed, merged）
- PR #3 head at merge: `e09ae718230a2100156baa8a2f46379a68f7b089`
- Merge method: Merge Commit（与 PR #2 相同）
- Merge commit / 最新 main SHA: `9505ce70e38b729bfb4d7dd36924a25229389194`
- 验收依据: 用户明确豁免了手动在 Mac 复跑测试，接受以执行 Agent 的等价复跑作为本机验收依据。复跑前已逐文件核对远端 head `e09ae71` 的 5 个代码/测试文件与复跑环境内容逐字一致、工作区干净；复跑结果（`tools/liuyao-kb`，Python 3.12.3）：pytest **144 passed**、adapter tests **38 passed**、Ruff check 通过、Ruff format check 通过（17 files）、Mypy 通过（10 source files）、`git diff --check` 通过。合并前再次确认 PR 仍 open、head 未变、mergeable_state clean、无新的阻断性审查意见。注意：该复跑不是在用户 Mac 上执行的，这一事实已如实告知用户并由用户确认接受。
- PR #4 同步方式: PR #4（`phase1/reference-source-catalog`）与 PR #3 共同修改本文件。处理顺序为：先把本文件对齐到 main 的合并后版本，再由 GitHub 将 main 合并进 PR #4 分支（merge commit `428b9a7`），最后写入本节及顶部状态、冻结决定 7/13 与里程碑表的合成更新。结果：PR #3 的全部 M2-A/M2-B checkpoint 记录完整保留；PR #4 的 2026-11-21 双仓库架构决策与 PDF deferred 决定完整保留（冻结决定 7、13 与里程碑表）；没有任何一方内容被整文件覆盖。
- PR #4 当前状态: Draft、未合并；已同步到 main `9505ce7`；共 11 个文件；等待 ChatGPT 对新 head 做最终复审，用户再决定是否合并。
- Secrets: 未写入任何密钥、凭据或私人内容。
- Next step: 等待 ChatGPT 复审 PR #4 与用户决定；不启动 M2-C、不创建 Source Collector 仓库、不开发 PDF Adapter/OCR。

## 2026-11-21 — PR #4 再次同步 main 记录

- main 已前进：PR #3 合并后，main 新增第十九课课堂案例（`materials/class-cases/lesson-19/case-001.json` 与 `case-001-analysis.md`，提交 `a92bf4a`）及数次每日记录更新，同步时最新 main 为 `de7d884`。
- PR #4 分支已通过 GitHub merge commit `6f2c405` 合并最新 main：PR #3 的 M2-A/M2-B 代码与测试完整保留（adapters.py blob SHA 与此前核对一致），本 PR 的架构决策、来源目录与 Reference Package Schema 未被覆盖。
- `docs/phase1-implementation-plan.md` 第 4 节已按现状修正：课堂案例不再是“只有 README 约定”，并记录 M2-C 实施准备要求。本节之后的状态以本节为准。

## 2026-11-22 — PR #4 合并与 M2-C 规划更新（PR #5，docs-only）

- PR #4 已由用户合并：merge commit `65fb501f4dad5a380b41b1c304aafa47b4b685e3`。main 现已包含 Reference Source Catalog、Reference Package v1 Schema 与双仓库架构文档。ChatGPT 对 PR #4 最终 head `5b8e05b` 的复审为 PASS（PR 评论 #issuecomment-7064313428）。
- `symbi/liuyao-source-collector` 已创建且为 Private（独立窗口维护）；此前文档中“尚未创建”的表述已在本 PR 修正。
- 本 PR（#5，分支 `phase1/m2c-planning`）只更新规划文档，不改任何 Python 实现代码，不改真实案例/每日记录文件。内容：
  - 按 main 真实文件区分四种案例相关资料：课程案例 JSON（case-001，`recordType=class-case`，案例 ID `L19-C01-work-transfer`，经 `dailyRecord.recordId` 关联每日记录子记录 `9f89c47a-...`）、人工分析 MD（case-001-analysis.md）、HTML 每日记录 JSON 容器（`additionalQuestions[]` 子记录各有独立 ID；容器本身不是 Case）、自动生成记录 MD（对应子记录 `7e0a6b19-...`，是呈现形式而非第二个案例；与 `9f89...` 是不同记录）。
  - M2-C 拆为 C1/C2/C3（见实施计划第 12 节）；`isCase`/`caseSource` 只能用于分类，不能单独作为案例匹配或验证依据（2026-11-21 每日记录中两个子记录都带这两个标记，但只有一条被 case-001 显式关联）。
  - 确立课堂案例身份原则（冻结决定 14）：课堂案例是老师讲解过的教学案例，不是个人练习；同一案例的 JSON 与 MD 是同一案例的两种表示，不重复建节点或计数；ClassCase 与 CastRecord 独立身份、独立 ID，仅在 `dailyRecord.recordId` 明确匹配时建 BASED_ON_RECORD，自动生成 MD 用 RENDERS 关联 CastRecord，人工分析 MD 用 ANALYZES_CASE 关联 ClassCase。
- M2-C1/C2/C3 均未启动实现；等待 ChatGPT 审查本 PR、用户合并决定与后续明确授权。
