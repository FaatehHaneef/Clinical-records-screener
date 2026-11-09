"""Application logic with no model dependency: validation, result records, overall rule and reports."""
import hashlib
import html
import re
from datetime import datetime, timezone

from screener.data.sentences import split_unseen_note
from screener.eval.explain import NO_EVIDENCE, explain
from screener.eval.verifier import INVALID

NOTICE = "Educational screening prototype. Not a clinical enrollment decision."
MAX_NOTE_CHARACTERS = 20_000
MAX_SENTENCES = 200
MAX_CRITERIA = 40
MAX_CRITERION_CHARACTERS = 1_000
MODES = ("cached", "uncached", "speculative")
OVERALL_RULE = (
    "Likely ineligible if a criterion failed with cited evidence. Otherwise needs review if anything is "
    "unknown, unverified or has no cited evidence. Otherwise potentially eligible. This is a rule applied to "
    "criterion-level predictions, not a ground-truth patient-trial label."
)
MET = {"included", "not excluded"}
FAILED = {"excluded", "not included"}
UNKNOWN = "not enough information"
NOT_APPLICABLE = "not applicable"

EXAMPLE = {
    "note": (
        "A 58-year-old woman presents with poorly controlled type 2 diabetes. Her HbA1c was 8.4 percent last month. "
        "She takes metformin 1000 mg twice daily. Her blood pressure is 132/84 mmHg. "
        "She has no history of myocardial infarction or stroke. She does not smoke."
    ),
    "inclusion": ["Adults aged 18 to 75 years", "Diagnosis of type 2 diabetes", "HbA1c between 7 and 10 percent"],
    "exclusion": ["History of myocardial infarction", "Current insulin therapy", "Pregnancy"],
    "source": "Invented for demonstration. Not a real patient and not from the dataset.",
}


class InputError(ValueError):
    """A problem with the user's input, with a message meant for display."""


def validate_note(text):
    text = (text or "").strip()
    if not text:
        raise InputError("Enter a patient note first.")
    if "\x00" in text:
        raise InputError("That file does not look like plain text.")
    if len(text) > MAX_NOTE_CHARACTERS:
        raise InputError(f"That note is too long. The limit is {MAX_NOTE_CHARACTERS:,} characters.")
    if sum(c.isalpha() for c in text) < 0.4 * len(text):
        raise InputError("That text does not look like a clinical note.")
    return text


def split_note(text):
    sentences = list(split_unseen_note(validate_note(text)).values())
    if not sentences:
        raise InputError("No sentences were found in that note.")
    if len(sentences) > MAX_SENTENCES:
        raise InputError(f"That note has too many sentences. The limit is {MAX_SENTENCES}.")
    return sentences


def validate_sentences(sentences):
    cleaned = [s.strip() for s in sentences or []]
    if not cleaned or not all(cleaned):
        raise InputError("Every sentence needs text. Remove any empty sentences.")
    if len(cleaned) > MAX_SENTENCES:
        raise InputError(f"That note has too many sentences. The limit is {MAX_SENTENCES}.")
    return dict(enumerate(cleaned))


def validate_criteria(inclusion, exclusion):
    items = [("inclusion", c.strip()) for c in inclusion or [] if c.strip()]
    items += [("exclusion", c.strip()) for c in exclusion or [] if c.strip()]
    if not items:
        raise InputError("Enter at least one inclusion or exclusion criterion.")
    if len(items) > MAX_CRITERIA:
        raise InputError(f"That is too many criteria. The limit is {MAX_CRITERIA}.")
    if any(len(text) > MAX_CRITERION_CHARACTERS for _, text in items):
        raise InputError(f"Each criterion must be under {MAX_CRITERION_CHARACTERS:,} characters.")
    return items


def validate_mode(mode):
    if mode not in MODES:
        raise InputError("Choose a valid decoding mode.")
    return mode


def build_record(index, criterion_type, criterion, verified, sentences, timing):
    """One criterion's complete result, traceable to the note's original sentence IDs."""
    if verified.valid:
        explanation = explain(verified.label, verified.evidence, sentences)
    else:
        explanation = "The model output could not be verified, so no verdict is reported."
    unconfirmed = verified.valid and verified.label != NOT_APPLICABLE and not verified.evidence
    missing = []
    if verified.label == UNKNOWN:
        missing.append("The note does not contain enough to settle this criterion.")
    if unconfirmed:
        missing.append(NO_EVIDENCE)
    return {
        "index": index,
        "criterion_type": criterion_type,
        "criterion": criterion,
        "label": verified.label,
        "valid": verified.valid,
        "unconfirmed": unconfirmed,
        "evidence_ids": list(verified.evidence),
        "evidence": [{"id": i, "text": sentences[i]} for i in verified.evidence],
        "explanation": explanation,
        "missing_information": missing,
        "errors": list(verified.errors),
        "raw_output": verified.raw,
        "timing": timing,
    }


def overall_result(records):
    """Apply the stated rule. A failure with no cited evidence cannot make a patient ineligible."""
    counts = {
        "met": sum(r["label"] in MET for r in records),
        "failed": sum(r["label"] in FAILED for r in records),
        "unknown": sum(r["label"] == UNKNOWN for r in records),
        "not_applicable": sum(r["label"] == NOT_APPLICABLE for r in records),
        "unverified": sum(r["label"] == INVALID for r in records),
        "no_evidence": sum(r["unconfirmed"] for r in records),
    }
    if any(r["label"] in FAILED and r["evidence_ids"] for r in records):
        outcome = "Likely ineligible"
    elif counts["unknown"] or counts["unverified"] or counts["no_evidence"]:
        outcome = "Needs review"
    else:
        outcome = "Potentially eligible"
    return {"outcome": outcome, "preliminary": True, "counts": counts, "rule": OVERALL_RULE}


def build_report(report_id, sentences, records, mode, provenance):
    note = "\n".join(sentences[i] for i in sorted(sentences))
    return {
        "id": report_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notice": NOTICE,
        "provenance": {**provenance, "decoding_mode": mode, "note_sha256": hashlib.sha256(note.encode("utf-8")).hexdigest()},
        "patient_sentences": [{"id": i, "text": sentences[i]} for i in sorted(sentences)],
        "overall": overall_result(records),
        "results": records,
    }


def render_report_html(report):
    """A self-contained, printable report. All values are escaped."""
    e = lambda value: html.escape(str(value))
    rows = []
    for record in report["results"]:
        evidence = "".join(f"<li>[{e(item['id'])}] {e(item['text'])}</li>" for item in record["evidence"]) or "<li>No sentence cited.</li>"
        missing = "".join(f"<p class='m'>{e(text)}</p>" for text in record["missing_information"])
        rows.append(
            f"<section><h3>{e(record['criterion_type'].title())}: {e(record['criterion'])}</h3>"
            f"<p class='v'>{e(record['label'].replace('__invalid__', 'unverified output'))}</p>"
            f"<ul>{evidence}</ul><p>{e(record['explanation'])}</p>{missing}</section>"
        )
    sentences = "".join(f"<li value='{e(s['id'])}'>{e(s['text'])}</li>" for s in report["patient_sentences"])
    provenance = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in report["provenance"].items())
    counts = ", ".join(f"{e(k.replace('_', ' '))}: {e(v)}" for k, v in report["overall"]["counts"].items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>CRS report {e(report['id'])}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:50rem;margin:2rem auto;padding:0 1rem;color:#111}}
.notice{{border:1px solid #111;padding:.6rem .9rem;font-weight:600}}section{{border-top:1px solid #ccc;padding:.6rem 0}}
.v{{font-weight:600}}.m{{color:#555}}table{{border-collapse:collapse}}th{{text-align:left;padding-right:1rem;font-weight:500}}</style></head>
<body><h1>CRS eligibility screening report</h1><p class="notice">{e(report['notice'])}</p>
<h2>Overall (preliminary): {e(report['overall']['outcome'])}</h2><p>{counts}</p><p>{e(report['overall']['rule'])}</p>
<h2>Criteria</h2>{''.join(rows)}<h2>Patient note</h2><ol start="0">{sentences}</ol>
<h2>Provenance</h2><table><tr><th>report</th><td>{e(report['id'])}</td></tr><tr><th>created (UTC)</th><td>{e(report['created_utc'])}</td></tr>{provenance}</table>
</body></html>"""


_HEADER = re.compile(r"^\s*(inclusion|exclusion)\s+criteria\s*:?\s*$", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
TRIAL_ID = re.compile(r"^NCT\d{8}$")


def parse_eligibility(text):
    """Split a ClinicalTrials.gov eligibility section into inclusion and exclusion lines."""
    groups, current = {"inclusion": [], "exclusion": []}, None
    for line in (text or "").splitlines():
        header = _HEADER.match(line)
        if header:
            current = header.group(1).lower()
        elif current and line.strip():
            item = _BULLET.sub("", line).strip()
            if item:
                groups[current].append(item[:MAX_CRITERION_CHARACTERS])
    return groups
