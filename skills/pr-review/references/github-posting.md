# GitHub Posting

The top-level parent is the only actor allowed to publish PR-review feedback.

## Posting contract

Unless the user selected `dry-run` or `no-post`, the review is incomplete until GitHub has accepted and persisted exactly one `COMMENT` pull-request review explicitly bound to the frozen reviewed head.

Every review has a non-empty top-level body, including a clean review, and contains fresh run markers:

```text
<!-- pr-review-skill -->
<!-- pr-review-skill-run: <reviewed-head-sha>-<fresh-UTC-timestamp-and-random-nonce> -->
```

Use a new marker for every invocation so an older review cannot satisfy verification accidentally.

## Snapshot rule

Never mix analysis from different head SHAs.

Bind publication to the frozen reviewed commit. A live PR head change does not cancel, restart, or retarget the review; publish the completed findings to the reviewed head even when GitHub renders the resulting review or inline comments as outdated.

Do not fall back to an unbound review against the current live head. When publication is required and the runtime cannot explicitly target the frozen reviewed commit, the review is `unsupported` and should have stopped before discovery.

Immediately before mutation, re-fetch current review feedback only for duplicate suppression. Do not use newer-head content to alter the frozen analysis, and drop a finding only when existing feedback clearly covers the same root cause on the reviewed snapshot.

## Inline vs top-level

Use inline comments for specific actionable findings when the finding maps unambiguously to a changed line on the reviewed snapshot. Use the review body for cross-file findings, unanchorable test/documentation/operational concerns, rare material `needs-human` notes, and the clean-result statement.

Do not duplicate one finding both inline and in the body. If an inline anchor is unsafe, move the finding to the body rather than guessing.

Each published finding should state the changed behavior that is wrong, its concrete impact or failing condition, and the smallest useful remediation direction. Avoid generic best practices, tutorials, praise attached to defects, and vague suggestions without a concrete failure.

## Clean result

When no publishable findings remain, still submit a non-empty COMMENT review such as:

```text
No new actionable findings were found in this review pass.
```

Do not imply approval or resolution of unrelated existing feedback.

## Verification

After submission, re-fetch reviews and inline comments. Success requires evidence that the specific current-run COMMENT review persisted, is associated with the frozen reviewed head when GitHub exposes that metadata, contains the intended top-level body and fresh run marker, and includes every intended inline comment at the expected location.

A returned review ID is useful but does not replace current-run marker verification. Do not treat process exit status, HTTP success alone, stdout, or the parent's final response as proof of publication.

If mutation succeeds but verification is inconclusive, re-read GitHub state once to rule out propagation delay. Do not create a second review merely because the first response was incomplete. If the intended artifact still cannot be verified, report publication failure.

In `dry-run` or `no-post` mode, skip mutation and return the arbitrated findings with an explicit statement that nothing was posted.
