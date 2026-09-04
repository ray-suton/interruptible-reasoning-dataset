# Source snapshots

`sources/` contains revision-pinned upstream records used to construct or audit
the Stage 1 benchmark. A source snapshot is not automatically part of the
benchmark: smoke-test selection and generated source-group files under
`data/smoke_150/` determine which records enter the active 150-sample run. The
former source registry was archived with the old workload scaffold.

The initial `upstream_interrupt_lrm/` import contains only original problems
and answers from the Math configuration. Upstream revised problems and update
instructions are excluded because they implement the earlier whole-problem
revision setting rather than the Stage 1 acceptance policy.

Every snapshot must record its upstream repository, immutable revision,
declared license, extraction rule, row counts, and content hash.
