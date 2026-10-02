import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESOLUTION = ROOT / "output" / "resolution.json"


def check(name, condition):
    if condition:
        print(f"PASS {name}")
        return True

    print(f"FAIL {name}")
    return False


def main():
    results = []

    # Check that the WorkGraph produced a resolution
    results.append(
        check(
            "resolution.json exists",
            RESOLUTION.is_file()
        )
    )

    if not RESOLUTION.is_file():
        print("WORKGRAPH_RESULT=FAIL")
        return 1

    # Check valid JSON
    try:
        resolution = json.loads(
            RESOLUTION.read_text(encoding="utf-8")
        )
        results.append(check("resolution is valid JSON", True))
    except Exception:
        results.append(check("resolution is valid JSON", False))
        print("WORKGRAPH_RESULT=FAIL")
        return 1

    expected_fields = {
        "case_id",
        "order_id",
        "customer_id",
        "valid_transaction",
        "duplicate_transaction",
        "action",
        "refund_transaction",
        "new_payment_status",
    }

    results.append(
        check(
            "resolution contains exactly required fields",
            set(resolution.keys()) == expected_fields
        )
    )

    results.append(
        check(
            "correct case identified",
            resolution.get("case_id") == "CE-001"
        )
    )

    results.append(
        check(
            "correct order identified",
            resolution.get("order_id") == "ORD-1042"
        )
    )

    results.append(
        check(
            "correct customer identified",
            resolution.get("customer_id") == "CUS-501"
        )
    )

    results.append(
        check(
            "valid payment retained",
            resolution.get("valid_transaction") == "txn_88201"
        )
    )

    results.append(
        check(
            "duplicate payment identified",
            resolution.get("duplicate_transaction") == "txn_88202"
        )
    )

    results.append(
        check(
            "correct transaction selected for refund",
            resolution.get("refund_transaction") == "txn_88202"
        )
    )

    results.append(
        check(
            "order corrected to PAID",
            resolution.get("new_payment_status") == "PAID"
        )
    )

    # Allow wording variation while requiring the important actions.
    action = str(resolution.get("action", "")).lower()

    results.append(
        check(
            "overall action includes duplicate refund",
            "refund" in action
        )
    )

    results.append(
        check(
            "overall action includes order correction",
            "paid" in action or "correct" in action
        )
    )

    if all(results):
        print("WORKGRAPH_RESULT=PASS")
        return 0

    print("WORKGRAPH_RESULT=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
