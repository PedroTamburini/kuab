#!/usr/bin/env python3
"""Evaluate lexical predictions against the provisional SFT v2 test set."""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import Counter
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_set(value: str) -> frozenset[str]:
    return frozenset(
        " ".join(unicodedata.normalize("NFC", item).casefold().split())
        for item in value.split(";")
        if item.strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="JSONL with id and prediction fields")
    parser.add_argument(
        "--references",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "sft_v2/test.jsonl",
    )
    args = parser.parse_args()

    references = {record["id"]: record for record in read_jsonl(args.references)}
    predictions = {record["id"]: record["prediction"] for record in read_jsonl(args.predictions)}
    matched = Counter()
    totals = Counter()
    unknown_ids = sorted(set(predictions) - set(references))

    for record_id, reference in references.items():
        task = reference["metadata"]["task"]
        totals[task] += 1
        if record_id in predictions and normalized_set(predictions[record_id]) == normalized_set(reference["messages"][1]["content"]):
            matched[task] += 1

    result = {
        "reference_examples": len(references),
        "predictions_received": len(predictions),
        "coverage": round(len(set(predictions) & set(references)) / len(references), 6),
        "exact_equivalent_set_accuracy": round(sum(matched.values()) / len(references), 6),
        "accuracy_by_task": {
            task: round(matched[task] / count, 6) for task, count in sorted(totals.items())
        },
        "unknown_prediction_ids": unknown_ids,
        "warning": "This test set is provisional until reviewed by Marubo speakers.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
