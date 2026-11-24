# Claude Code instructions

Read `AGENTS.md` and `docs/workspace-handoff.md` before doing anything. Then read `docs/phase1-progress.md` and the Phase 1 planning documents. They contain the cross-window coordination rules and current durable Phase 1 state.

For Phase 1, follow:
- `docs/phase1-progress.md` — current Phase 1 state and milestone checkpoints.
- `docs/phase1-implementation-plan.md` — detailed milestones and acceptance criteria.
- `docs/phase1-operating-model.md` — architecture and data-flow decisions.
- `docs/claude-code-phase1-execution-prompt.md` — Phase 1 execution workflow and checkpoint protocol.

Important:
- This Claude Code workstream is Phase 1 only. Do not modify `index.html`, front-end UI, or HTML maintenance progress unless the user explicitly reassigns that work to you.
- Work on only the milestone explicitly requested by the user.
- Current state (2026-11-24): M0, M1 and M2 are complete and merged (M2-C3 merged via PR #10, merge commit 673a581). Phase 1 is cloud-first: production execution runs on Google Cloud Run (Jobs for imports, Service for the M7 online analysis API), not on the user's Mac; see docs/phase1-implementation-plan.md v1.2. M3 has NOT started — do not start any milestone without the user's explicit authorization for that milestone.
- AuraDB Instance01 (Free) exists and must not be deleted; its credentials are pending recovery by the user in the Aura Console, and production secrets belong in Google Secret Manager — never in this repository, a PR, or any chat.
- If Vector Index is unavailable, report the evidence and stop for a ChatGPT/user decision. Do not upgrade a paid tier or change architecture on your own.
- Use a separate `phase1/mX-...` branch and Draft PR for each implementation milestone. Never commit implementation changes directly to main.
- After the Draft PR is ready, stop for ChatGPT review. Do not merge it or continue to the next milestone automatically.
- Update `docs/phase1-progress.md` so another model or window can resume without access to this conversation.
- Never commit secrets or private raw content.
