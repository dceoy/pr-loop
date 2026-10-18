# Finding Validation

Discovery yields hypotheses; **try to disprove each one** before publishing. For each deduplicated candidate, reconstruct changed behavior on the frozen commits, inspect only code necessary to establish reachability/constraints, and look for relevant counterevidence: upstream guards/authn, framework guarantees, tests, prior behavior, retries/cleanup, caller contracts, or unreachable paths.

Never publish solely because a pattern looks suspicious, violates generic best practice, or has high tool/model confidence.

## Disposition

- `confirmed`: evidence establishes a changed, reachable root cause and credible material impact.
- `rejected`: a control, counterexample, mistaken assumption, duplicate, pre-existing unrelated behavior, unreachable path, or unsupported impact defeats the claim.
- `needs-human`: one named external fact remains necessary to resolve material merge risk; use sparingly.

## Evidence gates

- **Security:** substantiate source/trust boundary/sink and account for existing protections.
- **Correctness/reliability:** show a concrete execution/input/state causing wrong results, loss, duplication, leak, or hidden failure.
- **Tests:** name a material regression the suite would miss.
- **Performance:** identify a realistic workload, scale, frequency, or lifecycle impact.
- **Compatibility/docs:** identify the affected external contract or factual documentation mismatch.
- **Maintainability:** show newly introduced concrete duplication, unnecessary complexity, or speculative flexibility; suggest only minimal KISS/DRY/YAGNI remediation.

Merge candidate findings sharing one changed root cause; keep distinct independently reachable failures. Rank impact (`critical`, `high`, `medium`, `low`), not confidence; normally suppress `low`.

A publishable finding must arise from changed behavior, survive counterevidence, have credible impact and a proportional fix, map accurately to the diff if inline, and not repeat already-addressed feedback. Publish only findings strong enough to interrupt the author.
