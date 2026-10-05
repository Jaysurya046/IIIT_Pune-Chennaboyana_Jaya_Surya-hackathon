# External Sentiment Benchmark

## Scope and Claim Boundary

Phases 12 and 13 add a local benchmark command that evaluates the same ordered CSV with
the project's explicit `deterministic` and `model` NLP implementations:

```bash
python -m risk_engine benchmark \
  --dataset data/runtime/phase12-benchmark/financial_phrasebank_allagree.csv \
  --text-col sentence \
  --label-col label \
  --output data/runtime/phase12-benchmark/results.json \
  --markdown-output data/runtime/phase12-benchmark/results.md
```

The command accepts UTF-8 CSV files, requires every row to contain text and a supported
label, and fails on missing columns, blank values, unsupported labels, unavailable model
dependencies, or unavailable weights. It never replaces model mode with deterministic
mode. JSON is written to standard output; the optional output paths retain the same JSON
and a presentation-ready Markdown table.

The classification metrics measure three-class financial sentiment. Phase 13 also runs
each record through entity resolution, event classification, and impact scoring, then
reports how often `impact_score > 7`. It does not run portfolio valuation or persist the
generated benchmark signals.

## Dataset Source and Permission

- **Dataset:** Financial PhraseBank v1.0, `sentences_allagree` configuration.
- **Authors:** Pekka Malo, Ankur Sinha, Pyry Takala, Pekka Korhonen, and Jyrki Wallenius.
- **Immutable distribution reference:** Hugging Face dataset commit
  [`598b6aad98f7c8d67be161b12a4b5f2497e07edd`](https://huggingface.co/datasets/takala/financial_phrasebank/commit/598b6aad98f7c8d67be161b12a4b5f2497e07edd).
- **Research description:** [Good Debt or Bad Debt: Detecting Semantic Orientations in
  Economic Texts](https://arxiv.org/abs/1307.5336).
- **Archive SHA-256:**
  `0e1a06c4900fdae46091d031068601e3773ba067c7cecb5b0da1dcba5ce989a6`.
- **License:** Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported
  (CC BY-NC-SA 3.0), as stated in the dataset card and included `License.txt`.

The dataset is used here only for academic, non-commercial evaluation. Commercial use
requires separate permission from the dataset authors. The source sentences and derived
CSV are not committed; they remain under ignored `data/runtime/`. This repository adds no
dataset entry to `data/sources.yaml` because that manifest covers committed artifacts.

## Acquisition and Selection

1. Download `data/FinancialPhraseBank-v1.0.zip` from the immutable distribution commit.
2. Verify the archive SHA-256 above before extraction.
3. Extract `FinancialPhraseBank-v1.0/Sentences_AllAgree.txt` only.
4. Decode the source file as ISO-8859-1. Split each non-empty record at its final `@`:
   the left side becomes `sentence` and the right side becomes `label`.
5. Write a UTF-8 CSV with the exact headers `sentence,label`. Do not shuffle, sample,
   deduplicate, relabel, or otherwise filter rows.

The resulting local evaluation file contained all 2,264 100%-agreement records and had
SHA-256
`a7a3128b1380b32d27f28b29c5f57c662492fd6ae6293a778d02593ef5bedae1`.
The class distribution was 303 negative, 1,391 neutral, and 570 positive records.

The command normalizes case and surrounding whitespace. It accepts the named labels
`negative`, `neutral`, and `positive`, plus the dataset-card numeric mapping `0`, `1`,
and `2`, respectively. No invalid record is silently skipped.

## Recorded Environment

- Run date: 2026-10-04 (Asia/Calcutta).
- Operating system: Windows 11, build 26200, AMD64.
- Processor: Intel64 Family 6 Model 186; Torch used 10 CPU threads.
- Python: 3.13.5.
- Torch: 2.14.1+cpu.
- Transformers: 5.18.0.
- Sentence Transformers: 5.7.0.
- Deterministic implementation: `deterministic-sentiment-v1`.
- Model implementation: `ProsusAI/finbert` pinned to revision
  `4556d13015211d73dccd3fdd39d39232506f3e43`.
- Model event classifier: `sentence-transformers/all-MiniLM-L6-v2` pinned to revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

The Phase 13 full-engine cold command took 385.6 seconds including first-run MiniLM
acquisition. That duration is setup evidence, not a throughput claim or production SLA.

## Results

Confusion cells are `predicted negative / neutral / positive`; each column represents
one actual class. Counts sum to the corresponding class support and to 2,264 overall.

| Mode | Model/version | Accuracy | Macro-F1 | Triggered (>7) | Trigger rate | Actual negative → N/Neu/P | Actual neutral → N/Neu/P | Actual positive → N/Neu/P |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic | deterministic-sentiment-v1 | 0.6793 | 0.4305 | 0/2264 | 0.0000 | 13/199/91 | 1/1350/40 | 31/364/175 |
| model | ProsusAI/finbert@4556d13015211d73dccd3fdd39d39232506f3e43 | 0.9717 | 0.9625 | 0/2264 | 0.0000 | 298/1/4 | 19/1345/27 | 12/1/557 |

Accuracy is the fraction of exactly matched labels. Per-class F1 uses
`2TP / (2TP + FP + FN)` with zero for an undefined class, and macro-F1 is the unweighted
mean across negative, neutral, and positive. Metrics are implemented locally; no scoring
package or network service participates.

For trigger comparison, every row is converted in memory to non-synthetic external
benchmark provenance at the fixed timestamp `2026-01-01T00:00:00Z`. All rows retain one
common source, no corroboration is invented, and entity relevance comes only from the
unchanged fictional issuer resolver. Both modes produced 0 scores above 7. This is an
honest result: the sentiment benchmark alone does not create enough combined event,
entity, corroboration, and sentiment evidence to cross the strict trigger.

## Interpretation and Limitations

- The high FinBERT score is **not an out-of-sample generalization estimate**. The
  published model card states that Financial PhraseBank was used to fine-tune FinBERT,
  and the dataset has no official train/test split. Training overlap may materially
  inflate this result.
- The all-agree configuration selects clearer examples and is class-imbalanced, with
  neutral representing about 61% of records. Accuracy therefore hides minority-class
  behavior; macro-F1 and confusion counts must accompany it.
- The deterministic implementation is intentionally a small transparent lexicon, not a
  trained competitor. Its low negative-class recall and broad neutral prediction are
  visible in the confusion matrix.
- The source contains English financial-news sentences about listed companies in a
  particular collection context. It does not establish performance on social posts,
  other languages, long documents, current events, or the project's fictional issuers.
- Trigger rate is descriptive pipeline behavior under the fixed benchmark provenance,
  not a labelled trigger-quality metric. Financial PhraseBank provides sentiment labels,
  not event severity, entity relevance, or ground-truth stress-trigger annotations.
- Results depend on the exact dataset bytes, model revision, libraries, and runtime
  recorded above. They do not imply investment performance or validate stress losses.

Phase 17's bounded inflection and negation rules changed the deterministic benchmark
from 0.6767 accuracy / 0.4302 macro-F1 to 0.6793 / 0.4305. The model row is unchanged.
This table is reproducible implementation evidence and a transparent mode comparison;
it is not a claim of independent state-of-the-art model quality.
