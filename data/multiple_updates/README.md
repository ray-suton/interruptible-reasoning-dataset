# Multiple Updates

Selection-only workspace for a small multiple-update smoke test.

## Selected shape

- 10 original sources
- 6 math: 2 GSM8K and 4 MATH500
- 4 planning: grid, delivery, door/key, and crate-capacity
- Qwen3-14B-FP8 no-update screening passed for every source
- Existing interrupt prefixes are referenced from the Smoke-20 trace packages

The selection spans short arithmetic chains, algebraic bounds and optimization,
route reachability, action preconditions, and capacity/order constraints. It was
also checked as a 40-row proxy using the existing Smoke-20 quartets: the selected
source set keeps the current batch audit gates passing if those quartets are used
as the starting design.

## Scope boundary

This directory currently contains source selection records only. No update rows,
multiple-update sequences, generators, review responses, or validation report
have been created yet.
