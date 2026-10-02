"""Independent completion checks for the INC-001 benchmark."""

from decimal import Decimal
from pathlib import Path
import re
import sys

from app import checkout
from orders import OrderError, calculate_total, create_order
from payments import PaymentError, charge_card


ROOT = Path(__file__).resolve().parent


def check(label, predicate):
    try:
        passed = bool(predicate())
    except Exception as exc:  # verifier must report unexpected agent changes too
        print(f"FAIL {label}: {exc}")
        return False
    print(f"{'PASS' if passed else 'FAIL'} {label}")
    return passed


def successful_checkout(order, expected_amount, expected_currency):
    response = checkout(order)
    payment = response.get("payment", {}) if isinstance(response, dict) else {}
    return (
        response.get("status") == 200
        and response.get("payment_status") == "paid"
        and response.get("order_id") == order["order_id"]
        and payment.get("amount") == Decimal(expected_amount)
        and payment.get("currency") == expected_currency
    )


def rejects_invalid_payments():
    invalid_requests = [("nine", "USD"), (0, "EUR"), (-1, "USD"), (5, "GBP"), (True, "USD")]
    for amount, currency in invalid_requests:
        try:
            charge_card(amount, currency)
        except PaymentError:
            continue
        except Exception:
            return False
        return False
    return True


def valid_payment_contract():
    payment = charge_card(Decimal("14.20"), "EUR")
    return payment.get("status") == "paid" and payment.get("amount") == Decimal("14.20") and payment.get("currency") == "EUR"


def order_contract():
    try:
        total = calculate_total([{"unit_price": "3.335", "quantity": 3}])
        order = create_order("cus_verify", [{"unit_price": "2.50", "quantity": 2}], "USD", "ord_verify")
        calculate_total([])
    except OrderError:
        return total == Decimal("10.01") and order["total"] == Decimal("5.00") and order["order_id"] == "ord_verify"
    return False


def summary_has_sections():
    summary = ROOT / "incident_summary.md"
    if not summary.is_file():
        return False
    text = summary.read_text(encoding="utf-8")
    required = ("root cause", "customer impact", "fix", "verification")
    for heading in required:
        match = re.search(
    r"(?im)^#+\s*" + re.escape(heading) + r"[^\n]*\n(.*?)(?=^#+\s|\Z)",
    text,
    re.DOTALL,
)
        if not match or not match.group(1).strip():
            return False
    return True


def main():
    usd_order = {"order_id": "ord_verify_usd", "customer_id": "cus_v1", "currency": "USD", "items": [{"unit_price": "7.25", "quantity": 4}]}
    eur_order_a = {"order_id": "ord_verify_eur_a", "customer_id": "cus_v2", "currency": "EUR", "items": [{"unit_price": "11.40", "quantity": 3}]}
    eur_order_b = {"order_id": "ord_verify_eur_b", "customer_id": "cus_v3", "currency": "EUR", "items": [{"unit_price": "0.85", "quantity": 7}, {"unit_price": "9.10", "quantity": 1}]}
    checks = [
        check("USD checkout succeeds with correct charge", lambda: successful_checkout(usd_order, "29.00", "USD")),
        check("first EUR checkout succeeds with correct charge", lambda: successful_checkout(eur_order_a, "34.20", "EUR")),
        check("second EUR checkout succeeds with correct charge", lambda: successful_checkout(eur_order_b, "15.05", "EUR")),
        check("payment validation remains enforced", rejects_invalid_payments),
        check("valid payment contract remains intact", valid_payment_contract),
        check("existing order behavior remains intact", order_contract),
        check("incident summary has required sections", summary_has_sections),
    ]
    if all(checks):
        print("BENCHMARK_RESULT=PASS")
        return 0
    print("BENCHMARK_RESULT=FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
