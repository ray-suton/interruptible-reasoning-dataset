#!/usr/bin/env python3
"""Export model-generated Smoke10 reasoning traces from an initial-run output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def model_slug(model_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", model_name).strip("_").lower()
    return slug or "model"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def normalize_answer(value: str | None) -> str:
    """Normalise a LaTeX answer for equality comparison.

    GSM8K answers are bare integers, so the original implementation only
    stripped commas. MATH500 answers are LaTeX, where one value has many
    spellings: \\dfrac vs \\frac, \\left(...\\right] vs (...], a leading
    "x \\in ", incidental spaces. Comparing those raw reports a correct answer
    as wrong -- see DATASET.md 4.1 on answer_equivalence.
    """
    if value is None:
        return ""
    v = value.strip()
    for a, b in (
        ("\\dfrac", "\\frac"), ("\\tfrac", "\\frac"),
        ("\\left", ""), ("\\right", ""),
        ("\\!", ""), ("\\,", ""), ("\\;", ""), ("\\ ", ""),
        ("$", ""), ("\\text{", "{"),
    ):
        v = v.replace(a, b)
    v = re.sub(r"^\s*[a-zA-Z]\s*\\in\s*", "", v)   # drop a leading "x \in "
    v = re.sub(r"^\s*[a-zA-Z]\s*=\s*", "", v)        # drop a leading "x = "
    v = v.replace(",", "").replace(" ", "")
    return v.rstrip(".")


def extract_boxed_answer(output_text: str) -> tuple[str | None, str]:
    """Return (answer, extraction_method).

    The method is returned so a fallback extraction is visible downstream
    instead of silent. The previous implementation used
    ``\\boxed\\{([^{}]+)\\}``, whose character class excludes braces, so it
    could not match any nested-brace answer -- every LaTeX fraction, radical
    and interval. It then fell through to "last number in the text" and
    returned a plausible-looking wrong value, which reads as an unsolved
    source rather than a broken extractor.
    """
    idx = output_text.rfind("\\boxed")
    if idx >= 0:
        brace = output_text.find("{", idx)
        if brace >= 0:
            depth = 0
            for k in range(brace, len(output_text)):
                ch = output_text[k]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return output_text[brace + 1 : k].strip(), "boxed"
    marker = re.search(r"(?:final answer|answer is)\s*:?\s*\$?(-?\d+(?:\.\d+)?)", output_text, flags=re.I)
    if marker:
        return marker.group(1), "final_answer_marker"
    numbers = re.findall(r"-?\d+(?:\.\d+)?", output_text)
    if numbers:
        return numbers[-1], "last_number_fallback"
    return None, "none"


def extract_reasoning_trace(output_text: str, model_name: str) -> str:
    lowered = model_name.lower()
    if "qwen3" in lowered or "deepseek-r1" in lowered or "nemotron" in lowered:
        trace = output_text.split("</think>")[0].strip()
        return trace.removeprefix("<think>").strip()
    if "gpt-oss" in lowered and "<|end|>" in output_text:
        return output_text.split("<|end|>")[0].strip()
    if "mistral" in lowered and "[/THINK]" in output_text:
        return output_text.split("[/THINK]")[0].strip()
    return output_text.strip()


def tokenizer_for(model_name: str, cache_dir: Path | None):
    from transformers import AutoTokenizer

    kwargs: dict[str, Any] = {"local_files_only": True}
    if cache_dir is not None:
        kwargs["cache_dir"] = str(cache_dir)
    return AutoTokenizer.from_pretrained(model_name, **kwargs)


def token_prefix(text: str, tokenizer: Any, interrupt_pos: float) -> tuple[str, int, int]:
    token_ids = tokenizer.encode(text)
    cut = max(1, int(len(token_ids) * interrupt_pos))
    prefix = tokenizer.decode(token_ids[:cut])
    return prefix, cut, len(token_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1-output", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--interrupt-pos", type=float, default=0.6)
    parser.add_argument("--run-config", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = load_jsonl(args.stage1_output)
    sidecar = json.loads(args.sidecar.read_text(encoding="utf-8"))
    tokenizer = tokenizer_for(args.model_name, args.model_cache)

    traces: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    slug = model_slug(args.model_name)

    for record in sorted(records, key=lambda item: int(item["id"])):
        model_id = int(record["id"])
        source = sidecar[str(model_id)]
        output_text = record["output"][0]
        reasoning_trace = extract_reasoning_trace(output_text, args.model_name)
        prefix, cut_tokens, total_tokens = token_prefix(
            reasoning_trace, tokenizer, args.interrupt_pos
        )
        extracted, extraction_method = extract_boxed_answer(output_text)
        expected = source["original_answer"]
        no_update_solved = normalize_answer(extracted) == normalize_answer(expected)
        status_counts["solved" if no_update_solved else "unsolved"] += 1

        trace = {
            "trace_id": f"{source['task_group_id']}_{slug}_initial_r0",
            "task_group_id": source["task_group_id"],
            "stable_source_id": source["stable_source_id"],
            "source_dataset": source["source_dataset"],
            "source_year": source["source_year"],
            "source_family": source["source_family"],
            "upstream_id": source["upstream_id"],
            "upstream_revision": source["upstream_revision"],
            "source_record_locator": source["source_record_locator"],
            "model_name": args.model_name,
            "trace_origin": "model_generated_no_update_initial",
            "run_stage": "initial_no_update",
            "run_record_id": model_id,
            "full_trace": reasoning_trace,
            "partial_reasoning_trace": prefix,
            "interrupt_position": round(cut_tokens / total_tokens, 6) if total_tokens else 0,
            "interrupt_position_basis": "token_fraction_of_model_reasoning_trace",
            "requested_interrupt_position": args.interrupt_pos,
            "total_reasoning_tokens": total_tokens,
            "prefix_reasoning_tokens": cut_tokens,
            "full_trace_sha256": sha256_text(reasoning_trace),
            "prefix_sha256": sha256_text(prefix),
            "prefix_text_is_prefix": reasoning_trace.startswith(prefix),
            "no_update_solved": no_update_solved,
            "answer_extraction_method": extraction_method,
            "prefix_valid": bool(prefix.strip()),
            "expected_answer": expected,
            "extracted_answer": extracted,
            "formatted_input_prompt_sha256": sha256_text(record["formatted_input_prompt"][0]),
            "full_model_output_sha256": sha256_text(output_text),
            "raw_output_path": str(args.stage1_output),
        }
        traces.append(trace)

    traces_path = args.output_dir / "traces.jsonl"
    summary_path = args.output_dir / "trace_summary.json"
    with traces_path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")

    run_config: dict[str, Any] = {}
    if args.run_config and args.run_config.exists():
        run_config = json.loads(args.run_config.read_text(encoding="utf-8"))
    summary = {
        "status": "complete",
        "trace_count": len(traces),
        "model_name": args.model_name,
        "requested_interrupt_position": args.interrupt_pos,
        "solvability_counts": dict(sorted(status_counts.items())),
        "traces_path": str(traces_path.relative_to(ROOT) if traces_path.is_relative_to(ROOT) else traces_path),
        "traces_sha256": sha256_text(traces_path.read_text(encoding="utf-8")),
        "stage1_output": str(args.stage1_output),
        "stage1_output_sha256": sha256_text(args.stage1_output.read_text(encoding="utf-8")),
        "sidecar": str(args.sidecar),
        "sidecar_sha256": sha256_text(args.sidecar.read_text(encoding="utf-8")),
        "run_config": run_config,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"exported {len(traces)} trace(s) to {traces_path}; "
        f"solvability={dict(sorted(status_counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
