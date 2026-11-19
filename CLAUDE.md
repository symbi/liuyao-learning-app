# Claude Code instructions

Read AGENTS.md and docs/phase1-progress.md before doing anything. They contain the cross-model working rules and current durable project state.

For Phase 1, follow:
- docs/phase1-implementation-plan.md — detailed milestones and acceptance criteria.
- docs/phase1-operating-model.md — architecture and data-flow decisions.
- docs/claude-code-phase1-execution-prompt.md — Phase 1 execution workflow and checkpoint protocol.

Important:
- Work on only the milestone explicitly requested by the user.
- Use a separate branch and Draft PR for every milestone.
- Never commit implementation changes directly to main.
- After the Draft PR is ready, stop for ChatGPT review. Do not merge it or continue to the next milestone automatically.
- Update docs/phase1-progress.md so another model can resume without access to this conversation.
- Never commit secrets or private raw content.
