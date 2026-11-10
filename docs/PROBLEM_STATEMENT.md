# Problem statement

## Background

Clinical trials depend on enrolling patients who meet detailed inclusion and exclusion criteria. Checking those criteria means reading a patient's record and comparing it against each requirement, which is slow, repetitive and easy to get wrong. Large language models can assist with this work, but systems that rely on hosted proprietary models can't be inspected, modified or run on local hardware.

## Problem

Build a system that takes a patient description and a clinical trial's eligibility criteria and, for each individual criterion, decides how the patient relates to it and identifies the sentences in the patient description that support that decision. The system has to run on an open-weight Transformer that can be executed locally, and its efficient inference paths have to be implemented and validated explicitly.

## Inputs and outputs

For each criterion the model receives the patient description, the criterion type (inclusion or exclusion) and the criterion text. It returns a structured result with one eligibility label and the IDs of the supporting patient sentences.

| Criterion type | Labels |
|---|---|
| Inclusion | included, not included, not enough information, not applicable |
| Exclusion | excluded, not excluded, not enough information, not applicable |

Insufficient-information and not-applicable outcomes must be preserved and not collapsed into a yes or no decision. Each prediction must also provide the criterion, the extracted evidence text and an explanation based only on the available information. The absence of evidence must never be treated as proof of eligibility or ineligibility.

## Data and evaluation protocol

The supervised benchmark is the [TrialGPT Criterion Annotations](https://huggingface.co/datasets/ncbi/TrialGPT-Criterion-Annotations) dataset, which holds patient descriptions, criteria, expert eligibility judgments and expert-identified evidence sentences. It also contains earlier model-generated predictions and explanations, and these must never be used as input features or leak into evaluation.

The data is split by patient. Unique patient IDs are sorted and shuffled with NumPy's `default_rng(42)`, the first 37 patients are used for training, the next 8 for validation and the remaining 8 for testing, and all annotations for a patient stay in one split. The split manifest is published. The test set stays untouched until final evaluation, and models, prompts and thresholds aren't tuned on it.

## Requirements

**Model adaptation.** Compare at least two suitable open-weight decoder models, justify the final choice by architecture, parameter count, licensing, memory and hardware fit, and fine-tune it on the training split. Compare the same model before and after fine-tuning, and document any truncation.

**Eligibility and evidence quality.** Report accuracy, macro-F1, per-class precision, recall and F1, and confusion matrices, overall and separately for inclusion and exclusion criteria. Report evidence precision, recall and F1 and state how records with no annotated evidence are treated. Analyze representative errors, contradictory cases and failures caused by missing information.

**Key/value cached generation.** Implement decoding that explicitly reuses and updates the Transformer's key/value cache, alongside a reference path with no cache reuse. Under deterministic greedy decoding, verify token-level agreement and compare prefill time, decoding time, tokens per second and peak memory across several input and output lengths.

**Efficient attention.** Implement a reference scaled dot-product attention and a variant based on tiling and online softmax. Verify agreement with causal masking at numerically stable tolerances, and compare speed and memory.

**Speculative decoding.** Pair the target with a smaller draft model with compatible tokenization and implement greedy speculative decoding, including drafting, target verification, accepting matching tokens, handling rejection and keeping cache state correct. Verify token equality with greedy decoding and report acceptance statistics, latency, tokens per second and memory.

**Application.** Provide a standalone browser application in which a user can supply a patient record, enter or select a trial's criteria, run the model, inspect each criterion's result and supporting evidence, and export a readable screening report. It must include a live comparison of the inference mechanisms and must be usable without running code by hand. Any overall patient-trial verdict is an aggregation based on explicit rules and isn't a ground-truth label.

## Constraints

Compulsory functionality can't depend on paid GPUs, paid APIs or proprietary model services. Large model weights are hosted separately with a working download method, and results must be reproducible from the published source.

## Out of scope

The system is a research screening prototype. It isn't a medical device and doesn't make clinical enrollment decisions.
