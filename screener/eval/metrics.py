"""Scoring used for model selection. Labels with no gold examples in a split are left out of macro-F1."""
from sklearn.metrics import accuracy_score, f1_score


def evidence_micro(gold_sets, predicted_sets):
    """Micro precision, recall and F1 over all sentence IDs."""
    true_positive = false_positive = false_negative = 0
    for gold, predicted in zip(gold_sets, predicted_sets):
        gold, predicted = set(gold), set(predicted)
        true_positive += len(gold & predicted)
        false_positive += len(predicted - gold)
        false_negative += len(gold - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def score_predictions(examples, verified):
    """Summarize generated answers against expert labels and evidence."""
    gold_labels = [example.label for example in examples]
    predicted_labels = [result.label for result in verified]
    present = sorted(set(gold_labels))
    evidence = evidence_micro([e.evidence for e in examples], [v.evidence for v in verified])
    return {
        "accuracy": float(accuracy_score(gold_labels, predicted_labels)),
        "macro_f1": float(f1_score(gold_labels, predicted_labels, labels=present, average="macro", zero_division=0)),
        "invalid_rate": sum(not v.valid for v in verified) / len(verified),
        "evidence_precision": evidence["precision"],
        "evidence_recall": evidence["recall"],
        "evidence_f1": evidence["f1"],
        "labels_scored": present,
    }


def selection_key(metrics):
    """Model selection: validation macro-F1, then evidence F1 as the tie-break."""
    return (round(metrics["macro_f1"], 6), round(metrics["evidence_f1"], 6))
