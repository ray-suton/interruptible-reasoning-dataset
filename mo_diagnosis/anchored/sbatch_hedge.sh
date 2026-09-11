#!/usr/bin/env bash
# Arm 4 -- hedge position -- Qwen3-14B-FP8 on the `gpu` partition.
#
# WHY SBATCH AND NOT THE INTERACTIVE NODE. The first two attempts ran on
# ws-l2-009 after the interactive allocation (job 182916) had already ended.
# Both died silently a couple of minutes in, right after torch.compile loaded
# the cached graph and before a single token was generated -- no traceback, no
# OOM in dmesg, 231 GB of host RAM free. Without a reservation there is nothing
# holding the card, so the work does not belong there regardless of the cause.
#
# Submit from the dataset repo:
#   sbatch mo_diagnosis/anchored/sbatch_hedge.sh
#
#SBATCH --job-name=p1hedge14b
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
# Per-user QOS caps reject larger asks outright; these match the values that
# were accepted for the 32B probe on this account.
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
# 8 h is the per-job QOS ceiling (12 h and 24 h are rejected with
# QOSMaxWallDurationPerJobLimit). This run needs about one.
#SBATCH --time=08:00:00
# Relative to the submission directory. An absolute path is not usable: the
# workspace path contains a space and #SBATCH directives do not support quoting.
#SBATCH --output=mo_diagnosis/anchored/hedge_slurm.log
#SBATCH --error=mo_diagnosis/anchored/hedge_slurm.log

set -euo pipefail
DS="/home/rui.gao/Desktop/Interruptible Reasoning/interruptible-reasoning-dataset"
LRM="/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm"
cd "$DS"

# The run scratch lives under $HOME, which is NFS (nfs-head:/c/home). /tmp is
# node-local, so a scratch built on the submitting host is invisible here --
# that is what the earlier per-session scratchpads were, and why they could not
# have worked from a batch job even if the process had survived.
SCRATCH="$HOME/p1_hedge_scratch"

# Weights are pre-fetched under interrupt-lrm/tmp/repro_hf_cache. Offline mode
# turns a missing file into an immediate error rather than a silent hub hang.
export HF_HUB_CACHE="$LRM/tmp/repro_hf_cache"
export HF_HUB_OFFLINE=1
export HF_DATASETS_OFFLINE=1

echo "=== node: $(hostname) ==="
echo "=== job:  ${SLURM_JOB_ID:-none} ==="
echo "=== gpus: ${CUDA_VISIBLE_DEVICES:-unset} ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv

bash "$DS/mo_diagnosis/anchored/run_hedge.sh" "$SCRATCH"
echo "=== sbatch wrapper finished, rc=$? ==="
