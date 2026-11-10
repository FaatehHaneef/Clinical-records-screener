# Design and implementation

This document explains how CRS is built, the decisions behind it and what was learned along the way. The problem it solves is defined in [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md), and the full evaluation is in the [paper](../report/i230688_A_Assignment2-Report.pdf).

## System overview

| Component | Location | Purpose |
|---|---|---|
| Data pipeline | `screener/data/` | Patient-grouped split, sentence handling, prompts and targets |
| Training | `screener/train/` | LoRA fine-tuning and the experiment runner |
| Evaluation | `screener/eval/` | Output verifier, metrics, explanations and the sealed evaluator |
| Decoders | `screener/inference/` | Uncached, key/value cached and speculative greedy decoding |
| Attention | `screener/attention/` | Reference and tiled online-softmax attention |
| Benchmarks | `benchmarks/` | Cache, attention and speculative measurements |
| Application | `app/` | FastAPI server, pipeline, number check, reports and React interface |

## Data handling

The dataset's own `training` column is ignored in favor of a fixed patient-grouped split: 37 patients for training, 8 for validation and 8 for testing, recorded in `splits/manifest.json`. The loader requests an explicit allowlist of columns, which keeps the GPT-4 predictions out of prompts and targets by construction. One row with a blank criterion (annotation 883) was removed before any results existed.

Labels are heavily skewed. Training has 8 "excluded" and 13 "not included" rows out of 602, and because the split is fixed this can't be changed by resampling patients. Oversampling rare labels in training was tested as one of the experiments. Experts also often reached "not excluded" because a condition was never mentioned, so 74.7% of those training rows have no cited evidence. The model is scored against the expert labels, and the application flags any verdict with no citation for human review.

Sentence IDs from the dataset are preserved. Unseen notes are split with NLTK, heading lines and list marks are removed, and the user can correct the result before screening. No prompt was truncated: the longest is 634 tokens against a context window of 32,768.

## Model selection

| | Qwen2.5-1.5B (target) | Qwen2.5-0.5B (draft) | SmolLM2-1.7B |
|---|---|---|---|
| Parameters | 1,543.7M | 494.0M | 1,711.4M |
| Layers, width | 28, 1,536 | 24, 896 | 24, 2,048 |
| Context window | 32,768 | 32,768 | 8,192 |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Macro-F1 after tuning (validation) | 0.558 | 0.446 | 0.514 |

The target had to be the largest open model that runs live on a 4 GB GPU and has a tokenizer-identical smaller partner. Qwen2.5-1.5B peaks at 2.89 GB during generation, and its vocabulary, special tokens, chat template and encodings were verified as identical to the 0.5B draft's. Qwen3 was rejected because its thinking mode complicates strict JSON output and its 4B model needs about 8 GB in half precision.

## Fine-tuning

LoRA was chosen over full fine-tuning because 602 rows wouldn't support training 1.54 billion parameters. Adapters attach to the query, key, value and output projections, and the loss covers answer tokens only. Training used AdamW at a learning rate of 2e-4 with batches of 4 and 2 accumulation steps, under half-precision autocast with seed 42. Early stopping used generated validation macro-F1, because loss and macro-F1 didn't move together.

| Run | Model | Rank | Oversampling | Output order | Accuracy | Macro-F1 | Evidence F1 |
|---|---|---|---|---|---|---|---|
| R0 | Qwen 1.5B, untrained | | | label first | 0.175 | 0.147 | 0.106 |
| R0b | SmolLM2, untrained | | | label first | 0.180 | 0.120 | 0.111 |
| R1 | Qwen 1.5B | 16 | none | label first | 0.752 | 0.534 | 0.462 |
| R2 | Qwen 1.5B | 16 | 0.5 | label first | 0.738 | 0.552 | 0.486 |
| **R3** | **Qwen 1.5B** | **32** | **0.5** | **label first** | **0.743** | **0.558** | **0.509** |
| R4 | Qwen 1.5B | 32 | 0.5 | evidence first | 0.762 | 0.459 | 0.526 |
| R5 | SmolLM2 | 32 | 0.5 | label first | 0.675 | 0.514 | 0.446 |
| R6 | Qwen 0.5B (draft) | 32 | 0.5 | label first | 0.738 | 0.446 | 0.491 |

R3 was selected by a rule fixed in advance. Its 95% patient-level interval on validation is 0.42 to 0.64, so the differences between R1, R2 and R3 may be noise. Listing evidence before the label (R4) raised evidence F1 slightly and cost macro-F1, so the label comes first.

## Evaluation

All evaluation uses deterministic greedy decoding, written out explicitly because Qwen's bundled defaults enable sampling and a repetition penalty. The sealed evaluator refuses the test split without a flag and logs each access.

| Test split (8 patients, 206 rows) | Accuracy | Macro-F1 | Evidence micro-F1 |
|---|---|---|---|
| Fine-tuned | 0.728 | 0.560 | 0.523 |
| Untrained | 0.204 | 0.234 | 0.130 |
| Majority baseline | 0.626 | 0.272 | 0.000 |

A label absent from a split's gold data is excluded from macro-F1 and reported as n/a. Over all rows, an evidence row where both sets are empty scores 1 and one where only one is empty scores 0. Uncertainty comes from a patient-level bootstrap with 2,000 resamples. Twelve analyzed errors are in [`results/error_analysis.md`](../results/error_analysis.md).

## Inference

**Key/value cached decoding** calls the model's forward pass directly with an explicit cache. It keeps the attention mask covering every cached token, passes each token's true position to the rotary embedding, and asserts that the cache grows by exactly one token per step. Tokens matched the uncached reference in all 9 tested combinations, with speedups up to 8.97x at 1,024 input and 256 output tokens.

**Tiled online-softmax attention** splits queries and keys into tiles, keeps a running maximum, normalizer and partial output for each query row, and skips fully masked tiles. Maximum error against the reference stayed near 1e-6. At length 4096 it used 18.5 MB of GPU memory above the inputs against 1,536 MB for the reference. Runtime is slower than the reference on the GPU, because each tile pays Python and submission overheads that a compiled kernel avoids.

**Greedy speculative decoding** drafts with the 0.5B model and verifies with the 1.5B target in one pass. Both caches always hold every token except the last, and this is checked each round. Tokens matched greedy decoding everywhere, at 0.51x to 0.85x of greedy speed on a T4. A 0.5B step cost about 24 ms against 39 ms for the target, since interpreter time and mask building don't shrink with the model, so drafting never becomes cheap enough to pay for itself at this size.

## Application

The app follows a guided flow from patient note to sentence review, criteria, results and a downloadable report, with an Inspect area for live comparisons. Work is kept in session storage across refreshes, and a refresh during a run reconnects to it.

**Overall result.** A patient is likely ineligible only if a criterion failed with cited evidence, needs review if anything is unknown, unverified or uncited, and potentially eligible otherwise. Uncited verdicts count as unconfirmed.

**Explanations.** These are fixed wording that quotes cited sentences. A model-written version was tested and rejected after it invented patient facts.

**Number check.** The model is unreliable at numeric comparisons, so plain code decides bare comparisons when the note holds one clear value, and it stays silent otherwise. It was developed on training notes and judged once on validation against a bar set in advance, where it made 5 decisions and all 5 were correct. All 5 were age criteria the model already had right, so its benefit on BMI and laboratory values hasn't been measured on the dataset. It's excluded from every reported metric and was never run on the test split.

**Startup.** `setup_app.bat` installs CPU or GPU PyTorch as appropriate and downloads only what the app needs at pinned revisions, and `start_app.bat` opens the browser once the model has loaded. Without a GPU the app uses full precision when at least 8 GB of memory is free, since half precision measured about three times slower on the CPU with identical labels.

## Alternatives considered

| Decision | Alternative | Reason |
|---|---|---|
| Merge adapter at load | Keep the adapter separate | Simpler and faster inference |
| Local browser app | Serverless hosting | No GPU, and a 3 GB model can't stay loaded |
| CSV and JSON logs | An experiment tracking service | Pinned configurations and logs were enough |
| Half-precision base with LoRA | 4-bit quantized base | The 1.5B model already fits on the training GPU |
| Keep the frozen model after testing | Retrain or switch to a larger model | Would mean tuning against test data, and a larger model doesn't fit the 4 GB target |
| Correct numbers in code | A hand-written drug dictionary | Numbers can be checked exactly, while a dictionary would be partial and look more reliable than it is |

## Engineering problems and fixes

- **Training memory.** A two-example run hit 8.38 GB because of the autograd graph. Gradient checkpointing cut it to 5.2 GB and from 264 to 74 seconds by ending paging.
- **Dependency conflict on Kaggle.** A preinstalled torchao was too old for PEFT, so torchao is now pinned.
- **Dataset delivered through Git LFS.** A plain clone would have received a pointer file, so the parquet is stored directly.
- **Evaluation session timeout.** A Kaggle session ended during the last benchmark and lost its files, so the notebook was rerun from the same frozen commit. Test metrics matched to four decimal places, and both runs are in the access log.
- **Startup on a 4 GB GPU.** The model needs nearly all of the 3.2 GB that's actually free. Merging on the CPU gives bit-identical weights at a slightly lower peak, moving to the GPU is retried, and a full card gets a plain message.
- **Browser opening too early.** The launcher now opens the browser after the model loads.

## Verification

The automated suite covers the split, data preparation, the verifier, metrics, explanations, all three decoders, attention, the number check and the application API. Browser click-throughs covered navigation, refresh recovery, sentence tools and report download. A fresh clone from GitHub was set up with CPU-only PyTorch and ran a real screening.

## Limitations and future work

The test split has 8 patients, so intervals are wide, and "excluded" has no test examples. The model is small and weak on numeric comparison and medical knowledge, and a cited verdict can still be wrong. The most useful next steps are more data for rare labels, a consistent annotation rule for "not applicable", having the model show its working before answering, and a larger model on hardware that can serve it.
