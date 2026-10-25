# Repository guidance

Start with README.md and docs/README.md. This is an interactive-search research
repository. Preserve the distinction between official totals, synthetic results,
and unverified ideas.

- Keep officially scored sources in data/versions/ byte-identical. Use a new candidate
  file for experiments. Do not update archive hashes to hide source changes.
- Every real query must respect Q<=199, O<=6, and a real final-parking allowance.
  Default redundancy control is heuristic; do not claim a universal guarantee.
- Do not remove counterexamples or weaken assertions to make a strategy pass.
  Core checks and full strategy diagnostics are explicitly separate.
- Run relevant offline checks. dev/run.py check covers core behavior;
  dev/run.py diagnostics retains known failures. Describe actual outcomes.
- Online uploads consume the user's/team's quota and require user authorization.
  Existing explicit authorization in the conversation remains valid; do not
  request it again. Never turn offline checks or CI into an upload workflow.
- Unknown upload outcomes must resume the same job. Reuse the stable work ID,
  frozen source hash, submission lock and two-score confirmation.
- Leaderboard references read page one only, focus on the leader, and share the
  at-least-two-hour cache/cooldown. Do not bypass it with another browser/API.
- Keep profiles, credentials, local automation settings and run state out of Git.
- Keep paths used by existing automation stable, or supply a compatibility path.
  Update documentation navigation when adding or moving docs.
- No license has been selected. Do not introduce a project license without the
  maintainer's instruction.
