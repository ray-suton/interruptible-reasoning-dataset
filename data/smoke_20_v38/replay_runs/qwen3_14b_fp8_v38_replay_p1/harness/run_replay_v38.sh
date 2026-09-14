#!/usr/bin/env bash
# Frozen-prefix replay of the v38 batch, UNDER THE PROMPT THE PREFIXES WERE MADE
# WITH. One GPU. Exit code is the signal.
#
# --interrupt_pos 1.0 makes run.py use output[-1] verbatim, so the pinned 0.6 cut
# is replayed, not re-cut. The seeds are per-record (inference_utils.py:131), but
# the stack is not reproducible at a fixed seed -- they are three stochastic
# rollouts of one row, never three independent observations.
set -euo pipefail
cd "/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"
PY="${PYTHON_BIN:-.venv312/bin/python}"
MODEL="${MODEL:-Qwen/Qwen3-14B-FP8}"
RUN="${RUN:?run dir}"
PROMPT="tmp/repro/smoke100_p1_run/prompts/baseline_v38.json"   # the registry's runnable copy
export HF_HUB_CACHE="${HF_HUB_CACHE:-$(pwd)/tmp/repro_hf_cache}" HF_HUB_OFFLINE=1
export VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-16384}"

"$PY" tmp/repro/smoke20_v38_replay/build_replay_input_v38.py \
    --seeds "${SEEDS:-42,43,44}" --output-dir "$RUN/data" --selfcheck
"$PY" tmp/repro/smoke20_v38_replay/selftest_grade_v38.py --run "$RUN"

"$PY" src/run.py --model_name "$MODEL" --task math --num_gpus 1 --local_rank 0 --tensor_parallel_size 1 \
    --max_tokens "${MAX_TOKENS:-8192}" --temperature 0.6 --top_p 0.95 --top_k 20 --seed 42 \
    --input_file "$RUN/data/stage2_input.jsonl" --output_dir "$RUN/update" \
    --mode subsequent_interrupt_update --interrupt_pos 1.0 --interrupt_role assistant \
    --problem_field_name original_problem --custom_prompt_file "$PROMPT"
echo "REPLAY COMPLETE: $RUN"
