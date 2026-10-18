# Review Lenses

Choose scopes from **changed behavior and concrete risk**, not filenames or generic checklists. For unscoped reviews, cover correctness/regression risk; include tests and documentation when relevant. Explicit user scope overrides the baseline.

Consider a conditional lens only when the diff implicates it:

- **Security:** authn/authz, secrets, untrusted input, serialization, file/process/network access, CI or deployment credentials.
- **Reliability/I/O:** errors, retries, fallback, cleanup, partial operations, external services, asynchronous failures.
- **Data/migrations:** schemas, formats, backfills, indexes, transactions, rollout/rollback, reader/writer compatibility.
- **Concurrency/lifecycle:** shared state, queues, caches, locking, timers/listeners, cancellation, idempotency, leaks, ordering.
- **API/compatibility:** public interfaces, CLI/config/environment, files/protocols, workflow inputs/outputs, consumed schemas.
- **Performance:** unbounded work, database/network calls, batching, allocation, caching, pagination, startup, long-lived resources.
- **Infrastructure/supply chain:** Actions, containers, IaC/IAM, dependencies, build/release, provenance, deployment order.
- **Observability:** critical background work, retries, recovery, transitions, distinguishable failure/partial states.
- **Documentation:** materially incorrect or incomplete changed comments, examples, defaults, commands, permissions, operational guidance.
- **Maintainability:** introduced duplication, speculative abstractions, needless branching or complexity without current requirements.

Use a small number of coherent scopes; split only for distinct risks. Apply [finding-validation.md](finding-validation.md)'s evidence/publication gates to security, tests, performance, compatibility, documentation, and maintainability instead of widening review into best-practice advice.
