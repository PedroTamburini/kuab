# Marubo SFT v2 — MVP lexical conservador

## Objetivo

Este pacote prepara exemplos de tradução lexical Marubo ↔ Português para treinamento e avaliação futura. Ele não contém corpus paralelo suficiente para tradução livre de frases e não representa fluência em Marubo.

## Origem e permissão

Os exemplos são derivados exclusivamente do léxico canônico deste repositório. O responsável pelo projeto confirmou permissão de uso para preparação, treinamento e teste; consulte [`../PERMISSION.md`](../PERMISSION.md).

A permissão para redistribuição pública não está documentada no repositório. Todos os registros permanecem com `requires_speaker_validation: true`.

## Política de inclusão

Somente registros com correspondência exata de glosa portuguesa e sem marca explícita de incerteza entram no SFT principal. Os demais permanecem preservados em subconjuntos separados:

- `silver`: elegível para o baseline lexical, ainda não revisado por falantes;
- `low_confidence`: relação recuperada apenas por reversão;
- `grammatical`: código ou função gramatical, não tradução portuguesa comum;
- `quarantine`: glosa desconhecida ou explicitamente incerta.

## Exemplos e conflitos

Cada consulta lexical aparece uma única vez. Quando há vários equivalentes conhecidos, eles são agregados na mesma resposta e registrados em `metadata.accepted_equivalents`. Isso evita ensinar respostas contraditórias para a mesma pergunta.

## Splits

Os componentes conectados do grafo lexical são mantidos integralmente em um único split. A atribuição determinística busca aproximadamente 80% treino, 10% validação e 10% teste, cobrindo as duas direções em todos os splits.

## Formato

Cada linha é um objeto JSON com `id`, duas mensagens (`user`, `assistant`) e metadados. Não há tokens especiais de Llama, Gemma ou outro modelo. O chat template do tokenizer escolhido deverá ser aplicado apenas no pipeline de treinamento.

## Limitações

- nenhum exemplo foi confirmado por falantes Marubo neste pacote;
- não há sentenças paralelas suficientes para avaliar tradução contextual;
- métricas automáticas medem apenas recuperação lexical;
- formas homônimas e variantes podem exigir contexto ausente no léxico;
- a auditoria do tokenizer depende da escolha futura do modelo exato.
