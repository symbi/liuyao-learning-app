# Repository agent instructions

These instructions apply to Claude Code, Codex, ChatGPT-assisted edits, and any other coding agent working in this repository.

## Source of truth and model switching

- Read `docs/workspace-handoff.md` first to identify active parallel workstreams and their boundaries.
- Then read the progress file for the workstream you are about to touch: `docs/phase1-progress.md` for Phase 1, or `docs/html-maintenance-progress.md` for HTML maintenance.
- For Phase 1, also read `docs/phase1-implementation-plan.md`, `docs/phase1-operating-model.md`, `docs/master-plan.md`, and relevant domain docs before coding.
- Each workstream owns its own progress file. Update it at every checkpoint; do not overwrite the other workstream's status.
- Do not rely on a previous model's conversation memory. GitHub `main` is the shared record of confirmed decisions; an unmerged Draft PR is not yet part of shared main state.
- If documentation conflicts, follow this order: latest explicit user decision recorded in the relevant workstream progress file -> `docs/workspace-handoff.md` for cross-workstream coordination -> the workstream's implementation plan -> older design documents.

## Mandatory Git workflow

- Never work directly on main. Never push implementation changes directly to main.
- Keep workstreams isolated. Phase 1 uses `phase1/mX-...`; HTML maintenance uses `fix/html-...`. Do not reuse the other workstream's branch.
- Start each task branch from the latest approved main.
- Do not combine unrelated workstreams or milestones in one branch/PR.
- Before editing, run `git status --short` and inspect existing changes. Preserve user changes; do not reset, clean, stash, or overwrite them without explicit permission.
- Before changing shared documentation, check whether another workstream's branch or PR is editing the same file. Prefer each workstream's own progress file.
- At a checkpoint, run applicable tests/lint, inspect `git diff`, update the relevant progress file, create a descriptive commit, push the branch, and create a Draft Pull Request to main.
- The PR must state task/milestone, scope, files changed, exact test commands/results, manual checks, known limits, security review, and next step.
- Stop after creating/updating the Draft PR. Do not merge, close, or mark the PR approved. ChatGPT reviews it; user controls approval/merge.
- If `gh` CLI or push access is unavailable, do not pretend the checkpoint is on GitHub. Commit locally if safe, report the blocker and exact branch/commit, and request help to publish it.

## Implementation discipline

- Do one explicitly requested task or milestone at a time.
- Phase 1 must follow `docs/phase1-implementation-plan.md`; do not broaden scope or rewrite the HTML app unless explicitly requested.
- HTML maintenance must follow `docs/html-maintenance-progress.md`; make only the requested front-end changes. Do not modify Cloudflare Pages Functions, GitHub save APIs, daily-record schema, or Phase 1 Python / Neo4j architecture unless explicitly requested.
- Do not deploy Cloud Run, add Supabase/PostgreSQL, or introduce Docker in Phase 1.
- Neo4j AuraDB Free is the Phase 1 knowledge database. Since the 2026-11-24 cloud-first decision, the Python Importer runs as Google Cloud Run Jobs and the online analysis API runs as a Cloud Run Service (M7); local runs are development convenience only, and Phase 1 does not depend on the user's Mac.
- Keep Raw ASR separate from Curated Lesson Notes. Raw ASR is disabled by default and must not silently enter the main chunk/vector/rule extraction pipeline.
- LLM-extracted knowledge remains candidate; never promote it to confirmed classroom rules.
- Use allowlisted sources only. Do not crawl/import an entire GitHub repository by default.
- External collection is a separate repository: `symbi/liuyao-source-collector` (created, Private; owned by a separate workstream) collects allowed web/GitHub material and outputs a standard Reference Package. This repository never implements crawlers or website collectors, and never collects external sites directly; it only receives, validates, and imports approved Reference Packages. The intake contract is `docs/reference-source-catalog.md` section 5 and `docs/reference-package-v1.schema.json`. Registration in the Source Catalog is not approval: candidate sources must not be described as downloaded, verified, or imported.
- PDF adapter and PDF OCR are deferred (decided 2026-11-21). There is currently no selected PDF input, so do not add PDF parsing/OCR dependencies or fixtures. Re-evaluate only when the user selects a concrete PDF and its rights status is confirmed.
- Keep original source path, commit/revision, page/heading/paragraph, source type, trust level, and model provenance.
- Re-import must be idempotent. Never create duplicate nodes or re-call models for unchanged chunks.
- HTML tests must use temporary or fixture data and must not overwrite real daily records or classroom cases.
- Do not claim a PDF, real case, browser check, or test was verified unless it was actually performed.

## Security and privacy

- Never commit `.env`, API keys, Neo4j credentials, GitHub tokens, private audio/transcripts, private user records, or secrets in logs, fixtures, docs, or screenshots.
- Use `.env.example` with placeholder values only.
- Do not upload Raw ASR, private material, or daily personal memos to Gemini by default.
- Gemini free-tier data handling must be checked before sending any real course content. Use only material the user explicitly allows for cloud processing.
- Logs must redact credentials and sensitive text.
- Never ask the user to paste secrets into ChatGPT.

## Checkpoint report

At every checkpoint, provide:
1. branch and Draft PR URL;
2. summary of behavior delivered;
3. files changed;
4. exact test/lint commands and results (do not claim tests that were not run);
5. manual checks and what still requires user action;
6. security / data-preservation check;
7. relevant progress-file update and next step.

Then stop and wait for ChatGPT review before proceeding.
