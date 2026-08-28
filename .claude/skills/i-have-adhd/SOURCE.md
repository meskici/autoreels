# Source

Vendored from the `i-have-adhd` Claude Code plugin marketplace:
https://github.com/ayghri/i-have-adhd

Upstream install (local Claude Code CLI only):

    claude plugin marketplace add ayghri/i-have-adhd

Plugin bundles do not sync into Claude Code on the web, so `SKILL.md` is
vendored here as a project-level skill instead. It loads for any session
working in this repository.

Vendored at upstream commit: cbe69fb
Upstream version: 0.2.0 (MIT, Ayoub G.)

Not vendored: the plugin's `hooks/` always-on SessionStart hook, which
re-arms the skill automatically each session. Without it, invoke the skill
explicitly with `/i-have-adhd`.
