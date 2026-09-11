#!/usr/bin/env bash
# Anchored MO sweep: 10 sources x 6 contract-compliant attack types, Qwen3-14B-FP8.
# Companion to run_20260910 (generic attacks). Same sources, same implied answers,
# same seeds -- the attack TEXT is the only thing that differs.
set -euo pipefail
set +o noclobber

DS="/home/rui.gao/Desktop/Interruptible Reasoning/interruptible-reasoning-dataset"
LRM="/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"
PY="$LRM/.venv312/bin/python"
SP="$1"                      # scratchpad run root (raw prompts stay out of the repo)
OUT="$DS/mo_diagnosis/anchored/run_hedge_20260911"
PREP="$DS/mo_diagnosis/anchored/prep_hedge.py"
MODEL="Qwen/Qwen3-14B-FP8"
ROLLOUTS=5
POS=0.6

export HF_HUB_CACHE="$LRM/tmp/repro_hf_cache"
export VLLM_MAX_MODEL_LEN=16384
export TOKENIZERS_PARALLELISM=false

mkdir -p "$OUT" "$SP/stage1" "$SP/load1"

wait_for_vram () {   # vLLM asks for 0.9 of TOTAL VRAM and run.py cannot lower it
  local need=$1 waited=0 idx
  # Query the ASSIGNED gpu, with no pipe. Two bugs lived in one line here:
  #   `nvidia-smi ... | head -1` made head close the pipe after one row, so on a
  #   multi-GPU node nvidia-smi took SIGPIPE and `set -o pipefail` turned that
  #   into exit 141 -- the job died in 1 second with no message. It could not
  #   fire on the 1-GPU interactive node, only under sbatch on gpu-01's 8 cards.
  #   And `head -1` read GPU 0 regardless of which card SLURM actually gave us,
  #   so even without the crash it would have waited on someone else's memory.
  idx="${CUDA_VISIBLE_DEVICES%%,*}"
  while :; do
    free=$(nvidia-smi --id="${idx:-0}" --query-gpu=memory.free --format=csv,noheader,nounits)
    if [ "$free" -ge "$need" ]; then echo "  VRAM ok: ${free}MiB free"; return 0; fi
    if [ "$waited" -ge 3600 ]; then echo "  TIMEOUT waiting for ${need}MiB (have ${free})"; return 1; fi
    echo "  waiting for VRAM: ${free}MiB free, need ${need}MiB (${waited}s)"
    sleep 60; waited=$((waited+60))
  done
}

echo "=== 1. build stage-1 input (baseline + load-0) ==="
"$PY" "$PREP" stage1 --src "$SP/input" --out "$SP/stage1" --rollouts "$ROLLOUTS"

echo "=== 2. generate stage 1 ==="
wait_for_vram 30000
cd "$LRM/src"
"$PY" run.py --mode initial \
  --input_file "$SP/stage1/initial_input.jsonl" \
  --output_dir "$SP/stage1/out" \
  --model_name "$MODEL" --problem_field_name original_problem \
  --max_tokens 8192 --temperature 0.6 --top_p 0.95 --top_k 20 \
  --custom_prompt_file "$LRM/src/prompts/intervene/wo_prompt_guidance.json"

echo "=== 3. split stage-1 by condition ==="
"$PY" "$PREP" split --model-output "$SP/stage1/out/output_0.jsonl" \
  --sidecar "$SP/stage1/sidecar.json" --out-dir "$SP/stage1/split"

echo "=== 4. build load-1 input from the baseline traces ==="
"$PY" "$PREP" load1 --stage1-output "$SP/stage1/split/baseline_output.jsonl" \
  --sidecar "$SP/stage1/sidecar.json" --out "$SP/load1/load1_input.jsonl"

echo "=== 5. generate load 1 (interrupt at $POS) ==="
wait_for_vram 30000
"$PY" run.py --mode subsequent_interrupt_update --interrupt_pos "$POS" \
  --input_file "$SP/load1/load1_input.jsonl" \
  --output_dir "$SP/load1/out" \
  --model_name "$MODEL" --problem_field_name original_problem \
  --max_tokens 8192 --temperature 0.6 --top_p 0.95 --top_k 20 \
  --custom_prompt_file "$LRM/src/prompts/intervene/wo_prompt_guidance.json"

echo "=== 6. collect ==="
TYPES=$("$PY" -c "import json;print(' '.join(json.load(open('$SP/stage1/meta.json'))['types']))")
for t in $TYPES; do
  "$PY" "$PREP" collect-baseline --model-output "$SP/stage1/split/baseline_output.jsonl" \
    --sidecar "$SP/stage1/sidecar.json" --attack-type "$t" --out "$OUT/base_${t}.jsonl"
  "$PY" "$PREP" collect --model-output "$SP/stage1/split/load0__${t}_output.jsonl" \
    --sidecar "$SP/stage1/sidecar.json" --attack-type "$t" --condition "load0" \
    --out "$OUT/load0_${t}.jsonl"
  "$PY" "$PREP" collect --model-output "$SP/load1/out/output_0.jsonl" \
    --sidecar "$SP/stage1/sidecar.json" --attack-type "$t" --condition "load1" --load1 \
    --out "$OUT/load1_${t}.jsonl"
done

cp "$PREP" "$OUT/prep.py"
echo "=== DONE -> $OUT ==="
