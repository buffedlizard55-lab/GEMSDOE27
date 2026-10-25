#!/usr/bin/env python3
"""Audit existing run cards without training, uploads, or external requests."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27.readiness import publication_decision  # noqa: E402


def main():
    cards = sorted((ROOT / "evidence").glob("*run_card*.json"))
    results = {p.name: publication_decision(json.loads(p.read_text()), ROOT) for p in cards}
    report = {"purpose": "Fail-closed evidence/byte audit, not a new geological experiment",
              "approved": [k for k, v in results.items() if v["ok_to_publish_as_submission"]],
              "results": results}
    out = ROOT / "docs/data/submission_readiness_audit.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
