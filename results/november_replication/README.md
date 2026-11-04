# Repeated tabular-evidence study

**The main conclusion is that GPT-5.6 Luna usually follows supplied tabular evidence accurately, but the inline experiments do not establish a consistent advantage for CSV, JSON, XML, or TXT. Exact-input repetitions reveal real variability. Actual CSV uploads expose an additional numeric-fidelity and retrieval problem that is separate from the inline serialization comparison.**

## What was run

- 8,376 planned attempts; 8,373 completed model responses. Three API failures were retained without retry (one rate limit and two server errors).
- Three query types: direct-ID lookup, selection by multiple attributes, and retrieval across two linked tables.
- Four formats, three calls per identical non-calibration input, original/altered values, named/neutral descriptions, 80/400-row primary tables, and separate 800-row stress cases.
- The primary comparison uses 36 fresh sampled blocks from Titanic, wine, and medical data. IBM, avocado, and credit card data add direct-lookup coverage. File uploads, synthetic controls, and empirical edits are separate arms.
- Medium reasoning, fresh requests, no tools, and unchanged frozen primary scoring throughout.

## Primary results

The primary had 5,104/5,184 strictly correct attempts (98.457% end-to-end). Among completed model responses it was 5,104/5,183 (98.476%).

| Query type | Entirely correct completed requests | Accuracy |
| --- | --- | --- |
| Direct ID | 1,726/1,727 | 99.942% |
| Attribute selection | 1,678/1,728 | 97.106% |
| Two-table retrieval | 1,700/1,728 | 98.380% |

All three prespecified pooled format contrasts include zero in their descriptive and family-adjusted block-bootstrap intervals. Task-specific raw rankings differ. This supports no established stable format winner, not equivalence. The extra three datasets passed all 1,152 direct-lookup requests.

## Why repetitions were worthwhile

Among 1,727 primary inputs with three completed responses, 45 had mixed correctness and 8 failed all three repetitions. The remaining 1,674 passed all three. Repetitions measure reliability on a fixed input; they are not new independent sampled tables. We averaged correctness indicators, never numerical answer values or majority-vote replacements.

The primary's 75 incorrect present-value answers include 62 false NOT_FOUND responses and 13 other supplied values. Only six completed answers to genuinely absent queries were wrong. Errors also occurred in 80-row tables, so the pattern is not simply that larger tables fail. No altered-value error in any arm returned the replaced original. This is an observed behavior, not proof about training-data membership or internal memory.

## Actual files reveal a different issue

Across exactly matched neutral inputs, inline delivery passed 862/864 attempts (99.769%), compared with 811/864 file attempts (93.866%). The exploratory paired block difference was -5.903 percentage points, with a descriptive 95% interval of [-8.218, -3.588]. Two file attempts were server errors.

The loss was concentrated in native CSV uploads: 167/216 strictly correct versus 215/216 for matched inline CSV. Other uploaded formats stayed close to their inline baselines.

Eighteen CSV numeric cell answers differed from wine ground truth by only 1e-16. Seventeen requests failed solely on that precision difference. A separately labeled post-collection sensitivity allowing numeric differences up to 1e-12 improves file performance to 828/864, but the overall matched delivery gap remains -3.935 points (descriptive 95% interval [-4.745, -3.125]). The frozen exact scores are unchanged. Remaining CSV failures were mostly false NOT_FOUND on present records.

This is a file-delivery workflow result. CSV is processed through a spreadsheet augmentation path, while the other tested text formats use text extraction. These data do not identify whether parsing, the augmented representation, or model inference caused the failures. Repeated file queries reused uploaded file IDs; variability across independent re-uploads was not tested.

## Other checks

- Empirical edits: 430/432 correct. Plausible source-field values did not produce a clear decrease relative to their paired uniform-edit baselines in this selected subset.
- 800-row stress: 421/432 correct. Format rankings varied by task; this arm has only two blocks per source and is descriptive.
- Synthetic controls: 273/288 correct. Generated tables also elicited errors, but they are not distribution-matched copies of the real sources.

## Do we need more broad collection?

**There is enough evidence now to write the scoped exploratory conclusion. More generic direct-ID runs or simply repeating the whole batch are not the next priority.** If more work is needed, the most informative next experiment is a targeted CSV control: compare identical CSV bytes through spreadsheet versus text handling and compare raw versus canonicalized numeric values/selectors, on new matched blocks with three repetitions. That would address the observed pipeline pattern. General claims across LLMs still require additional models and source/task coverage.

## Methodological disclosures

The first development calibration stopped under its all-correct rule at 23/24. Before any main response, a separately versioned technical-completion/schema gate was documented; all development outputs, including the error, were retained. Main prompts, sampled tables, order, repetitions, and scoring were unchanged. The work is exploratory rather than an untouched public preregistration.

After the rate-limit stop, only unsent requests resumed at lower concurrency. No failed or incorrect attempt was silently replaced. All 300 uploaded files have confirmed deletion. Actual runtime versions are recorded and differ from the shared lock; the hosted model alias is not an immutable snapshot. Tables overlap in source records, so thousands of calls are not thousands of independent tables.

Conservative accounted token spend was $27.4775, below the $50 backstop; the standard uncached token-price estimate was $21.3818. Neither is an exact invoice amount. Raw outputs and cases remain local and ignored by Git. This directory publishes reviewed aggregates and plots.

See [detailed findings](REPORT.md), [technical report](REPORT.md), [audit](audit.json), and [precision sensitivity](file_precision_sensitivity.json).

## Artifacts and reproduction

These aggregate files and plots can be read on a fresh clone without datasets, API access, or withheld logs. The experiment code and frozen protocols are under `../../experiments/`. The historical results notebook has not been extended to this study.

Rebuilding response-level analyses requires the local frozen run under `results/overall_replication_20261103_v2/`. Restore the authorized local artifacts matching the hashes in provenance.json; do not substitute arbitrary datasets or rerun paid requests to reconstruct historical responses. See ../../experiments/README.md for offline commands.
