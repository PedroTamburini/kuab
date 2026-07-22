#!/usr/bin/env python3
"""Validate the derived Marubo SFT v2 package without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


EXAMPLE_ID = re.compile(r"example_[a-f0-9]{20}")
COMPONENT_ID = re.compile(r"component_[a-f0-9]{16}")


def read_jsonl(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
    return records


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sft_record(
    record: dict,
    path: Path,
    eligible_source_ids: set[str],
    errors: list[str],
) -> None:
    required = {"id", "messages", "metadata"}
    if set(record) != required:
        errors.append(f"{path}: invalid top-level keys for {record.get('id')}")
        return
    if not EXAMPLE_ID.fullmatch(record["id"]):
        errors.append(f"{path}: invalid example id {record['id']}")
    messages = record["messages"]
    if len(messages) != 2 or [message.get("role") for message in messages] != ["user", "assistant"]:
        errors.append(f"{path}: invalid role sequence for {record['id']}")
    if any(not str(message.get("content", "")).strip() for message in messages):
        errors.append(f"{path}: empty message for {record['id']}")
    metadata = record["metadata"]
    expected_metadata = {
        "task",
        "direction",
        "component_id",
        "query",
        "accepted_equivalents",
        "source_record_ids",
        "data_quality",
        "requires_speaker_validation",
        "permission_status",
        "permission_reference",
        "contains_authored_marubo_sentence",
    }
    if set(metadata) != expected_metadata:
        errors.append(f"{path}: invalid metadata keys for {record['id']}")
    if not COMPONENT_ID.fullmatch(metadata.get("component_id", "")):
        errors.append(f"{path}: invalid component id for {record['id']}")
    expected_directions = {
        "marubo_to_pt_lexical": "mzr_to_pt-BR",
        "pt_to_marubo_lexical": "pt-BR_to_mzr",
    }
    if expected_directions.get(metadata.get("task")) != metadata.get("direction"):
        errors.append(f"{path}: task/direction mismatch for {record['id']}")
    if metadata.get("permission_status") != "confirmed_for_this_project":
        errors.append(f"{path}: permission not confirmed for {record['id']}")
    if metadata.get("requires_speaker_validation") is not True:
        errors.append(f"{path}: missing speaker-validation flag for {record['id']}")
    expected_answer = {normalized(value) for value in metadata.get("accepted_equivalents", [])}
    actual_answer = {normalized(value) for value in messages[1]["content"].split(";")}
    if expected_answer != actual_answer:
        errors.append(f"{path}: assistant answer/reference mismatch for {record['id']}")
    if len(expected_answer) != len(metadata.get("accepted_equivalents", [])):
        errors.append(f"{path}: duplicate normalized equivalent for {record['id']}")
    source_ids = set(metadata.get("source_record_ids", []))
    if not source_ids or not source_ids <= eligible_source_ids:
        errors.append(f"{path}: invalid source record references for {record['id']}")
    strings = [record["id"]]
    strings.extend(message["content"] for message in messages)
    strings.extend(metadata.get("accepted_equivalents", []))
    if any(unicodedata.normalize("NFC", value) != value for value in strings):
        errors.append(f"{path}: non-NFC text for {record['id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    canonical = read_jsonl(root / "lexicon/lexicon.jsonl")
    prepared = read_jsonl(root / "lexicon/prepared_lexicon.jsonl")
    tier_paths = {
        "silver": root / "lexicon/training_eligible.jsonl",
        "low_confidence": root / "lexicon/low_confidence.jsonl",
        "grammatical": root / "lexicon/grammatical_entries.jsonl",
        "quarantine": root / "lexicon/quarantine.jsonl",
    }
    tiers = {name: read_jsonl(path) for name, path in tier_paths.items()}
    eligible_source_ids = {record["id"] for record in tiers["silver"]}

    canonical_ids = {record["id"] for record in canonical}
    prepared_ids = {record["id"] for record in prepared}
    if len(canonical_ids) != len(canonical) or canonical_ids != prepared_ids:
        errors.append("canonical/prepared lexicon IDs differ or are duplicated")

    seen_tier_ids: set[str] = set()
    for tier, records in tiers.items():
        ids = {record["id"] for record in records}
        if len(ids) != len(records):
            errors.append(f"duplicate IDs in tier {tier}")
        if seen_tier_ids & ids:
            errors.append(f"overlapping IDs in tier {tier}")
        seen_tier_ids |= ids
        for record in records:
            if record["quality"].get("preparation_tier") != tier:
                errors.append(f"wrong tier annotation for {record['id']}")
    if seen_tier_ids != canonical_ids:
        errors.append("quality tiers do not form a complete partition")

    split_rows = {}
    split_components = {}
    all_ids: set[str] = set()
    prompts: defaultdict[str, set[str]] = defaultdict(set)
    for split in ("train", "validation", "test"):
        path = root / f"sft_v2/{split}.jsonl"
        rows = read_jsonl(path)
        split_rows[split] = rows
        split_components[split] = {row["metadata"]["component_id"] for row in rows}
        for row in rows:
            validate_sft_record(row, path, eligible_source_ids, errors)
            if row["id"] in all_ids:
                errors.append(f"duplicate SFT id across splits: {row['id']}")
            all_ids.add(row["id"])
            prompts[row["messages"][0]["content"]].add(row["messages"][1]["content"])
        tasks = Counter(row["metadata"]["task"] for row in rows)
        if set(tasks) != {"marubo_to_pt_lexical", "pt_to_marubo_lexical"}:
            errors.append(f"{split} does not cover both translation directions")

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if split_components[left] & split_components[right]:
            errors.append(f"component leakage between {left} and {right}")
    if any(len(answers) > 1 for answers in prompts.values()):
        errors.append("identical prompts have conflicting answers")

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("permission_status") != "confirmed_for_this_project":
        errors.append("manifest does not record project permission")
    for relative_path, expected in manifest.get("files", {}).items():
        artifact = root / relative_path
        if not artifact.is_file():
            errors.append(f"manifest artifact is missing: {relative_path}")
            continue
        if artifact.stat().st_size != expected.get("bytes"):
            errors.append(f"manifest size mismatch: {relative_path}")
        if sha256(artifact) != expected.get("sha256"):
            errors.append(f"manifest hash mismatch: {relative_path}")

    report = {
        "status": "failed" if errors else "passed",
        "canonical_records": len(canonical),
        "prepared_records": len(prepared),
        "tier_counts": {name: len(records) for name, records in tiers.items()},
        "split_counts": {name: len(records) for name, records in split_rows.items()},
        "unique_sft_ids": len(all_ids),
        "manifest_files_checked": len(manifest.get("files", {})),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
