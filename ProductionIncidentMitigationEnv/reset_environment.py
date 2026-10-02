from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Restore the original buggy app.py
buggy_app = '''"""Application-facing checkout entry point."""

from orders import OrderError, create_order
from payments import PaymentError, charge_card


def checkout(order):
    """Charge a validated order and return an HTTP-like response dictionary."""
    try:
        prepared_order = create_order(
            order["customer_id"],
            order["items"],
            order["currency"],
            order.get("order_id"),
        )
        if prepared_order["currency"] == "EUR":
            payment = charge_card(
                prepared_order["currency"],
                prepared_order["total"]
            )
        else:
            payment = charge_card(
                prepared_order["total"],
                prepared_order["currency"]
            )
        return {
            "status": 200,
            "order_id": prepared_order["order_id"],
            "payment_status": payment["status"],
            "payment": payment,
        }
    except (KeyError, OrderError, PaymentError, ValueError, TypeError):
        return {"status": 500, "error": "checkout could not be completed"}
'''

(ROOT / "app.py").write_text(buggy_app, encoding="utf-8")

# Remove artifact produced by the agent
summary = ROOT / "incident_summary.md"

if summary.exists():
    summary.unlink()

print("Environment reset successfully.")
