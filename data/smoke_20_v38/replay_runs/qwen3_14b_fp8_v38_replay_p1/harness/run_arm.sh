#!/usr/bin/env bash
# One prompt-condition arm over the ALREADY-BUILT input in $RUN/data.
# The input builder has already checked the pinned prefix shas; this only runs.
set -euo pipefail
cd "/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"
PY="${PYTHON_BIN:-.venv312/bin/python}"; MODEL="${MODEL:-Qwen/Qwen3-14B-FP8}"
RUN="${RUN:?run dir}"; PROMPT="${PROMPT:?prompt file}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$(pwd)/tmp/repro_hf_cache}" HF_HUB_OFFLINE=1
export VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-16384}"
"$PY" src/run.py --model_name "$MODEL" --task math --num_gpus 1 --local_rank 0 --tensor_parallel_size 1 \
    --max_tokens "${MAX_TOKENS:-8192}" --temperature 0.6 --top_p 0.95 --top_k 20 --seed 42 \
    --input_file "$RUN/data/stage2_input.jsonl" --output_dir "$RUN/update" \
    --mode subsequent_interrupt_update --interrupt_pos 1.0 --interrupt_role assistant \
    --problem_field_name original_problem --custom_prompt_file "$PROMPT"
echo "ARM COMPLETE: $RUN"
