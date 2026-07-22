#!/usr/bin/env python3
"""Build the conservative Marubo lexical SFT v2 package.

Only Python's standard library is required. The canonical lexicon is never
overwritten: quality tiers and training files are emitted as derived assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PREPARATION_VERSION = "2.0.0"
PREPARATION_DATE = "2026-07-22"
SPLIT_RATIOS = {"train": 0.8, "validation": 0.1, "test": 0.1}
GRAMMATICAL_CODE = re.compile(r"[A-Z][A-Z0-9_-]{1,9}")


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, records: list[dict]) -> None:
    text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def unique_values(values: list[str]) -> list[str]:
    selected: dict[str, str] = {}
    for value in values:
        selected.setdefault(normalized(value), value.strip())
    return sorted(selected.values(), key=lambda item: normalized(item))


def classify(record: dict) -> tuple[str, list[str]]:
    portuguese = record["portuguese"].strip()
    if "?" in portuguese or not any(character.isalpha() for character in portuguese):
        return "quarantine", ["unknown_or_explicitly_uncertain_portuguese_gloss"]
    if GRAMMATICAL_CODE.fullmatch(portuguese):
        return "grammatical", ["grammatical_code_not_portuguese_translation"]
    if record["quality"].get("sense_match") != "exact_portuguese_gloss":
        return "low_confidence", ["reversal_only_no_exact_sense_match"]
    return "silver", []


def annotate(record: dict) -> dict:
    result = json.loads(json.dumps(record, ensure_ascii=False))
    tier, reasons = classify(result)
    result["quality"]["preparation_tier"] = tier
    result["quality"]["training_eligible"] = tier == "silver"
    result["quality"]["exclusion_reasons"] = reasons
    result["source"]["license_for_model_training"] = "permission_confirmed_for_this_project"
    result["source"]["permission_reference"] = "../PERMISSION.md"
    result["source"]["permission_scope"] = [
        "dataset_preparation",
        "model_training",
        "model_evaluation",
        "project_use",
    ]
    result["source"]["redistribution_permission"] = "not_documented_in_repository"
    return result


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def build_components(records: list[dict]) -> dict[str, list[dict]]:
    union_find = UnionFind()
    for record in records:
        union_find.union(
            "m:" + normalized(record["lemma_marubo"]),
            "p:" + normalized(record["portuguese"]),
        )

    grouped: defaultdict[str, list[dict]] = defaultdict(list)
    for record in records:
        root = union_find.find("m:" + normalized(record["lemma_marubo"]))
        grouped[root].append(record)

    components: dict[str, list[dict]] = {}
    for component_records in grouped.values():
        digest = hashlib.sha256(
            "\n".join(sorted(record["id"] for record in component_records)).encode("utf-8")
        ).hexdigest()[:16]
        components[f"component_{digest}"] = component_records
    return components


def example_id(task: str, query: str) -> str:
    digest = hashlib.sha256(f"{task}\0{normalized(query)}".encode("utf-8")).hexdigest()[:20]
    return f"example_{digest}"


def build_examples(component_id: str, records: list[dict]) -> list[dict]:
    examples: list[dict] = []
    by_marubo: defaultdict[str, list[dict]] = defaultdict(list)
    by_portuguese: defaultdict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_marubo[normalized(record["lemma_marubo"])].append(record)
        by_portuguese[normalized(record["portuguese"])].append(record)

    for key in sorted(by_marubo):
        matches = by_marubo[key]
        query = matches[0]["lemma_marubo"]
        answers = unique_values([record["portuguese"] for record in matches])
        examples.append(
            make_example(
                task="marubo_to_pt_lexical",
                direction="mzr_to_pt-BR",
                query=query,
                prompt=f"Traduza para português o verbete Marubo: {query}",
                answers=answers,
                component_id=component_id,
                source_ids=[record["id"] for record in matches],
            )
        )

    for key in sorted(by_portuguese):
        matches = by_portuguese[key]
        query = matches[0]["portuguese"]
        answers = unique_values([record["lemma_marubo"] for record in matches])
        examples.append(
            make_example(
                task="pt_to_marubo_lexical",
                direction="pt-BR_to_mzr",
                query=query,
                prompt=f"Traduza para Marubo o verbete português: {query}",
                answers=answers,
                component_id=component_id,
                source_ids=[record["id"] for record in matches],
            )
        )
    return examples


def make_example(
    *,
    task: str,
    direction: str,
    query: str,
    prompt: str,
    answers: list[str],
    component_id: str,
    source_ids: list[str],
) -> dict:
    return {
        "id": example_id(task, query),
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "; ".join(answers)},
        ],
        "metadata": {
            "task": task,
            "direction": direction,
            "component_id": component_id,
            "query": query,
            "accepted_equivalents": answers,
            "source_record_ids": sorted(set(source_ids)),
            "data_quality": "silver_source_extracted_unreviewed",
            "requires_speaker_validation": True,
            "permission_status": "confirmed_for_this_project",
            "permission_reference": "../PERMISSION.md",
            "contains_authored_marubo_sentence": False,
        },
    }


def assign_splits(examples_by_component: dict[str, list[dict]]) -> dict[str, list[dict]]:
    totals = Counter()
    for examples in examples_by_component.values():
        totals.update(example["metadata"]["task"] for example in examples)
    total_examples = sum(totals.values())
    targets = {
        split: {
            "total": max(total_examples * ratio, 1),
            **{task: max(count * ratio, 1) for task, count in totals.items()},
        }
        for split, ratio in SPLIT_RATIOS.items()
    }
    assigned = {split: [] for split in SPLIT_RATIOS}
    counts = {split: Counter() for split in SPLIT_RATIOS}

    ordered = sorted(examples_by_component.items(), key=lambda item: (-len(item[1]), item[0]))
    for _, examples in ordered:
        component_tasks = Counter(example["metadata"]["task"] for example in examples)

        def fill_score(split: str) -> tuple[float, int]:
            ratios = [counts[split]["total"] / targets[split]["total"]]
            ratios.extend(
                counts[split][task] / targets[split][task]
                for task in component_tasks
            )
            split_order = list(SPLIT_RATIOS).index(split)
            return sum(ratios) / len(ratios), split_order

        selected = min(SPLIT_RATIOS, key=fill_score)
        assigned[selected].extend(examples)
        counts[selected]["total"] += len(examples)
        counts[selected].update(component_tasks)

    for split in assigned:
        assigned[split].sort(key=lambda example: hashlib.sha256(example["id"].encode()).hexdigest())
    return assigned


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report(
    canonical: list[dict],
    tiers: dict[str, list[dict]],
    splits: dict[str, list[dict]],
) -> dict:
    split_components = {
        split: {row["metadata"]["component_id"] for row in rows}
        for split, rows in splits.items()
    }
    overlaps = {}
    names = list(splits)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlaps[f"{left}_{right}"] = len(split_components[left] & split_components[right])

    prompts: defaultdict[str, set[str]] = defaultdict(set)
    for rows in splits.values():
        for row in rows:
            prompts[row["messages"][0]["content"]].add(row["messages"][1]["content"])

    return {
        "package": "marubo_sft_v2",
        "preparation_version": PREPARATION_VERSION,
        "prepared_on": PREPARATION_DATE,
        "purpose": "MVP lexical; does not represent sentence-level fluency",
        "permission_status": "confirmed_for_this_project",
        "permission_reference": "../PERMISSION.md",
        "source_lexicon_records": len(canonical),
        "quality_tiers": {tier: len(records) for tier, records in tiers.items()},
        "training_eligible_records": len(tiers["silver"]),
        "total_sft_examples": sum(len(rows) for rows in splits.values()),
        "split_examples": {split: len(rows) for split, rows in splits.items()},
        "split_percentages": {
            split: round(100 * len(rows) / sum(len(value) for value in splits.values()), 2)
            for split, rows in splits.items()
        },
        "split_task_counts": {
            split: dict(Counter(row["metadata"]["task"] for row in rows))
            for split, rows in splits.items()
        },
        "split_component_counts": {
            split: len(component_ids) for split, component_ids in split_components.items()
        },
        "validations": {
            "component_overlaps": overlaps,
            "conflicting_prompt_groups": sum(len(answers) > 1 for answers in prompts.values()),
            "all_records_require_speaker_validation": all(
                row["metadata"]["requires_speaker_validation"]
                for rows in splits.values()
                for row in rows
            ),
            "all_records_have_project_permission": all(
                row["metadata"]["permission_status"] == "confirmed_for_this_project"
                for rows in splits.values()
                for row in rows
            ),
            "authored_marubo_sentences": 0,
        },
    }


def build_manifest(root: Path, report: dict) -> dict:
    candidates = [
        root / "raw/dicionario_portugues_marubo.xlsx",
        root / "lexicon/lexicon.jsonl",
        root / "lexicon/prepared_lexicon.jsonl",
        root / "lexicon/training_eligible.jsonl",
        root / "lexicon/low_confidence.jsonl",
        root / "lexicon/grammatical_entries.jsonl",
        root / "lexicon/quarantine.jsonl",
        root / "sft_v2/train.jsonl",
        root / "sft_v2/validation.jsonl",
        root / "sft_v2/test.jsonl",
        root / "sft_v2/sft.schema.json",
        root / "sft_v2/dataset_card.md",
        root / "sft_v2/tokenizer_report.json",
        root / "sft_v2/validation_report.json",
        root / "scripts/prepare_dataset.py",
        root / "scripts/validate_dataset.py",
        root / "scripts/evaluate_predictions.py",
        root / "README.md",
        root / "PERMISSION.md",
    ]
    files = {}
    for path in candidates:
        if path.exists():
            files[path.relative_to(root).as_posix()] = {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
    return {
        "dataset": "marubo-portuguese-lexical",
        "package": "marubo_sft_v2",
        "preparation_version": PREPARATION_VERSION,
        "prepared_on": PREPARATION_DATE,
        "permission_status": report["permission_status"],
        "permission_reference": "PERMISSION.md",
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="dataset_marubo directory",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    lexicon_dir = root / "lexicon"
    output_dir = root / "sft_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical = read_jsonl(lexicon_dir / "lexicon.jsonl")
    prepared = [annotate(record) for record in canonical]
    tiers: dict[str, list[dict]] = {tier: [] for tier in ("silver", "low_confidence", "grammatical", "quarantine")}
    for record in prepared:
        tiers[record["quality"]["preparation_tier"]].append(record)

    write_jsonl(lexicon_dir / "prepared_lexicon.jsonl", prepared)
    write_jsonl(lexicon_dir / "training_eligible.jsonl", tiers["silver"])
    write_jsonl(lexicon_dir / "low_confidence.jsonl", tiers["low_confidence"])
    write_jsonl(lexicon_dir / "grammatical_entries.jsonl", tiers["grammatical"])
    write_jsonl(lexicon_dir / "quarantine.jsonl", tiers["quarantine"])

    components = build_components(tiers["silver"])
    examples_by_component = {
        component_id: build_examples(component_id, records)
        for component_id, records in components.items()
    }
    splits = assign_splits(examples_by_component)
    for split, rows in splits.items():
        write_jsonl(output_dir / f"{split}.jsonl", rows)

    report = build_report(canonical, tiers, splits)
    write_json(output_dir / "validation_report.json", report)
    write_json(root / "manifest.json", build_manifest(root, report))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
