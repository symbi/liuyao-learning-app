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
- Current state: M0 is waiting for the user to create AuraDB Free in Aura Console. Do not create an implementation branch, modify code, or start M1 before the user confirms the instance is ready.
- After confirmation, run only the M0 smoke tests and record real results, including tier, Neo4j version, connection, basic read/write, and Vector Index behavior / dimensions.
- If Vector Index is unavailable, report the evidence and stop for a ChatGPT/user decision. Do not upgrade a paid tier or change architecture on your own.
- Use a separate `phase1/mX-...` branch and Draft PR for each implementation milestone. Never commit implementation changes directly to main.
- After the Draft PR is ready, stop for ChatGPT review. Do not merge it or continue to the next milestone automatically.
- Update `docs/phase1-progress.md` so another model or window can resume without access to this conversation.
- Never commit secrets or private raw content.
