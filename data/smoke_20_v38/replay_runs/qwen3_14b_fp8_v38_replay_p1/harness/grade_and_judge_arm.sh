#!/usr/bin/env bash
# Grade one arm and queue its judge batches. Deliberately reuses
# grade_replay_v38.py and judge_rubric_v38.md UNCHANGED -- if the grader or the
# rubric differed between arms, the comparison would measure those instead.
set -euo pipefail
LRM="/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"; cd "$LRM"
H=tmp/repro/smoke20_v38_replay; PY="${PYTHON_BIN:-.venv312/bin/python}"
RUN="${RUN:?run dir}"; LABEL="${LABEL:-$RUN}"
"$PY" $H/selftest_grade_v38.py --run "$RUN" > "$RUN/selftest.log" 2>&1
tail -1 "$RUN/selftest.log"
"$PY" $H/grade_replay_v38.py --run "$RUN"
"$PY" $H/decision_coverage.py --run "$RUN" --label "$LABEL" > "$RUN/decision.log" 2>&1 || echo "decision diagnostic skipped"
python3 $H/make_judge_batches_v38.py --run "$RUN"
