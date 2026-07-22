# Léxico português–marubo para IA

Pacote canônico em JSON Lines gerado a partir da planilha português–marubo e enriquecido com os verbetes principais estruturados da API oficial do Webonary.

## Arquivos

- `lexicon.jsonl`: um registro lexical por relação de sentido recuperada.
- `lexicon.schema.json`: esquema JSON dos registros.
- `rejected_records.jsonl`: registros que não puderam ser convertidos com segurança.
- `validation_report.json`: contagens e verificações.
- `prepared_lexicon.jsonl`: cópia derivada com nível de preparação e permissão registrada.
- `training_eligible.jsonl`: correspondências exatas elegíveis para o SFT lexical.
- `low_confidence.jsonl`: correspondências recuperadas apenas por reversão.
- `grammatical_entries.jsonl`: códigos gramaticais separados das traduções comuns.
- `quarantine.jsonl`: entradas desconhecidas ou explicitamente incertas.

## Resumo

- Registros da planilha de relações: 2435
- Registros lexicais produzidos: 2211
- Lemas marubo distintos: 1936
- Formas portuguesas distintas: 1868
- Registros recuperados que antes apareciam apenas como números: 224
- Registros rejeitados: 0

## Uso recomendado

Este arquivo é a fonte lexical canônica. Não o envie diretamente como conversa para Llama ou Gemma. Gere exemplos de instrução separados e aplique o chat template do tokenizer escolhido durante o pré-processamento.

Os campos `part_of_speech`, `semantic_domains` e `examples` são preenchidos quando existem na fonte. Valores ausentes não foram inventados. Todos os registros permanecem com `requires_speaker_validation: true`.

## Permissão e atenção

O responsável pelo projeto confirmou permissão de uso dos dados para preparação, treinamento e teste neste projeto. A declaração e seus limites estão registrados em `../PERMISSION.md`; a permissão de redistribuição pública não está documentada no repositório.

A publicação identifica o compilador como Christopher Sean Smith e informa © 2025 SIL Global. A autorização de uso não substitui validação por falantes nem governança apropriada com a comunidade Marubo.
