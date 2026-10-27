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
- Research selection maximizes aggregate local score INCLUDING zeros under
  research_objective=robust_total_score. The latest user clarification supersedes
  the previous lexicographic zero-first rule. Individual regressions are reported,
  not automatic vetoes; verify held-out mean gain, aggregate zero rate and CVaR25.
  Keep every counterexample and zero ledger. Deduplicate exact arrays and do not
  count transformed siblings as independent. Freeze the selected source before
  independent confirmation; only the confirmed winner enters the upload queue.
- Do not qualify from easy or single-profile curves alone. Include compositional
  mixed cases, a classic control domain, development-only operator ablations and
  independent confirmation. Report per-family/tier losses and actual branch usage.
  A family with all-zero scores must stay visible; do not patch a consumed holdout
  and then reuse it as novel structural evidence.
- Research is offline-first under automation/research_policy.json. Automatic
  research uses at most3 of the official team uploads per Beijing day, as an
  upper bound, not a target. Supersedes the earlier use-all30 instruction.
  Candidates need frozen diverse local evidence in qualified_candidates.json.
  Resume already delivered/uncertain work before applying any new-upload gate.
- The2026-10-27 batch is conditional, not a list sweep: primaryA first; backupB
  only after a dated recorded officialA result without improvement. Its execution
  condition is enforced by research_policy.py. Leave the third slot unallocated.
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
