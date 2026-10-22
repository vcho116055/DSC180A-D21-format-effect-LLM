# Experimental methodology archive

These technical references describe the experiments actually recorded in this personal repository. They were written retrospectively on October 21, 2026, from the source code, frozen prompts, manifests, and response logs. They are not new preregistrations or replacements for the original artifacts. No additional model requests were made to prepare them.

## Rounds

| Round | Collection date, Los Angeles | Requested model | Experimental requests | Technical reference |
|---|---|---|---:|---|
| 1. Initial counting and isolation pilot | October 13, 2026 | `gpt-6-luna` | 20 | [Round 1 methodology](round1_counting_pilot.md) |
| 2. Main lookup study and planned controls | October 21, 2026 | `gpt-5.6-luna` | 358 | [Round 2 methodology](round2_lookup_study.md) |
| 3. Revised knowledge probes and recognizable-record follow-up | October 21, 2026 | `gpt-5.6-luna` | 24 | [Round 3 methodology](round3_knowledge_followup.md) |
| 4. Attribute selection and two-table retrieval | October 21, 2026 | `gpt-5.6-luna` | 552 completed | [Round 4 methodology](round4_selection_and_joins.md) |

Round 2 includes 288 primary comparisons and 70 secondary requests. Its six original no-table probes were incomplete. All Round 1 and Round 3 experimental requests completed. The Week 4 total of 382 is Round 2 plus Round 3, not an additional run. Four failed Round 1 launch attempts are retained as operational diagnostics and excluded from the 20 successful experimental requests. Other informal connectivity checks are not reconstructed as experiments without corresponding trial artifacts.

Round 4 is a later extension and is not included in the earlier 382-request total. Its first four calibration dispatches failed at the transport layer and are preserved separately from the restarted calibration. See its technical reference for the operational deviation and the calibration gate.

## How to use these references

Each document covers the question, data and transformations, experimental conditions, prompts, execution settings, scoring, recorded outcomes, limitations, and reproduction procedure. Exact prompts and final model outputs remain in the linked JSONL files. The technical documents explain those files rather than duplicating every table payload.

Class-facing summaries, personal reflections, and presenter notes remain in the personal repository and are excluded from this shared checkout. The combined report (`../results/week4_overview/REPORT.md`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md)) summarizes outcomes across Rounds 2 and 3.

## Interpretation shared across rounds

- A request is one API invocation. A queried cell is one answer inside that request. A sampled table is a shared block reused across experimental conditions. These are different units and should not be counted as independent replications interchangeably.
- Ground truth is the value in the supplied local table. The repository does not independently authenticate the downloaded dataset versions or establish membership in any model's training corpus.
- A familiar original answer appearing in a changed-data task is a behavioral observation. It does not identify an internal mechanism or prove training-data leakage.
- Fresh requests omit earlier conversation messages, except for Round 1's explicit-history positive control. This is an implemented request property, not proof that every possible form of server-side state is absent.
- Local random seeds reproduce table construction and request ordering. No model sampling seed was set, and identical model outputs on rerun are not guaranteed by these seeds.
- The model changed between Rounds 1 and 2. Methodology, prompts, data projections, and output requirements changed too. Cross-round differences do not isolate the effect of any one change.
- The later explanation for preferring an older generation was an expectation of a more stable baseline. Stability was not measured here. The saved model identifiers are not dated snapshots, and the artifacts do not establish unchanged model weights over the quarter.
- Xiao's discussions informed the design, but these logs contain the locally executed experiments only. His separately reported GPT-3.5/Iris tests are not reconstructed without their prompts, data slices, and responses.

## Recorded data identities

The following hashes were verified against the current local files when these references were written. Titanic's hash also matches the Round 1 metadata. The other two hashes match the Round 2 manifest.

| Local file | Source rows | Source columns | SHA-256 |
|---|---:|---:|---|
| `data/titanic.csv` | 1,309 | 28 | `5c3c684032fa169dcc8b4853e06a9a5296fbb2f1b8061a5527710c418f5feac4` |
| `data/redwine.csv` | 1,599 | 12 | `d6a0d9bd24806944818795f22500c46cb6424cbff517aacda36595d3ed9b2daa` |
| `data/medicalcost.csv` | 1,338 | 7 | `388eff679557d08ac19f463d025de5e0b4adc482537c8456d19934d78621fd47` |

Only these three of the ten available target datasets were used in the recorded rounds. Round 1 used Titanic alone plus generated binary tables. Round 2 used all three plus generated controls. Round 3 used the same saved probe targets and a new Titanic table.

## Offline verification

The shared checkout contains code and aggregate results; row-level artifacts remain local and are excluded from Git. Restore the required files using the [transfer review](../results/TRANSFER_REVIEW.md) before running artifact-dependent tests or analysis. Full source-hash audits additionally need the exact authorized local datasets. From the repository root, these commands validate or summarize restored artifacts without making model requests:

```powershell
python exploratory_luna.py
python -m unittest experiments.test_week4_study -v
python experiments/week4_study.py analyze --directory results/week4_lookup
python -m experiments.summarize_week4
```

The first command regenerates the pilot cases and prints their expected answers. It does not itself regrade the saved pilot responses. The last two commands regenerate derived analysis files. Preserve raw prompts, manifests, and response logs when reviewing or extending the work.
