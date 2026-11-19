# Repository agent instructions

These instructions apply to Claude Code, Codex, ChatGPT-assisted edits, and any other coding agent working in this repository.

## Source of truth and model switching

- Do not rely on the previous model's conversation memory.
- Always read docs/phase1-progress.md first, then docs/phase1-implementation-plan.md, docs/phase1-operating-model.md, docs/master-plan.md, and relevant domain docs before coding.
- docs/phase1-progress.md is the model-independent handoff state. Update it at each milestone checkpoint.
- If documentation conflicts, follow this order: latest user decision recorded in docs/phase1-progress.md -> docs/phase1-implementation-plan.md -> docs/phase1-operating-model.md -> older design documents.
- Never infer that a milestone is complete just because another model claimed it. Verify code, tests, GitHub branch/PR, and progress status.

## Mandatory Git workflow

- Never work directly on main. Never push implementation changes directly to main.
- Work on one milestone branch at a time: phase1/m1-python-skeleton, phase1/m2-source-parsers, etc.
- Start each milestone branch from the latest approved main.
- Do not combine unrelated milestones in one branch/PR.
- Before editing, run git status --short and inspect existing changes. Preserve user changes; do not reset, clean, stash, or overwrite them without explicit permission.
- At the milestone checkpoint, run tests/lint, inspect git diff, update docs/phase1-progress.md, create a descriptive commit, push the branch, and create a Draft Pull Request to main.
- The PR must state milestone, scope, files changed, exact test commands/results, manual checks, known limits, security review, and next milestone.
- Stop after creating/updating the Draft PR. Do not merge, close, or mark the PR approved. ChatGPT reviews it; user controls approval/merge.
- If gh CLI or push access is unavailable, do not pretend the checkpoint is on GitHub. Commit locally if safe, report the blocker and exact branch/commit, and request help to publish it.
- Do not start the next milestone until the prior milestone is reviewed and merged to main.

## Implementation discipline

- Do one requested milestone at a time. Never execute M0–M8 in a single unattended run.
- Follow docs/phase1-implementation-plan.md; do not broaden scope or rewrite the HTML app unless explicitly requested.
- Do not deploy Cloud Run, add Supabase/PostgreSQL, or introduce Docker in Phase 1.
- Neo4j AuraDB Free is the Phase 1 knowledge database. Python Importer and Query Tool run locally on Mac.
- Keep Raw ASR separate from Curated Lesson Notes. Raw ASR is disabled by default and must not silently enter the main chunk/vector/rule extraction pipeline.
- LLM-extracted knowledge remains candidate; never promote it to confirmed classroom rules.
- Use allowlisted sources only. Do not crawl/import an entire GitHub repository by default.
- Keep original source path, commit/revision, page/heading/paragraph, source type, trust level, and model provenance.
- Re-import must be idempotent. Never create duplicate nodes or re-call models for unchanged chunks.
- Do not claim a PDF or real case was tested unless an actual user-provided file/record was used.

## Security and privacy

- Never commit .env, API keys, Neo4j credentials, GitHub tokens, private audio/transcripts, private user records, or secrets in logs, fixtures, docs, or screenshots.
- Use .env.example with placeholder values only.
- Do not upload Raw ASR, private material, or daily personal memos to Gemini by default.
- Gemini free-tier data handling must be checked before sending any real course content. Use only material the user explicitly allows for cloud processing.
- Logs must redact credentials and sensitive text.
- Never ask the user to paste secrets into ChatGPT.

## Checkpoint report

At every milestone, provide:
1. branch and Draft PR URL;
2. summary of behavior delivered;
3. files changed;
4. exact test/lint commands and results (do not claim tests that were not run);
5. manual checks and what still requires user action;
6. security/secret scan result;
7. progress file update and next milestone recommendation.

Then stop and wait for ChatGPT review before proceeding.
