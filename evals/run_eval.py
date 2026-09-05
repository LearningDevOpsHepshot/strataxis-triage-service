"""Evaluate the classifier against a fixed, labelled dataset.

Unit tests check whether the program works correctly.
This script checks whether the classifier is accurate enough to release.

The script returns exit code 1 when accuracy is below the required threshold.
Jenkins interprets exit code 1 as a failed build and stops deployment.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from app.classifier import classify  # noqa: E402

EVAL_FILE = ROOT / "evals" / "eval_set.jsonl"
REPORT_DIR = ROOT / "reports"


def load_cases() -> list[dict]:
    """Load and validate evaluation cases from the JSONL file."""
    cases = []

    if not EVAL_FILE.exists():
        print(f"ERROR: Evaluation file not found: {EVAL_FILE}")
        return cases

    with EVAL_FILE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as error:
                print(
                    f"ERROR: Invalid JSON in {EVAL_FILE.name}, "
                    f"line {line_number}: {error}"
                )
                raise

            required_fields = {"id", "text", "expected"}
            missing_fields = required_fields - case.keys()

            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ValueError(
                    f"Line {line_number} is missing required fields: {missing}"
                )

            cases.append(case)

    return cases


def run(threshold: float) -> int:
    """Run the evaluation and return an operating-system exit code."""
    if not 0.0 <= threshold <= 1.0:
        print("ERROR: Threshold must be between 0.0 and 1.0.")
        return 1

    cases = load_cases()

    if not cases:
        print("ERROR: No evaluation cases were found.")
        return 1

    rows = []
    passed = 0

    for case in cases:
        result = classify(case["text"])
        passed_case = result["label"] == case["expected"]

        if passed_case:
            passed += 1

        rows.append(
            {
                "id": case["id"],
                "text": case["text"],
                "expected": case["expected"],
                "predicted": result["label"],
                "confidence": result["confidence"],
                "pass": passed_case,
            }
        )

    total = len(rows)
    accuracy = round(passed / total, 4)
    verdict = "PASS" if accuracy >= threshold else "FAIL"

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

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(summary)
    write_html(summary)
    print_results(summary)

    return 0 if verdict == "PASS" else 1


def write_json(summary: dict) -> None:
    """Write the evaluation results to a JSON report."""
    report_file = REPORT_DIR / "eval_report.json"

    report_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )


def write_html(summary: dict) -> None:
    """Write the evaluation results to an HTML report."""
    pass_colour = "#0E7C7B"
    fail_colour = "#B3261E"

    verdict_colour = (
        pass_colour
        if summary["verdict"] == "PASS"
        else fail_colour
    )

    table_rows = []

    for result in summary["results"]:
        result_text = "PASS" if result["pass"] else "FAIL"
        result_colour = pass_colour if result["pass"] else fail_colour

        case_id = escape(str(result["id"]))
        message = escape(str(result["text"]))
        expected = escape(str(result["expected"]))
        predicted = escape(str(result["predicted"]))
        confidence = escape(str(result["confidence"]))

        table_rows.append(
            "<tr>"
            f"<td>{case_id}</td>"
            f"<td>{message}</td>"
            f"<td>{expected}</td>"
            f"<td>{predicted}</td>"
            f"<td>{confidence}</td>"
            f"<td style='color:{result_colour};font-weight:700'>"
            f"{result_text}</td>"
            "</tr>"
        )

    body = "".join(table_rows)

    html = f"""<!doctype html>
<html lang="en">
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
<p>
Build <strong>{summary['build']}</strong>
· {summary['generated_at']}
</p>
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

    report_file = REPORT_DIR / "eval_report.html"
    report_file.write_text(html, encoding="utf-8")


def print_results(summary: dict) -> None:
    """Display the evaluation results in Command Prompt or Jenkins."""
    print("=" * 62)
    print("  EVALUATION GATE")
    print("=" * 62)

    for row in summary["results"]:
        mark = "PASS" if row["pass"] else "FAIL"
        expected = row["expected"]
        predicted = row["predicted"]

        print(
            f"  [{mark}] {row['id']} "
            f"exp={expected:<15} got={predicted}"
        )

    print("-" * 62)
    print(
        f"  Accuracy : {summary['accuracy']:.2%} "
        f"({summary['passed']}/{summary['total_cases']})"
    )
    print(f"  Threshold: {summary['threshold']:.2%}")
    print(f"  Verdict  : {summary['verdict']}")
    print("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate the Strataxis client signal classifier."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Minimum required accuracy between 0.0 and 1.0.",
    )
    arguments = parser.parse_args()

    sys.exit(run(arguments.threshold))