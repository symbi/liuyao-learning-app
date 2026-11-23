# Phase 1 进度与跨模型交接记录

> 本文件是 Claude Code、Codex、ChatGPT 或其他模型之间的持久化项目记忆。切换模型时，以 GitHub 当前 main 分支中的本文件和引用文档为准，不依赖旧聊天窗口的记忆。

## 当前状态

- Project: symbi/liuyao-learning-app
- Phase: Phase 1 — Neo4j Knowledge Base + Incremental Importer + Evidence Pack
- Status: in_progress
- Current milestone: M2 — Source Adapters（M2-A/M2-B 已合并；M2-C 规划 PR #6 已合并；M2-C1 已合并（PR #7，merge commit `51a0476da6b8986e44fbe0d6fa0a5779cf5dbad2`）；M2-C2 已合并（PR #8，merge commit `e963bf3f378cb3787a8ce27bb121eed193c7c3a5`）；M2-C3 进行中（本分支，Draft PR 待创建）；PDF Adapter/OCR 已暂缓）
- Phase 1 plan baseline commit: f5869ad643c94760e72e77f0bc3d747fa3b38652
- Implementation code status: M1 approved_merged; M2-A/M2-B approved_merged（PR #3，merge commit `9505ce70e38b729bfb4d7dd36924a25229389194`）; M2-C1 approved_merged（PR #7，merge commit `51a0476da6b8986e44fbe0d6fa0a5779cf5dbad2`）; M2-C2 approved_merged（PR #8，merge commit `e963bf3f378cb3787a8ce27bb121eed193c7c3a5`）; M2 整体 in_progress（剩 M2-C3）
- Active implementation branch: `phase1/m2c3-classroom-case-markdown-adapter`（M2-C3，基于最新 main `e963bf3` 创建，Draft PR 待创建）
- Active PR: M2-C3 Draft PR（本分支，待创建）；PR #8（M2-C2）已合并，merge commit `e963bf3f378cb3787a8ce27bb121eed193c7c3a5`；PR #7（M2-C1）已合并，merge commit `51a0476da6b8986e44fbe0d6fa0a5779cf5dbad2`；PR #6 已合并，merge commit `dbc2c19d9bd6bca509c7db1e5e83d478871c35e4`
- Last completed milestone: M2-C2（经 PR #8 合并，merge commit `e963bf3f378cb3787a8ce27bb121eed193c7c3a5`）；M2-C1 已合并（PR #7）；M2-A/M2-B 已合并（PR #3）；M1 已合并
- Next action: M2-C3（课堂案例 MD 表示解析）已在本分支实现，等待以 Draft PR 提交后由 ChatGPT 复审和用户决定合并；M3 不得顺手启动。第一轮路线（用户 2026-11-23 决定）：先用现有课程笔记、课堂案例与每日记录完成 M2-C、M3、M4、M5、M7、M8 的端到端验收，M6 外部参考资料延期到现有知识验收之后，不作为第一轮验收前置条件（M6 不取消）。不开发 PDF Adapter/OCR；外部资料经独立仓库 Source Collector 输出 Reference Package 后再由本仓库接收
- Latest M2 implementation commit: 38b4e09（PR #3 分支 head `e09ae71` 已合并）
- Merged M2 PR: https://github.com/symbi/liuyao-learning-app/pull/3（merge commit `9505ce7`）
- Last updated: 2026-11-23

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
14. 课堂案例身份原则（2026-11-22 决定）：课堂案例是老师在实际课程中讲解过的教学案例（classroom_case），不是用户个人练习数据，不得归类为 personal_practice。每个课堂案例保留稳定案例 ID，并尽可能连接老师 ASR/录音讲解位置、课程整理笔记、用户核对的卦盘结构、HTML JSON 记录、与案例 JSON 配对的 MD 表示；课程笔记/ASR 对同一案例的提及建立引用关系并保留定位。同一案例的 JSON 与 MD 是同一案例的两种表示，不产生重复 Case 节点或重复计数。ClassCase 与 CastRecord 保留独立身份和唯一 ID，仅当 `dailyRecord.recordId` 明确匹配时建立 BASED_ON_RECORD；案例 JSON 与课堂案例 MD 以 HAS_REPRESENTATION 关联到同一个 ClassCase（MD 不是独立分析来源）；daily-records 的自动生成 MD 以 RENDERS 关联 CastRecord，与课堂案例 MD 分属两类。老师 ASR 的来源定位不依赖 Chunk：ClassCase 可直接关联 ASR 的 SourceDocument/DocumentRevision，保留 Locator（仓库/路径、课程、段落序号、可选时间范围）与置信度/校正状态；不得为建引用而把全部 Raw ASR 自动 Chunk/Embedding。老师讲解、用户补充、AI 推算必须分开标记；ASR 未经音频校正时保留低置信度说明，不得称为已验证的逐字原话。（设计修正 2026-11-22：JSON 与配对 MD 是同一 ClassCase 的两份不同资料，不要求内容一致；C1 只识别 MD 的路径/存在/关联，C3 解析正文；链接只登记不抓取；内容冲突保留双源并标记待核对。详见 M2-C1 checkpoint。）

## 里程碑状态

| Milestone | 目标 | 状态 | Review PR / Merge commit | 备注 |
|---|---|---|---|---|
| M0 | 创建 AuraDB Free、保存本地凭据、连接与 Vector Index smoke test | completed | — | 用户环境验收完成；原始报告保留在用户本地，不虚构独立 PR 或 merge commit |
| M1 | Python 项目骨架、配置、CLI、日志、doctor、sources list、dry-run | approved_merged | [PR #2](https://github.com/symbi/liuyao-learning-app/pull/2) / `df7bc3fe0a568dc89fe9875d87e653d9eca026fb` | 2026-11-20 已合并；M1 代码审查通过 |
| M2 | Markdown/TXT/JSON Source Adapters（PDF 已暂缓，不属于当前 M2） | in_progress | [PR #3](https://github.com/symbi/liuyao-learning-app/pull/3) / merge commit `9505ce7`；M2-C 规划 [PR #6](https://github.com/symbi/liuyao-learning-app/pull/6) / merge commit `dbc2c19` | M2-A/M2-B 已合并；M2-C 拆为 C1（案例 JSON Mapping）、C2（自动生成 MD 伴随文件）、C3（课堂案例 MD 表示）；C1 已合并（PR #7，merge commit `51a0476`）；C2 已合并（PR #8，merge commit `e963bf3`）；C3 进行中（本分支，Draft PR 待创建）；每日记录默认不全量导入，只有显式允许的记录 ID 才进入 |
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

## 2026-11-22 — PR #4 合并与 M2-C 规划更新（PR #6，docs-only）

- PR #4 已由用户合并：merge commit `65fb501f4dad5a380b41b1c304aafa47b4b685e3`。main 现已包含 Reference Source Catalog、Reference Package v1 Schema 与双仓库架构文档。ChatGPT 对 PR #4 最终 head `5b8e05b` 的复审为 PASS（PR 评论 #issuecomment-7064313428）。
- `symbi/liuyao-source-collector` 已创建且为 Private（独立窗口维护）；此前文档中“尚未创建”的表述已在本 PR 修正。
- 本 PR（#6，分支 `phase1/m2c-planning`）只更新规划文档，不改任何 Python 实现代码，不改真实案例/每日记录文件。内容：
  - 按 main 真实文件区分四种案例相关资料：课程案例 JSON（case-001，`recordType=class-case`，案例 ID `L19-C01-work-transfer`，经 `dailyRecord.recordId` 关联每日记录子记录 `9f89c47a-...`）、课堂案例 MD 表示（case-001-analysis.md，与案例 JSON 同属一个 case_id）、HTML 每日记录 JSON 容器（`additionalQuestions[]` 子记录各有独立 ID；容器本身不是 Case）、自动生成记录 MD（对应子记录 `7e0a6b19-...`，是呈现形式而非第二个案例；与 `9f89...` 是不同记录）。
  - M2-C 拆为 C1/C2/C3（见实施计划第 12 节）；`isCase`/`caseSource` 只能用于分类，不能单独作为案例匹配或验证依据（2026-11-21 每日记录中两个子记录都带这两个标记，但只有一条被 case-001 显式关联）。
  - 确立课堂案例身份原则（冻结决定 14）：课堂案例是老师讲解过的教学案例，不是个人练习；同一案例的 JSON 与 MD 是同一案例的两种表示，不重复建节点或计数；ClassCase 与 CastRecord 独立身份、独立 ID，仅在 `dailyRecord.recordId` 明确匹配时建 BASED_ON_RECORD；案例 JSON 与课堂案例 MD 都是同一 ClassCase 的表示（HAS_REPRESENTATION），不另建案例；daily-records 的自动生成 MD 用 RENDERS 关联 CastRecord，与课堂案例 MD 不是同一类文件。老师 ASR 来源不依赖 Chunk：ClassCase 可直接关联 ASR 的 SourceDocument/DocumentRevision，关系上保留 Locator 与置信度/校正状态。
- M2-C1/C2/C3 均未启动实现；等待 ChatGPT 审查本 PR、用户合并决定与后续明确授权。
- 修订（2026-11-22，据 ChatGPT 审查意见）：（1）修正本节一处残留的 PR 编号（#5 → #6）；（2）课堂案例 MD 的身份关系修订——案例 JSON 与课堂案例 MD 都是同一个 ClassCase 的表示，关系由 ANALYZES_CASE 改为 HAS_REPRESENTATION，M2-C3 相应改名为“课堂案例 MD 表示”，并明确区分课堂案例 MD（A 类）与 daily-records 自动生成 MD（B 类，RENDERS 关联 CastRecord）；（3）ASR 来源定位落点明确——ClassCase 可直接关联 ASR 的 SourceDocument/DocumentRevision 并携带 Locator 与置信度，不以存在 Chunk 为前提，M7 Evidence Pack 须返回 ASR 定位与置信度。
- 收尾修订（2026-11-22，据 ChatGPT 收尾意见）：（1）实施计划第 4 节案例配对表述修正为“JSON 与课堂案例 MD 通过同一个稳定 `case_id` 配对；必要时辅以内容一致性校验”，全文排查无 case_id 与 dailyRecord.recordId 混用；（2）class-cases README 中残留的“分析稿”改为“课堂案例 MD 表示”；（3）实施计划第 11 节 Evidence Pack 明确 Raw ASR 三档返回规则——默认返回来源元数据（仓库/路径、DocumentRevision、Locator、置信度、音频校正状态），默认不返回正文与长篇摘录，仅当用户明确启用时才在独立低置信度区域返回正文并标注未经音频校正；Raw ASR 默认不进主要 Chunk/Embedding/规则抽取的原则不变；（4）清除实施计划页首等处尾随空格，并在工作目录实际运行 `git diff --check` 验证通过。
- 同步 main 与待核对样本（2026-11-22，据 ChatGPT 最终复审评论 #issuecomment-7075790808，设计审查已通过）：main 在本 PR 创建后前进两个提交——`0584a54`（2026-11-22 每日记录 JSON）与 `dd50d1f`（其生成 MD），已以 merge commit `96e49ce9633f2b42f99f2eaa4d0f20827f2c0edd` 合入本分支，两个每日记录文件经回读比对未被修改，本 PR 的五份文档未被合并覆盖。新增子记录 `13e9c29a-cdbc-41e0-912d-5e02fa7c54d3` 已从 main 回读核对：`recordType=additionalQuestion`、`isCase=true`、`caseSource=classroom`、生成 MD 标注“案例核对状态：待核对”，但无 case_id/lessonId/matchStatus、无课堂案例 JSON 关联——按冻结决定 14 只作待核对候选处理，不自动成为已验证 ClassCase；该样本已补入实施计划第 4 节作为真实反例。PR 保持 Draft，不合并、不启动 M2-C。
- 跨文档模型同步（2026-11-22，据用户复审）：此前 operating-model 第 3、4 节与实施计划第 8 节仍残留旧 Case 语义（以 recordId 作为案例身份、“更新同一个 Case”），与第 7 节模型冲突，本轮已统一：ClassCase 用 case_id、CastRecord 用 record_id，两者独立身份，仅 dailyRecord.recordId 明确匹配时建 BASED_ON_RECORD；课堂案例内容修改更新同一 ClassCase 的表示/revision，每日记录修改只更新对应 CastRecord、不创建或替换 ClassCase。class-cases README 同步明确：案例 JSON 与配对 MD 表达同一份案例内容、仅形式不同，内容应保持一致，MD 不是可额外增加分析内容的独立资料；独立扩展分析文档如将来需要另行定义。全文已复扫 recordId/record_id/case_id/Case 语义。
- 再次同步 main（2026-11-22）：main 前进 8 个提交至 `cf06eee0094602dd0bf02e2050d0921914468782`（2026-11-22 每日记录的多次更新保存，以及第十九课 case-002 的建立：分析稿、结构化图表与来源记录、与每日记录的显式关联、matched 标记），已以 merge commit `c112ba66ef3720b79cffe2691753a764659ba131` 合入本分支，无冲突；经逐文件比对，这 8 个提交未触及本 PR 的五份文档，合并后每日记录与 case-002 文件与 main 逐字节一致。此前待核对的子记录 `13e9c29a-...` 已被显式配对为 case-002（`L19-C02-shop-operation-transfer`，matchStatus=matched），实施计划第 4 节的样本已相应更新为完整的核对生命周期记录。PR 保持 Draft，不合并、不启动 M2-C。
- matchStatus 语义统一（2026-11-22，据最终复审）：回读 main 上全部真实课堂案例 JSON（仅 lesson-19 的 case-001、case-002 两个）后确认——case-001 的 `verified` 与 case-002 的 `matched` 是同一状态的两种历史写法（两者的 verificationBasis 均为 ASR 内容核对 + 用户提供卦盘 + 明确限定，证据结构相同），规范状态定为 `verified`，`matched` 作为历史别名由 M2-C Mapper 读取时归一化并保留原始值，未知值不得静默丢弃或误判；`verified` 不等于音频逐字验证。已同步 README 状态列表、实施计划第 4 节与第 12 节 M2-C1 要求；真实案例 JSON 未修改。另修正 operating-model 第 3 节输入列表的重复编号（两个“3.”），实施计划资料状态核对日期更新为 2026-11-22。
- 最终同步 main（2026-11-22）：main 前进 8 个提交至 `a306ffa70691a16d369ecb343c686123122efa25`，全部为 2026-11-22 每日记录的更新保存与新子记录 `d4f2ced4-a5de-459c-b0cd-82b5481660be` 生成 MD 的保存，未触及五份规划文档与 case-001/case-002；已以 merge commit `ab9c5f650cb349aaf5c6634062c8761fa67f0efd` 合入本分支，无冲突，main 已成为分支祖先（behind 0）。新子记录 d4f2ced4 同样只是待核对的 CastRecord 候选（isCase=true、caseSource=classroom、生成 MD 标注待核对、无课堂案例 JSON 关联），未自动建立 ClassCase。合并后每日记录 JSON 与生成 MD 与 main 逐字节一致，matchStatus 规范与双身份模型完整保留。PR 保持 Draft，不合并、不启动 M2-C。

## M2-C1 checkpoint (2026-11-22)

- PR #6（M2-C 规划更新）已由用户授权合并：merge commit `dbc2c19d9bd6bca509c7db1e5e83d478871c35e4`。本节之前各处“PR #6 Draft / 等待合并”的表述均为合并前的历史记录。
- 设计修正（2026-11-22，用户确认，取代此前“JSON 与配对 MD 表达同一份内容”的表述）：课堂案例 JSON 与配对 Markdown 是同一个 ClassCase 的**两份不同资料**，不是两份案例，也不要求内容一致；MD 可以包含自身的分析内容、来源链接与上下文。两者各自保留来源、路径与版本；内容冲突时保留各自来源、标记待核对、不静默合并；MD 中的链接只登记引用信息，不自动抓取目标文件；老师分析、用户 Memo、AI 分析保留各自来源身份，不能互相转化为老师确认内容。M2-C1 只识别 A 类配对 MD 的路径、存在状态与 case_id 关联（不解析正文）；M2-C3 负责解析 A 类 MD 正文；B 类 daily-records 自动生成 MD 继续按 CastRecord 的 RENDERS 呈现处理，两类 MD 不共用身份模型。已同步修订 implementation-plan 第 4、7 节、operating-model、class-cases README 与本文件决定 14 的适用说明。
- M2-C1 实现（本地分支 `phase1/m2c1-case-json-mapper`，从 main `dbc2c19` 创建；**尚未推送、尚未创建 PR**）：
  - 提交 `67be290`：新增 `tools/liuyao-kb/src/liuyao_kb/sources/case_json.py`（ClassCase/CastRecord 类型化映射、完整原始 JSON 冻结保留、dailyRecord `path`/`jsonPath` 双别名兼容且冲突报错、matchStatus 归一化、精确 recordId 关联、严格 JSON 解码）；`sources/config.py` 新增 fail-closed `allowed_records` 白名单（(容器路径, 子记录 ID) 精确条目，默认空，重复/冲突在配置层报错）；`sources/__init__.py` 导出；`sources.example.yaml` 补说明；新增 `tests/test_case_json.py`。
  - 提交 `150d7fb`：补全 A 类配对 MD 识别——`PairedMarkdownRef`（case_id 关联、预期仓库相对路径、canonical repo:// source URI 与 source identity、exists 三态：已查存在/已查缺失/未查为 None），路径只依据 JSON 文件自身路径与文件名推导（同目录 `<stem>-analysis.md`），文件缺失不使映射失败；bytes 级解析保持纯 JSON、不访问文件系统，识别只发生在文件级 Mapper / resolver 层；与 B 类 `dailyRecord.markdownPath` 严格区分。
  - 测试（执行环境：执行 Agent 本机 clone 的 venv，Python 3.12.3；非用户 Mac）：pytest 全套 193 passed（原 144 + C1 新增 49）；Ruff check/format 通过；Mypy strict 通过；`git diff --check` 退出码 0。测试全部使用 synthetic fixtures，无真实案例/每日记录内容。
  - 边界：未做 Neo4j 写入、Chunk、Embedding、LLM 调用；未修改真实案例 JSON、每日记录、HTML、Cloudflare Functions 或 Source Collector；C2/C3 未启动。
- 下一步：停下等用户审查本地分支；是否推送并创建 Draft PR 由用户决定。

## M2-C1 路径一致性修复检查点（2026-11-22）

- 背景：M2-C1 已于 2026-11-22 推送并开启 Draft PR #7（分支 `phase1/m2c1-case-json-mapper`，首个远端快照提交 `3ceec76226f56839ea82f504fade1f88e56d8b39`，父提交为 main `dbc2c19`；远端文件已按 Git blob SHA 与本地逐一核对一致）。上方 2026-11-22 的 M2-C1 检查点中“尚未推送、尚未创建 PR”是当时的状态记录，此处更正当前状态，历史记录不改写。
- 代码审查发现并已修复：`map_class_case_file()` 与 `map_daily_records_file()` 在 `_relative_to_root()` 完成边界检查后，仍用调用方传入的原始路径 `read_bytes()`，相对路径会按当前工作目录读取，可能与受检文件不一致。现改为共用 `_resolve_within_root()`：相对路径始终相对于 source_root 解析，绝对路径 resolve 后做仓库边界检查，检查与实际读取使用同一个解析后的绝对路径；外部路径与外部符号链接继续拒绝。
- 新增 synthetic 回归测试 2 个（`TestRelativePathsResolveAgainstSourceRoot`）：repository root 与另一个 current working directory 放置同名但内容不同的 JSON，切换 CWD 后以相对路径调用两个 Mapper，断言只读取 repository root 内的文件（daily 版若误读 CWD 文件会因 allowlist 记录缺失而报错）。
- 验证（实现方 Linux clone 的 venv，Python 3.12.3，非用户 Mac、非 CI）：pytest 199 passed（原 197 + 新增 2），Ruff check/format 通过，Mypy strict 通过，`git diff --check` 退出码 0。
- 当前状态：M2-C1 正在 Draft PR #7 审查与修订中；C2/C3 未启动；PR #7 不自行合并，等待 ChatGPT 复审与用户决定。

## M2-C1 only_cases 语义修复检查点（2026-11-23）

- 复审发现（ChatGPT 对 PR #7 head `d56c8d3` 的复审）：M2-C1 把既有配置 `DailyRecordsSettings.only_cases` 改成了描述性偏好，实际导入只看 allowlist、不看 `isCase`，与 main 上原有语义（“Only import records explicitly marked as classroom cases”）及 `SourcesConfig.summary()` 的 “cases only” 显示不一致。结论为暂不通过，须先修复此兼容性问题。
- 修复：恢复原有语义。`parse_daily_container_bytes()` 新增 `only_cases` 参数（默认 True），`map_daily_records_file()` 透传 `settings.only_cases`。only_cases=True 时，allowlist 内记录还须 `isCase` 严格为 true 才映射，被过滤的 allowlist 记录记入结果的 `filtered_record_ids`（不静默丢弃）；only_cases=False 时 allowlist 内非案例记录也可映射。两种情况下 (path, record_id) 白名单始终是硬性前提；`isCase`/`caseSource` 仍只是分类信息，映射结果永远是 CastRecord，不会生成 ClassCase。config 类 docstring 已同步恢复为真实语义，summary 显示与行为一致。
- 测试修正与新增：修正 `test_map_daily_records_file_with_allowlist`（默认配置下被映射的记录改为显式 `isCase=True`）及 CWD 回归测试的 repo 侧记录；allowlist 机制类测试显式传 `only_cases=False`；新增 4 个测试（解析层与文件层各 2 个：only_cases=True 排除 allowlist 内非案例含 isCase 缺失、only_cases=False 允许 allowlist 内非案例）。
- 验证（实现方 Linux clone 的 venv，Python 3.12.3，非用户 Mac、非 CI）：pytest 203 passed（原 199 + 新增 4），Ruff check/format 通过，Mypy strict 通过，`git diff --check` 退出码 0。
- 当前状态：修复已推送至 Draft PR #7，等待 ChatGPT 对新 head 的最终复审与用户合并决定；C2/C3 未启动。

## M2-C1 合并与 M2-C2 启动检查点（2026-11-23）

- PR #7（M2-C1）已由用户授权并正式合并到 main，merge commit `51a0476da6b8986e44fbe0d6fa0a5779cf5dbad2`。M2-C1 完成。
- 用户 2026-11-23 授权启动 M2-C2，并决定第一轮路线：先用现有知识（课程笔记、课堂案例、每日记录）完成端到端验收，再引入外部资料来源；M6 延期到现有知识验收之后，不作为第一轮验收前置条件，不取消（计划文档 §12 同步）。
- M2-C2 在新分支 `phase1/m2c2-daily-markdown-adapter`（基于 main `51a0476`）实现，新增 `tools/liuyao-kb/src/liuyao_kb/sources/daily_markdown.py`：
  - 复用既有 MarkdownAdapter 完整解析生成的每日记录 MD（type-B），保留正文 Section、来源 URI/身份、内容哈希与原文定位；
  - 提取 `## 原始记录 JSON` 内嵌块（围栏感知，围栏内的同名标题行不算该 Section；重复 Section、缺失、JSON 格式错误、id 缺失均为显式错误）；
  - 三方身份核对：文件名 `<日期>--<record_id>.md` 的 id、内嵌 JSON 的 id 必须一致；提供容器时再经 C1 的容器 Mapping 验证该 id 是已映射的 CastRecord（allowlist 与 only_cases 已在 C1 生效），不一致、未映射或容器未处理均为显式错误，不静默猜测；
  - `body_sections` 排除原始记录 Section（标题与其 JSON 围栏块），下游 Chunk 不会重复索引内嵌结构化 JSON；内嵌 JSON 原文以哈希与冻结副本保留在 `embedded_raw_record`；
  - 关联以 `RendersLink`（relation=`RENDERS`）表达，只引用既有 CastRecord 的 record_id 与容器身份，不创建 ClassCase 或第二个 CastRecord；未提供容器时链接为未验证状态，不伪造容器身份。
- 测试：新增 `tests/test_daily_markdown.py` 18 个 synthetic 测试（身份一致/不匹配、内嵌缺失/格式错误、重复 Section、缺失 id、文件名无 id、围栏内假标题、排除后正文与定位、容器验证与不重复创建）。完整测试：pytest 221 passed（原 203 + 新增 18）；Ruff check 通过、format 通过；Mypy strict 通过（12 个源文件）；git diff --check 退出码 0。测试均在实现方 Linux Python 3.12.3 venv 中运行，不是用户 Mac，也不是 CI。
- 人工核查：以仓库内真实生成 MD（2026-11-21 的 7e0a6b19 记录）只读试跑文件级 Mapper 并经真实容器验证通过（record_id 一致、RENDERS 容器验证为真、19 个 Section 中正文 17 个、内嵌 schemaVersion 16、正文不含原始记录标题）；真实文件未修改、未提交为测试 fixture。
- 本检查点之后停下：M2-C2 以 Draft PR 提交，等待 ChatGPT 复审与用户合并决定；不合并、不标记 Ready；C3、M3–M8 不启动。

## M2-C2 复审修正检查点（2026-11-23）

- ChatGPT 第一轮复审 PR #8：整体实现方向符合设计，提出两项修正，本检查点记录修正结果；PR #8 已创建并审查中（当前状态行中的“Draft PR 待创建”已按现状更正，历史检查点保留不改写）。
- 修正 1（代码）：`body_sections` 的排除逻辑由“标题文字等于 `原始记录 JSON`”改为按已识别原始记录 Section 的实际 span 精确排除（`section_start_offset`/`section_end_offset` 区间）。普通 H1/H3 即使标题文字同为“原始记录 JSON”，只要不在该 span 内，一律保留为正文；原有围栏识别、重复 Section 检查与原文定位行为不变。新增 synthetic 测试 `TestSameNameHeadingsKept`：同名 H1/H3 及其正文保留、只有被识别的 H2 原始记录 Section 被排除、被排除 Section 全部落在记录的 span 内。
- 修正 2（文档）：progress 的 Active PR 改为 PR #8 并注明等待 ChatGPT 复审、Last updated 更新为 2026-11-23；handoff 将 M2-C2 改为 Draft PR #8 审查中，明确 C2 已获用户授权并正在实施、C3 仍未启动且仍须单独授权，并更新 Knowledge Base 工作流授权描述与 Claude Code / Knowledge Base 窗口启动提示（删除“规划阶段、C2 尚未启动、不得开始实现”的过时表述）。plan §12 的第一轮路线（M6 延期、非前置、不取消）保持不变。
- 修正后验证：pytest 222 passed（原 221 + 新增 1）；Ruff check 通过、format 通过；Mypy strict 通过（12 个源文件）；git diff --check 退出码 0。测试均在实现方 Linux Python 3.12.3 venv 中运行，不是用户 Mac，也不是 CI。
- 修正后停下：更新推送至现有 Draft PR #8，等待 ChatGPT 最终复审与用户合并决定；不合并、不标记 Ready；C3 不启动。

## M2-C2 第二轮复审修正检查点（2026-11-23）

- ChatGPT 第二轮复审 PR #8：上轮 body_sections 的 span 精确排除已确认修复（普通 H1/H3 同名标题保留）；本轮只处理围栏识别一致性与小型文档同步。
- 修正（代码）：`daily_markdown.py` 的 `_raw_record_spans()` 与 `_extract_embedded_json()` 不再使用自有 `_FENCE_RE` 判断围栏，改为直接复用 MarkdownAdapter 的 `_FENCE_LINE_RE`、`_is_opening_fence()`、`_is_closing_fence()`：反引号 info string 中含反引号的 fence-shaped 行不再被当作开围栏；关闭围栏须同字符、长度不短于开围栏、其后只能有空格或 tab。两个 Parser 对同一份 Markdown 的围栏理解从此不可能不一致。新增 2 个 synthetic 测试（`TestFenceRulesMatchMarkdownAdapter`）：真实原始记录 Section 之前放无效反引号 fence-shaped 行仍能正确识别 H2 Section；原始记录 Section 内先放无效 fence-shaped 行、再放真正的 ```json 围栏时能正确提取实际 JSON。原有同名 H1/H3 保留测试继续通过。
- 修正（文档）：本文件 Last completed milestone 更新为 M2-C1（PR #7）；PR #8 描述中 `test_daily_markdown.py` 的测试数量已改为当前真实数量（21 个；全文合计见下）。历史 checkpoint 不改写。plan §12 第一轮路线保持不变（M6 延期、非前置、不取消）。
- 修正后验证：pytest 224 passed（原 222 + 新增 2）；Ruff check 通过、format 通过；Mypy strict 通过（12 个源文件）；git diff --check 退出码 0。测试均在实现方 Linux Python 3.12.3 venv 中运行，不是用户 Mac，也不是 CI。
- 修正后停下：更新推送至现有 Draft PR #8，等待 ChatGPT 最终复审与用户合并决定；不合并、不标记 Ready；C3、M3 不启动。

## M2-C2 第三轮复审修正检查点（2026-11-23）

- ChatGPT 第三轮复审 PR #8：围栏规则一致性已确认修复；仅剩切行规则一处窄边界：C2 自有 `_iter_lines()` 用 `str.splitlines()`，会把 U+2028、U+0085、单独 `\r` 等也当作行分隔符，与 MarkdownAdapter 只按 `\n` 切分（并处理紧邻的 `\r`）不一致，极端情况下两者对围栏位置的判断可能不同。
- 修正（代码）：删除 C2 自有 `_iter_lines()`，`_raw_record_spans()` 与 `_extract_embedded_json()` 改为直接复用 MarkdownAdapter 的 `_iter_lines()`，物理行切分规则与适配器完全相同（顺带消除了 `_extract_embedded_json` 内部 `splitlines()` 的同类分歧）。新增 U+2028 边界 synthetic 测试：正文行中 U+2028 后的 fence-shaped 文本只是行内正文，两个 Parser 判断一致，真正的原始记录 Section 仍被正确识别。
- 修正（文档）：workspace-handoff.md 的 Last updated 更新为 2026-11-23。按复审建议，本轮不更新 PR #8 描述（避免测试数量再次变动后重复改），待最终复审通过后统一更新。
- 修正后验证：pytest 225 passed（原 224 + 新增 1；`test_daily_markdown.py` 共 22 个）；Ruff check 通过、format 通过；Mypy strict 通过（12 个源文件）；git diff --check 退出码 0。测试均在实现方 Linux Python 3.12.3 venv 中运行，不是用户 Mac，也不是 CI。
- 修正后停下：更新推送至现有 Draft PR #8，等待 ChatGPT 最终复审与用户合并决定；不合并、不标记 Ready；C3、M3 不启动。

## M2-C2 合并与 M2-C3 启动检查点（2026-11-23）

- PR #8（M2-C2）已由用户授权并正式合并到 main，merge commit `e963bf3f378cb3787a8ce27bb121eed193c7c3a5`。M2-C2 为 approved_merged。main 上的进度文档此前仍停留在“C2 等待复审”，本检查点起在 C3 分支内同步为实际状态（不直接改 main）。
- 用户 2026-11-23 明确授权启动 M2-C3（仅 C3，不含 M3 及后续里程碑）。M2-C3 在新分支 `phase1/m2c3-classroom-case-markdown-adapter`（基于 main `e963bf3`）实现，新增 `tools/liuyao-kb/src/liuyao_kb/sources/case_markdown.py`：
  - 配对关系完全复用 C1：只消费 `ClassCaseMapping.paired_markdown`（PairedMarkdownRef 的路径、URI、identity、exists），不重新猜测 case 身份；case_id 与原 ClassCase 完全相同；
  - 用既有 MarkdownAdapter 解析 Type-A 配对 MD，保留标题层级、Section、段落与原文 offset，MD 有自己独立的 SourceDocument 身份、URI 与内容哈希；关联以 `HasRepresentationLink`（relation=`HAS_REPRESENTATION`，format=`markdown`）表达，不创建第二个 ClassCase、不把 MD 当作独立分析案例；
  - JSON 与 MD 内容不要求一致、不静默合并；不按语义推断来源角色，老师讲解/用户 Memo/AI 计算按原文标题与段落原样保留；MD 中的链接只保留文本，永不抓取；
  - Type-A/Type-B 严格区分：只读 `paired_markdown.relative_path`，绝不读 `dailyRecord.markdownPath`（Type-B）；有专门的 synthetic 回归测试；
  - 失败一律显式：paired 缺失、exists=False（文件缺失）、exists=None（未验证存在性）均为 ClassCaseMarkdownError；无效 UTF-8、空文件由 MarkdownAdapter 显式失败；路径越界/symlink 越界经 C1 的 `_resolve_within_root` 与 C1 的 exists 规则显式失败；MD 缺失时 ClassCase Mapping 本身保留不动。
- 测试：新增 `tests/test_case_markdown.py` 14 个 synthetic 测试（正常映射、case_id 一致、HAS_REPRESENTATION/format、URI/identity/hash、标题段落与 offset、链接保留、内容不同不合并、Type-B 不误读、同名文件不同 lesson 不混淆、缺失/未验证/无效 UTF-8/空文件/路径越界/symlink 越界、重复映射幂等）。完整测试：pytest 239 passed（原 225 + 新增 14）；Ruff check 通过、format 通过；Mypy strict 通过（13 个源文件）；git diff --check 退出码 0。测试均在实现方 Linux Python 3.12.3 venv 中运行，不是用户 Mac，也不是 CI。
- 真实文件只读核验：lesson-19 的 case-001（case_id `L19-C01-work-transfer`，Type-A MD 解析 51 个 Section，offset 全部可回定位）与 case-002（case_id `L19-C02-shop-operation-transfer`，28 个 Section，offset 全部可回定位）；case-002 的 `dailyRecord.markdownPath` 指向 Type-B 文件且未被读取，C3 读的是 `case-002-analysis.md`。真实文件未修改、未用作 fixture。
- 本检查点之后停下：M2-C3 以 Draft PR 提交，等待 ChatGPT 复审与用户合并决定；不合并、不标记 Ready；M3 不启动。
