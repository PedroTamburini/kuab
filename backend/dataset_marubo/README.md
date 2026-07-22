# Dataset Marubo–Português

Este diretório contém um léxico Marubo–Português e pacotes derivados para um MVP de tradução lexical. Ele não deve ser apresentado como corpus suficiente para tradução livre de frases.

## Fonte e versões

- `raw/`: planilha-fonte preservada.
- `lexicon/lexicon.jsonl`: léxico canônico extraído, preservado sem limpeza destrutiva.
- `lexicon/prepared_lexicon.jsonl`: léxico anotado com nível de preparação e permissão do projeto.
- `lexicon/training_eligible.jsonl`: registros exatos elegíveis para o SFT lexical.
- `lexicon/low_confidence.jsonl`: correspondências obtidas somente por reversão.
- `lexicon/grammatical_entries.jsonl`: códigos e funções gramaticais que não são traduções portuguesas comuns.
- `lexicon/quarantine.jsonl`: glosas desconhecidas ou explicitamente incertas.
- `sft_v1/`: primeira geração, mantida apenas como histórico e não recomendada para treinamento.
- `sft_v2/`: pacote conservador atual, sem prompts contraditórios e com splits por componente lexical.
- `scripts/`: geração, validação e avaliação reproduzíveis.
- `manifest.json`: hashes e tamanhos dos principais artefatos.

## Permissão e validação linguística

O responsável pelo projeto confirmou permissão para utilizar estes dados no projeto, inclusive para preparação, treinamento e teste de modelos. Consulte [`PERMISSION.md`](PERMISSION.md).

A permissão de uso não substitui validação linguística. Todos os registros continuam marcados como não revisados e requerem validação por falantes Marubo antes de uma avaliação conclusiva ou disponibilização de um tradutor.

## Gerar e validar

Execute a partir deste diretório:

```powershell
python scripts/prepare_dataset.py
python scripts/validate_dataset.py
```

Os scripts usam somente a biblioteca padrão do Python e não treinam nem consultam modelos.

A auditoria de tokenizer permanece explicitamente como `not_run` em `sft_v2/tokenizer_report.json`, pois deve usar o modelo e a revisão exatos que forem escolhidos posteriormente.

## Avaliação futura

O script `scripts/evaluate_predictions.py` recebe um JSONL com os campos `id` e `prediction` e compara conjuntos de equivalentes separados por `;`:

```powershell
python scripts/evaluate_predictions.py predictions.jsonl
```

O teste de `sft_v2` é provisório até ser revisado por falantes.
