"""Build the paper's figures and results tables directly from the files in results/.

Run from anywhere: python report/make_assets.py
Figures go to report/figures and LaTeX tables to report/tables, so no number is typed by hand.
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "report" / "figures"
TABLES = ROOT / "report" / "tables"

BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, SECONDARY, MUTED, GRID, BASELINE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
WASH = "#f4f3ef"
SEQUENTIAL = LinearSegmentedColormap.from_list("seq", ["#ffffff", "#cde2fb", "#86b6ef", "#2a78d6", "#184f95", "#0d366b"])
ONE_COLUMN = 3.5
TWO_COLUMN = 7.16

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": SECONDARY,
    "axes.titlesize": 8,
    "axes.titlecolor": INK,
    "axes.titleweight": "bold",
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "xtick.color": SECONDARY,
    "ytick.color": SECONDARY,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "legend.frameon": False,
    "legend.fontsize": 7,
    "lines.linewidth": 1.6,
    "lines.markersize": 4.5,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})


def load(path):
    return json.loads((RESULTS / path).read_text(encoding="utf-8"))


def metrics(name):
    return load(f"eval/{name}/metrics.json")


def save(figure, name):
    figure.savefig(FIGURES / f"{name}.pdf")
    plt.close(figure)


def write_table(name, body):
    (TABLES / f"{name}.tex").write_text(body.strip() + "\n\\bottomrule\n", encoding="utf-8")


def n(value, digits=3):
    return "--" if value is None else f"{value:.{digits}f}"


# Diagrams ------------------------------------------------------------------


def box(axis, x, y, width, height, text, fill=WASH, edge=BASELINE, color=INK, size=6.8, weight="normal"):
    axis.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0,rounding_size=0.09", facecolor=fill, edgecolor=edge, linewidth=0.8))
    axis.text(x + width / 2, y + height / 2, text, ha="center", va="center", color=color, fontsize=size, fontweight=weight, linespacing=1.2)


def arrow(axis, start, end, color=SECONDARY, style="-"):
    axis.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=7, linewidth=0.9, color=color, linestyle=style, shrinkA=0, shrinkB=0))


def canvas(width, height, x_limit, y_limit):
    figure, axis = plt.subplots(figsize=(width, height))
    axis.set_xlim(0, x_limit)
    axis.set_ylim(0, y_limit)
    axis.axis("off")
    figure.subplots_adjust(0, 0, 1, 1)
    return figure, axis


def figure_model():
    figure, axis = canvas(ONE_COLUMN, 3.05, 10, 9.2)
    box(axis, 2.1, 8.3, 5.8, 0.72, "Token IDs from the Qwen2 tokenizer")
    box(axis, 2.1, 7.2, 5.8, 0.72, "Token embedding, 1,536 dimensions")
    axis.add_patch(FancyBboxPatch((0.3, 2.0), 9.4, 4.85, boxstyle="round,pad=0,rounding_size=0.12", facecolor="#ffffff", edgecolor=BLUE, linewidth=1.1))
    axis.text(0.55, 6.5, "Decoder layer, repeated 28 times", color=INK, fontsize=7, fontweight="bold", va="center")
    box(axis, 0.7, 5.2, 8.6, 0.9, "Masked attention: 12 query heads, 2 key/value heads,\nrotary positions, causal mask", fill="#cde2fb", edge=BLUE)
    box(axis, 0.7, 4.0, 4.1, 0.85, "LoRA on q, k, v, o\nrank 32, alpha 64", fill="#ffffff", edge=ORANGE)
    box(axis, 5.2, 4.0, 4.1, 0.85, "KV cache per layer\ngrows token by token", fill="#ffffff", edge=AQUA)
    box(axis, 0.7, 2.4, 8.6, 1.15, "Attention kernel, chosen at run time:\nreference, PyTorch fused, or tiled online softmax\nfollowed by feed-forward layer and normalization")
    box(axis, 2.1, 0.95, 5.8, 0.72, "Final normalization and linear head")
    box(axis, 2.1, 0.0, 5.8, 0.65, "Next-token logits (greedy argmax)")
    for start, end in (((5, 8.3), (5, 7.92)), ((5, 7.2), (5, 6.85)), ((5, 2.0), (5, 1.67)), ((5, 0.95), (5, 0.65))):
        arrow(axis, start, end)
    save(figure, "model")


def figure_pipeline():
    figure, axis = canvas(TWO_COLUMN, 2.75, 20, 7.6)
    axis.text(0.1, 7.3, "Training and evaluation (Kaggle T4)", color=INK, fontsize=7.5, fontweight="bold", va="center")
    row = 5.75
    steps = [
        ("TrialGPT criterion\nannotations\n1,015 rows", 0.1),
        ("Patient split\n37 / 8 / 8, seed 42\nmanifest saved", 3.45),
        ("Prompt and JSON target\nnumbered note, type,\ncriterion, no GPT-4 text", 6.8),
        ("LoRA fine-tuning\nloss on answer tokens,\nearly stop on macro-F1", 10.65),
        ("Adapter published,\nmerged at load time,\nrevision pinned", 14.5),
    ]
    for text, x in steps:
        box(axis, x, row, 3.0 if x < 6 else 3.5, 1.25, text)
    for start, end in ((3.1, 3.45), (6.45, 6.8), (10.3, 10.65), (14.15, 14.5)):
        arrow(axis, (start, row + 0.62), (end, row + 0.62))
    box(axis, 18.15, row, 1.8, 1.25, "Sealed\ntest run", fill="#fde3d8", edge=ORANGE)
    arrow(axis, (18.0, row + 0.62), (18.15, row + 0.62))
    axis.text(0.1, 4.95, "Live application (local browser app)", color=INK, fontsize=7.5, fontweight="bold", va="center")
    row = 3.3
    steps = [
        ("Patient note\nand criteria\nvalidated", 0.1, 2.4),
        ("Numbered\nsentences\nreviewed by user", 2.85, 2.6),
        ("Decoder\nuncached, KV cached\nor speculative", 5.8, 3.0),
        ("Verifier\nJSON, label set,\nsentence IDs", 9.15, 2.7),
        ("Number check\nsimple numeric\ncomparisons only", 12.2, 2.8),
        ("Explanation\nquotes cited\nsentences only", 15.35, 2.6),
    ]
    for text, x, width in steps:
        box(axis, x, row, width, 1.25, text, fill="#cde2fb" if "Decoder" in text else WASH, edge=BLUE if "Decoder" in text else BASELINE)
    for start, end in ((2.5, 2.85), (5.45, 5.8), (8.8, 9.15), (11.85, 12.2), (15.0, 15.35)):
        arrow(axis, (start, row + 0.62), (end, row + 0.62))
    box(axis, 18.3, row, 1.65, 1.25, "Overall\nrule", fill="#d2f1e4", edge=AQUA)
    arrow(axis, (17.95, row + 0.62), (18.3, row + 0.62))
    axis.text(0.1, 2.5, "Application workflow", color=INK, fontsize=7.5, fontweight="bold", va="center")
    row, height = 0.75, 1.15
    screens = [("Landing", 0.1, 1.75), ("Step 1\nPatient note", 2.2, 2.1), ("Step 2\nSentence review", 4.65, 2.5), ("Step 3\nTrial criteria", 7.5, 2.1), ("Running\nCancel allowed", 9.95, 2.3), ("Results\noverall and rows", 12.6, 2.5), ("Criterion detail\nlit evidence", 15.45, 2.4)]
    for text, x, width in screens:
        box(axis, x, row, width, height, text)
    for start, end in ((1.85, 2.2), (4.3, 4.65), (7.15, 7.5), (9.6, 9.95), (12.25, 12.6), (15.1, 15.45)):
        arrow(axis, (start, row + height / 2), (end, row + height / 2))
    box(axis, 18.2, row, 1.75, height, "Report\nHTML, JSON", fill="#d2f1e4", edge=AQUA)
    arrow(axis, (17.85, row + height / 2), (18.2, row + height / 2))
    box(axis, 7.5, 0.0, 10.35, 0.5, "Inspect: live decoding and attention comparisons, saved reports, model details", size=6.5, fill="#ffffff", edge=BLUE)
    arrow(axis, (13.85, 0.75), (13.85, 0.5))
    save(figure, "pipeline")


# Charts --------------------------------------------------------------------


def figure_training():
    rows = list(csv.DictReader((RESULTS / "training/R3/history.csv").open(encoding="utf-8")))
    epochs = [int(r["epoch"]) for r in rows]
    figure, (left, right) = plt.subplots(1, 2, figsize=(ONE_COLUMN, 1.75))
    left.plot(epochs, [float(r["train_loss"]) for r in rows], color=BLUE, marker="o", label="Training")
    left.plot(epochs, [float(r["val_loss"]) for r in rows], color=ORANGE, marker="s", label="Validation")
    left.set_title("Loss")
    left.set_xlabel("Epoch")
    left.set_ylim(-0.08, 0.24)
    left.set_yticks([0, 0.05, 0.10, 0.15, 0.20])
    left.legend(loc="lower left", bbox_to_anchor=(-0.02, -0.02), handlelength=1.4, labelspacing=0.2)
    right.plot(epochs, [float(r["macro_f1"]) for r in rows], color=BLUE, marker="o")
    best = max(rows, key=lambda r: float(r["macro_f1"]))
    x, y = int(best["epoch"]), float(best["macro_f1"])
    right.plot([x], [y], marker="o", markersize=8, markerfacecolor="none", markeredgecolor=ORANGE, markeredgewidth=1.4, linestyle="none")
    right.annotate(f"kept: epoch {x}\n{y:.3f}", (x, y), xytext=(12, -32), textcoords="offset points", ha="center", color=INK, fontsize=6.8)
    right.set_title("Validation macro-F1")
    right.set_xlabel("Epoch")
    right.set_ylim(0.3, 0.65)
    for axis in (left, right):
        axis.set_xticks(epochs)
    figure.tight_layout(pad=0.3, w_pad=1.0)
    save(figure, "training")


LABEL_SHORT = {"included": "Included", "not included": "Not incl.", "excluded": "Excluded", "not excluded": "Not excl.", "not enough information": "Not enough", "not applicable": "Not appl."}


def confusion(axis, block, title, order):
    matrix = block["confusion_matrix"]["matrix"]
    data = [[matrix[g].get(p, 0) for p in order] for g in order]
    largest = max(max(row) for row in data)
    axis.imshow(data, cmap=SEQUENTIAL, vmin=0, vmax=largest, aspect="equal")
    axis.grid(False)
    axis.spines[:].set_visible(False)
    axis.set_xticks(range(len(order)), [LABEL_SHORT[x] for x in order], rotation=35, ha="right", fontsize=6.6)
    axis.set_yticks(range(len(order)), [LABEL_SHORT[x] for x in order], fontsize=6.6)
    axis.set_title(title)
    axis.set_xlabel("Predicted")
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            axis.text(j, i, value, ha="center", va="center", fontsize=7, color="#ffffff" if value > 0.5 * largest else INK)


def figure_confusion():
    c = metrics("after_test")["metrics"]["classification"]
    figure, axes = plt.subplots(1, 3, figsize=(TWO_COLUMN, 2.5), gridspec_kw={"width_ratios": [5, 4, 3]})
    confusion(axes[0], c["overall"], "All criteria (206)", ["included", "not included", "not excluded", "not enough information", "not applicable"])
    confusion(axes[1], c["inclusion"], "Inclusion (75)", ["included", "not included", "not enough information", "not applicable"])
    confusion(axes[2], c["exclusion"], "Exclusion (131)", ["not excluded", "not enough information", "not applicable"])
    axes[0].set_ylabel("Expert label")
    figure.tight_layout(pad=0.3, w_pad=1.2)
    save(figure, "confusion")


def figure_before_after():
    runs = [("before_test", "Untrained", MUTED), ("baseline_test", "Majority baseline", ORANGE), ("after_test", "Fine-tuned", BLUE)]
    groups = ["Accuracy", "Macro-F1", "Evidence\nmicro-F1"]
    figure, axis = plt.subplots(figsize=(ONE_COLUMN, 2.0))
    for index, (name, label, color) in enumerate(runs):
        m = metrics(name)["metrics"]
        values = [m["classification"]["overall"]["accuracy"], m["classification"]["overall"]["macro_f1"], m["evidence"]["overall"]["micro"]["f1"]]
        positions = [x + (index - 1) * 0.27 for x in range(3)]
        bars = axis.bar(positions, values, width=0.24, color=color, label=label)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, value + 0.012, f"{value:.2f}", ha="center", va="bottom", fontsize=6.3, color=INK)
    axis.set_xticks(range(3), groups)
    axis.set_ylim(0, 0.92)
    axis.set_ylabel("Score on the test split")
    axis.xaxis.grid(False)
    axis.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.17), columnspacing=1.0, handlelength=1.1, handletextpad=0.4)
    save(figure, "before_after")


def figure_cache():
    results = load("bench_cache_kaggle-t4-finetuned.json")["results"]
    figure, axis = plt.subplots(figsize=(ONE_COLUMN, 1.95))
    for input_length, color, marker in ((1024, BLUE, "o"), (256, ORANGE, "s"), (64, AQUA, "^")):
        rows = [r for r in results if r["input_tokens"] == input_length]
        x = [r["output_tokens"] for r in rows]
        y = [r["modes"]["uncached"]["total_s"]["median"] / r["modes"]["cached"]["total_s"]["median"] for r in rows]
        axis.plot(x, y, color=color, marker=marker, label=f"{input_length} input tokens")
        axis.annotate(f"{y[-1]:.2f}x", (x[-1], y[-1]), xytext=(5, 0), textcoords="offset points", va="center", fontsize=6.8, color=INK)
    axis.axhline(1, color=SECONDARY, linewidth=0.8, linestyle="--")
    axis.set_xscale("log", base=2)
    axis.set_xticks([16, 64, 256], ["16", "64", "256"])
    axis.minorticks_off()
    axis.set_xlim(13, 340)
    axis.set_ylim(0, 10.5)
    axis.set_xlabel("Output tokens")
    axis.set_ylabel("Speedup over uncached")
    axis.legend(loc="upper left")
    save(figure, "cache")


def figure_attention():
    results = [r for r in load("bench_attention_kaggle-t4.json")["results"] if r["device"] == "cuda"]
    series = (("tiled_16", "Tiled, 16", ORANGE, "s"), ("tiled_64", "Tiled, 64", YELLOW, "D"), ("tiled_256", "Tiled, 256", AQUA, "^"), ("reference", "Reference", BLUE, "o"), ("pytorch_fused", "PyTorch fused", MAGENTA, "v"))
    figure, axis = plt.subplots(figsize=(ONE_COLUMN, 2.15))
    lengths = [r["length"] for r in results]
    for key, label, color, marker in series:
        y = [r["modes"][key]["median_s"] * 1000 for r in results]
        axis.plot(lengths, y, color=color, marker=marker, label=label)
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xticks(lengths, [str(x) for x in lengths])
    axis.minorticks_off()
    axis.set_xlabel("Sequence length (tokens)")
    axis.set_ylabel("Median runtime (ms, log scale)")
    axis.legend(loc="upper left", ncol=2, columnspacing=1.0, handlelength=1.6)
    save(figure, "attention")


def figure_speculative():
    drafts = (("finetuned-draft", "Fine-tuned 0.5B draft"), ("base-draft", "Base 0.5B draft"))
    scenes = (("screening_json", "Screening JSON", BLUE, "o"), ("long_256in_128out", "256 in, 128 out", ORANGE, "s"), ("long_1024in_128out", "1024 in, 128 out", AQUA, "^"))
    figure, axes = plt.subplots(1, 2, figsize=(ONE_COLUMN, 1.95), sharey=True)
    for axis, (key, title) in zip(axes, drafts):
        results = {r["scenario"]: r for r in load(f"bench_speculative_kaggle-t4-{key}.json")["results"]}
        for scene, label, color, marker in scenes:
            axis.plot([2, 4, 8], [results[scene]["modes"][f"speculative_k{k}"]["speedup_vs_greedy"] for k in (2, 4, 8)], color=color, marker=marker, label=label)
        axis.axhline(1, color=SECONDARY, linewidth=0.8, linestyle="--")
        axis.set_xscale("log", base=2)
        axis.set_xticks([2, 4, 8], ["2", "4", "8"])
        axis.minorticks_off()
        axis.set_title(title)
        axis.set_xlabel("Draft length k")
        axis.set_ylim(0, 1.15)
    axes[0].set_ylabel("Speed relative to greedy")
    axes[0].text(2.05, 1.03, "greedy = 1.0", fontsize=6.5, color=SECONDARY)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.13), columnspacing=1.0, handlelength=1.5)
    figure.tight_layout(pad=0.3, w_pad=0.8)
    save(figure, "speculative")


# Tables --------------------------------------------------------------------


def table_split():
    manifest = json.loads((ROOT / "splits/manifest.json").read_text(encoding="utf-8"))["splits"]
    order = ("train", "validation", "test")
    keys = [("inclusion/included", "Included"), ("inclusion/not included", "Not included"), ("inclusion/not enough information", "Inclusion, not enough info."), ("inclusion/not applicable", "Inclusion, not applicable"), ("exclusion/excluded", "Excluded"), ("exclusion/not excluded", "Not excluded"), ("exclusion/not enough information", "Exclusion, not enough info."), ("exclusion/not applicable", "Exclusion, not applicable")]
    lines = ["Patients & " + " & ".join(str(manifest[s]["num_patients"]) for s in order) + r" \\", "Usable rows & " + " & ".join(str(manifest[s]["num_usable_rows"]) for s in order) + r" \\", r"\midrule"]
    for key, name in keys:
        lines.append(f"{name} & " + " & ".join(str(manifest[s]["label_counts"].get(key, 0)) for s in order) + r" \\")
    write_table("split", "\n".join(lines))


def table_runs():
    rows = list(csv.DictReader((RESULTS / "training/summary.csv").open(encoding="utf-8")))
    names = {"models/qwen2.5-1.5b": "Qwen 1.5B", "models/smollm2-1.7b": "SmolLM2 1.7B", "models/qwen2.5-0.5b": "Qwen 0.5B"}
    lines = []
    for r in rows:
        trained = r["trained"] == "True"
        lora = r["lora_rank"] if trained else "--"
        over = r["oversample_power"] if trained else "--"
        order = {"label_first": "L", "evidence_first": "E"}[r["order"]] if trained else "--"
        epoch = r["best_epoch"] if trained else "--"
        bold = r["run"] == "R3"
        cells = [r["run"], names[r["model"]], lora, over, order, epoch, n(float(r["accuracy"])), n(float(r["macro_f1"])), n(float(r["evidence_f1"]))]
        lines.append(" & ".join(rf"\textbf{{{c}}}" if bold else c for c in cells) + r" \\")
    write_table("runs", "\n".join(lines))


def table_eval():
    lines = []
    for split, title in (("test", "Test"), ("validation", "Validation")):
        for group, label in (("overall", "Overall"), ("inclusion", "Inclusion"), ("exclusion", "Exclusion")):
            cells = [title if group == "overall" else "", label]
            for run in ("before", "baseline", "after"):
                block = metrics(f"{run}_{split}")["metrics"]["classification"][group]
                cells += [n(block["accuracy"]), n(block["macro_f1"])]
            lines.append(" & ".join(cells) + r" \\")
        if split == "test":
            lines.append(r"\midrule")
    write_table("eval", "\n".join(lines))


def table_per_class():
    c = metrics("after_test")["metrics"]["classification"]
    order = {
        "overall": ("included", "not included", "not excluded", "excluded", "not enough information", "not applicable"),
        "inclusion": ("included", "not included", "not enough information", "not applicable"),
        "exclusion": ("not excluded", "excluded", "not enough information", "not applicable"),
    }
    lines = []
    for group, labels in order.items():
        for index, label in enumerate(labels):
            x = c[group]["per_class"][label]
            name = label[0].upper() + label[1:]
            title = group.title() if index == 0 else ""
            lines.append(f"{title} & {name} & {x['support']} & {n(x['precision'])} & {n(x['recall'])} & {n(x['f1'])} " + r"\\")
        if group != "exclusion":
            lines.append(r"\midrule")
    write_table("per_class", "\n".join(lines))


def table_evidence():
    lines = []
    for run, name in (("before", "Untrained"), ("after", "Fine-tuned")):
        e = metrics(f"{run}_test")["metrics"]["evidence"]
        for group in ("overall", "inclusion", "exclusion"):
            x = e[group]
            micro, every, gold = x["micro"], x["macro_all_rows"], x["macro_rows_with_gold_evidence"]
            cells = [name if group == "overall" else "", group.title(), n(micro["precision"]), n(micro["recall"]), n(micro["f1"]), n(every["f1"]), n(gold["f1"])]
            lines.append(" & ".join(cells) + r" \\")
        if run == "before":
            lines.append(r"\midrule")
    write_table("evidence", "\n".join(lines))


def table_cache():
    lines = []
    for r in load("bench_cache_kaggle-t4-finetuned.json")["results"]:
        u, c = r["modes"]["uncached"], r["modes"]["cached"]
        speedup = u["total_s"]["median"] / c["total_s"]["median"]
        cells = [
            r["input_tokens"], r["output_tokens"],
            n(c["prefill_s"]["median"]), n(u["decode_s"]["median"], 2), n(c["decode_s"]["median"], 2),
            n(u["total_tokens_per_s"]["median"], 1), n(c["total_tokens_per_s"]["median"], 1),
            n(u["peak_above_model_gb"]["median"] * 1024, 0), n(c["peak_above_model_gb"]["median"] * 1024, 0),
            rf"{speedup:.2f}$\times$",
        ]
        lines.append(" & ".join(str(c) for c in cells) + r" \\")
    write_table("cache", "\n".join(lines))


def table_attention():
    lines = []
    for r in (x for x in load("bench_attention_kaggle-t4.json")["results"] if x["device"] == "cuda" and x["length"] in (256, 1024, 4096)):
        m = r["modes"]
        worst = max(m[k]["max_abs_error"] for k in ("tiled_16", "tiled_64", "tiled_256"))
        mean = max(m[k]["mean_abs_error"] for k in ("tiled_16", "tiled_64", "tiled_256"))
        cells = [str(r["length"])]
        cells += [n(m[k]["median_s"] * 1000, 1) for k in ("reference", "pytorch_fused", "tiled_64", "tiled_256")]
        cells += [n(m[k]["peak_extra_gpu_mb"], 1) for k in ("reference", "tiled_256")]
        cells += [f"{worst:.1e}".replace("e-0", "e-"), f"{mean:.1e}".replace("e-0", "e-")]
        lines.append(" & ".join(cells) + r" \\")
    write_table("attention", "\n".join(lines))


def table_speculative():
    data = load("bench_speculative_kaggle-t4-finetuned-draft.json")["results"]
    names = {"screening_json": "Screening JSON", "long_256in_128out": "256 in, 128 out", "long_1024in_128out": "1024 in, 128 out"}
    lines = []
    for r in data:
        g = r["modes"]["greedy"]
        for k in (2, 4, 8):
            s = r["modes"][f"speculative_k{k}"]
            first = names[r["scenario"]] if k == 2 else ""
            base = f"{g['total_s']:.2f}" if k == 2 else ""
            cells = [first, base, str(k), n(s["total_s"], 2), n(s["acceptance_rate"]), n(s["tokens_per_round"], 2), n(s["tokens_per_s"], 1), n(s["peak_above_models_gb"] * 1024, 0), rf"{s['speedup_vs_greedy']:.2f}$\times$"]
            lines.append(" & ".join(cells) + r" \\")
        if r is not data[-1]:
            lines.append(r"\midrule")
    write_table("speculative", "\n".join(lines))


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    for build in (figure_model, figure_pipeline, figure_training, figure_confusion, figure_before_after, figure_cache, figure_attention, figure_speculative, table_split, table_runs, table_eval, table_per_class, table_evidence, table_cache, table_attention, table_speculative):
        build()
    print(f"wrote {len(list(FIGURES.glob('*.pdf')))} figures and {len(list(TABLES.glob('*.tex')))} tables")


if __name__ == "__main__":
    main()
