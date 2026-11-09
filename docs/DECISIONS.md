# Design decisions and failures

A running record of options considered, what was rejected, and what went wrong.

## Data

**The dataset's `training` column is ignored.** The assignment prescribes a split by patient with seed 42.

**Only allowlisted columns are read.** Blocking GPT-4 columns by name can miss a column, so the loader requests just the eight columns it needs. `gpt4_*` and `explanation_correctness` are never loaded for prompts or targets.

**One row with a blank criterion is removed (annotation 883).** It has nothing to judge. This was decided before any results existed, and the row stays in the manifest's total counts.

**Absent evidence and expert labels are in tension.** In the training split, 74.7% of "not excluded" rows have no cited evidence, along with 82.1% of "not applicable" rows and 5.7% of "included" rows. Experts often reached "not excluded" because a condition was never mentioned. The assignment says absent evidence must not be treated as proof, so the model is scored against expert labels as required, and the app flags any verdict with no cited evidence for human review instead of presenting it as established.

**Rare labels.** Training has 8 "excluded" and 13 "not included" rows out of 602. The split is mandatory, so this cannot be fixed by resampling patients. Run R2 tests oversampling these labels in training only.

## Models

**Qwen3 rejected.** Its thinking mode is on by default and adds reasoning text that complicates structured output, and the 4B model needs about 8 GB at float16, which exceeds the laptop's 4 GB GPU.

**Qwen2.5-1.5B and 0.5B chosen as target and draft.** Verified identical vocabulary, special tokens, chat template and encodings, as Task 5 requires.

**Explanations are not trained.** The dataset's only written explanations come from GPT-4, and the assignment bars them from input and evaluation. Using them as training targets would teach the model GPT-4's outputs, so explanations are built only from the cited sentences.

## Training

**LoRA was chosen over full fine-tuning.** With only 602 training rows, training all 1.54B parameters would invite overfitting and would need far more memory. LoRA on the attention projections trains 4.36M parameters at rank 16, about 0.28% of the model.

**Decoding settings are written out explicitly.** Qwen's bundled generation settings enable sampling and a repetition penalty. Left in place, they would make before/after comparisons unclear and break token equality with the custom decoders, so greedy decoding with a repetition penalty of 1.0 is stated in the code.

**Gradient checkpointing added after a memory surprise.** A two-example laptop run reported a peak of 8.38 GB on a 4 GB GPU, against 2.98 GB for prediction. The model had stayed at float16; the extra memory was the autograd graph, which keeps activations for every layer and grows with token count, and Windows paged the overflow into system RAM. A batch of 8 long examples could exceed the 16 GB on Kaggle's T4, so checkpointing was enabled, which cut the same run's peak to 5.2 GB and its time from 264 to 74 seconds because it no longer paged. Batches were also set to 4 with 2 accumulation steps, keeping 8 examples per update with less peak memory.

**Model-written explanations were tested and rejected.** The base model, with the adapter disabled, was asked to explain verdicts from only the cited sentences. On real validation rows it invented facts: it called a female patient male, and said age 58 falls outside a 25-65 range. A check that rejected numbers absent from the sources did not catch either error, since both used numbers or words already present. The assignment requires explanations based only on available information, so explanations now state the verdict in fixed wording and quote the cited sentences exactly. This is less fluent, but it cannot introduce a fact.

## Environment failures

**System PyTorch was CPU-only.** Found during the resource check. A project virtual environment now installs the CUDA 12.8 build.

**First dependency install failed.** `datasets` 5.1.0 needs `huggingface_hub` 1.31 or newer, and the initial pin was 1.14.0. Corrected to 1.33.0.

**First Kaggle training run failed on a preinstalled package.** Kaggle ships torchao 0.10.0, and peft 0.21.2 raises an error when it finds a torchao older than 0.16 while attaching LoRA layers. The baselines finished because they attach no adapter. torchao is now pinned to 0.18.0, and this was tested on the laptop with a real LoRA epoch.

**Dataset arrived under Git LFS.** The upstream `.gitattributes` routed the parquet file through LFS, so a plain clone without git-lfs would receive a pointer file. The rule was removed and the file is stored directly.
