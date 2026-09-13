#!/usr/bin/env bash
# v38 judging, N workers. mkdir is the lock: atomic, so two workers never take the
# same batch. A dead worker leaves its lock behind on purpose -- a rerun reports
# the batch missing rather than silently redoing it.
set -u
RUN="${RUN:?run dir}"; LRM="/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"; cd "$LRM"
OUT="${OUT:-judge_out_v38}"; IN="${IN:-judge_in_v38}"; W="${W:-?}"
mkdir -p "$RUN/$OUT" "$RUN/.locks_$OUT"
for B in "$RUN/$IN"/batch_*.json; do
  N=$(basename "$B" .json); OUTF="$RUN/$OUT/$N.jsonl"
  [ -s "$OUTF" ] && continue
  mkdir "$RUN/.locks_$OUT/$N" 2>/dev/null || continue
  echo "[w$W] $N start $(date +%H:%M:%S)"
  timeout 1800 codex exec -C "$LRM" -s workspace-write --skip-git-repo-check \
    "Read the file \"$B\" and do exactly what its 'instructions' field says, using the rubric file it names and its 'records'. Write your JSON lines to its 'output_file'. Print JUDGE-DONE when finished." \
    < /dev/null > "$RUN/$OUT/$N.exec.log" 2>&1
  [ -s "$OUTF" ] && echo "[w$W] $N done $(grep -c . "$OUTF") $(date +%H:%M:%S)" || echo "[w$W] $N NO OUTPUT"
done
echo "[w$W] exhausted"
