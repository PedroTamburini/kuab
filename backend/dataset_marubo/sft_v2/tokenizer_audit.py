#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

parser = argparse.ArgumentParser(description="Audita a fragmentação de lemas Marubo em um ou mais tokenizers.")
parser.add_argument("models", nargs="+", help="Nomes Hugging Face ou caminhos locais dos modelos/tokenizers")
parser.add_argument("--lexicon", default="lexicon.jsonl")
parser.add_argument("--output", default="tokenizer_model_results.json")
args = parser.parse_args()

records = [json.loads(line) for line in Path(args.lexicon).read_text(encoding="utf-8").splitlines() if line.strip()]
lemmas = sorted({record["lemma_marubo"] for record in records})
results = []

for model in args.models:
    tokenizer = AutoTokenizer.from_pretrained(model)
    counts = [len(tokenizer.encode(lemma, add_special_tokens=False)) for lemma in lemmas]
    fragmented = sorted(
        ({"lemma": lemma, "token_count": count} for lemma, count in zip(lemmas, counts)),
        key=lambda item: (-item["token_count"], item["lemma"]),
    )
    results.append({
        "model": model,
        "lemmas": len(lemmas),
        "mean_tokens_per_lemma": sum(counts) / len(counts),
        "max_tokens_per_lemma": max(counts),
        "single_token_lemmas": sum(count == 1 for count in counts),
        "top_fragmented_lemmas": fragmented[:50],
    })

Path(args.output).write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": args.output, "models": len(results)}, ensure_ascii=False))
