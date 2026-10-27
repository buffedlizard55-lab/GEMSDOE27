#!/usr/bin/env python3
"""Audit existing run cards without training, uploads, or external requests."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27.readiness import publication_decision  # noqa: E402


def audit_cards(root: Path) -> dict:
    cards = sorted((root / "evidence").glob("*run_card*.json"))
    results = {}
    for path in cards:
        try:
            card = json.loads(path.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            results[path.name] = {
                "ok_to_publish_as_submission": False,
                "slot_authorized": False,
                "actual_sha256": None,
                "reasons": [f"unreadable run card: {type(exc).__name__}"],
                "scope": "Evidence could not be read; no approval",
            }
            continue
        results[path.name] = publication_decision(card, root)
    evidence_passed = [k for k, v in results.items() if v["ok_to_publish_as_submission"]]
    # Keep selector authorization distinct from technical/scientific evidence. A passing
    # run card cannot authorize a weekly slot; the selector must record that separately.
    slot_authorized = [
        k for k, v in results.items()
        if v["ok_to_publish_as_submission"] and v["slot_authorized"] is True
    ]
    return {
        "purpose": "Fail-closed evidence/byte audit, not a new geological experiment",
        "evidence_passed_not_slot_authorized": evidence_passed,
        "slot_authorized": slot_authorized,
        "results": results,
    }


def main():
    report = audit_cards(ROOT)
    out = ROOT / "docs/data/submission_readiness_audit.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
