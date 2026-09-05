"""Evaluate the classifier against a fixed, labelled dataset.

Unit tests ask whether the code works correctly.
This script asks whether the classifier is good enough to release.

It returns exit code 1 when accuracy is below the required threshold.
This causes Jenkins to fail the build and stop deployment.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier import classify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVAL_FILE = ROOT / "evals" / "eval_set.jsonl"
REPORT_DIR = ROOT / "reports"


def load_cases():
    cases = []

    with open(EVAL_FILE, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if line:
                cases.append(json.loads(line))

    return cases


def run(threshold: float) -> int:
    cases = load_cases()
    rows = []
    passed = 0

    for case in cases:
        result = classify(case["text"])
        ok = result["label"] == case["expected"]
        passed += 1 if ok else 0

        rows.append(
            {
                "id": case["id"],
                "text": case["text"],
                "expected": case["expected"],
                "predicted": result["label"],
                "confidence": result["confidence"],
                "pass": ok,
            }
        )

    total = len(rows)
    accuracy = round(passed / total, 4) if total else 0.0
    verdict = "PASS" if accuracy >= threshold else "FAIL"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "build": os.environ.get("BUILD_NUMBER", "local"),
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": accuracy,
        "threshold": threshold,
        "verdict": verdict,
        "results": rows,
    }

    json_report = REPORT_DIR / "eval_report.json"
    json_report.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    write_html(summary)

    print("=" * 62)
    print("  EVALUATION GATE")
    print("=" * 62)

    for row in rows:
        mark = "PASS" if row["pass"] else "FAIL"
        expected = row["expected"]
        predicted = row["predicted"]

        print(
            f"  [{mark}] {row['id']} "
            f"exp={expected:<15} got={predicted}"
        )

    print("-" * 62)
    print(f"  Accuracy : {accuracy:.2%} ({passed}/{total})")
    print(f"  Threshold: {threshold:.2%}")
    print(f"  Verdict  : {verdict}")
    print("=" * 62)

    return 0 if verdict == "PASS" else 1


def write_html(summary: dict) -> None:
    pass_colour = "#0E7C7B"
    fail_colour = "#B3261E"

    if summary["verdict"] == "PASS":
        verdict_colour = pass_colour
    else:
        verdict_colour = fail_colour

    table_rows = []

    for result in summary["results"]:
        result_text = "PASS" if result["pass"] else "FAIL"
        result_colour = pass_colour if result["pass"] else fail_colour

        table_rows.append(
            "<tr>"
            f"<td>{result['id']}</td>"
            f"<td>{result['text']}</td>"
            f"<td>{result['expected']}</td>"
            f"<td>{result['predicted']}</td>"
            f"<td>{result['confidence']}</td>"
            f"<td style='color:{result_colour};font-weight:700'>"
            f"{result_text}</td>"
            "</tr>"
        )

    body = "".join(table_rows)

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Evaluation Report - Build {summary['build']}</title>
<style>
body {{
    font-family: Calibri, Arial, sans-serif;
    margin: 24px;
    color: #142B4B;
}}
h1 {{
    color: #142B4B;
}}
.verdict {{
    color: {verdict_colour};
    font-weight: 700;
    font-size: 20px;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 14px;
    font-size: 14px;
}}
th {{
    background: #142B4B;
    color: #ffffff;
    text-align: left;
    padding: 8px;
}}
td {{
    border-bottom: 1px solid #dddddd;
    padding: 8px;
}}
</style>
</head>
<body>
<h1>Strataxis Classifier — Evaluation Report</h1>
<p>Build <b>{summary['build']}</b> · {summary['generated_at']}</p>
<p class="verdict">
{summary['verdict']} — accuracy {summary['accuracy']:.2%}
(threshold {summary['threshold']:.2%})
</p>
<table>
<tr>
<th>ID</th>
<th>Message</th>
<th>Expected</th>
<th>Predicted</th>
<th>Confidence</th>
<th>Result</th>
</tr>
{body}
</table>
</body>
</html>
"""

    html_report = REPORT_DIR / "eval_report.html"
    html_report.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
    )
    arguments = parser.parse_args()
    sys.exit(run(arguments.threshold))
