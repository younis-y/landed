"""Write synthetic_demo/paypal-sample.json: six months of a fictional freelance designer's PayPal account,
in the exact shape the Transaction Search API returns, so it runs through the same mapping code.

Four clients pay her in three currencies. A payment in USD or EUR arrives in that currency, then PayPal
converts it into the GBP balance: one payment record plus two conversion records that point back to it.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "synthetic_demo" / "paypal-sample.json"
RATES = {"USD": 0.78, "EUR": 0.85}  # GBP per unit, after PayPal's conversion spread
rows, balance, ids = [], 1840.00, iter(range(1, 1000))


def record(day, currency, value, end, code, subject=None, payer=None, fee=0.0, ref=None):
    info = {
        "transaction_id": f"5SAMPLE{next(ids):05d}",
        "transaction_initiation_date": f"{day}T09:00:00+0000",
        "transaction_amount": {"currency_code": currency, "value": f"{value:.2f}"},
        "fee_amount": {"currency_code": currency, "value": f"{fee:.2f}"},
        "ending_balance": {"currency_code": currency, "value": f"{end:.2f}"},
        "transaction_event_code": code,
    }
    if subject:
        info["transaction_subject"] = subject
    if ref:
        info["paypal_reference_id"] = ref
    rows.append({"transaction_info": info, "payer_info": {"payer_name": {"alternate_full_name": payer}} if payer else {}})
    return info["transaction_id"]


def out(day, value, subject, code="T0003"):
    global balance
    balance = round(balance + value, 2)
    record(day, "GBP", value, balance, code, subject=subject)


def paid(day, client, currency, value):
    """A client payment, net of PayPal's fee; foreign currency is converted into the GBP balance."""
    global balance
    fee = -round(value * 0.029 + 0.30, 2)
    if currency == "GBP":
        balance = round(balance + value + fee, 2)
        record(day, "GBP", value, balance, "T0006", payer=client, fee=fee)
        return
    net = round(value + fee, 2)
    payment = record(day, currency, value, net, "T0006", payer=client, fee=fee)
    record(day, currency, -net, 0.0, "T0200", ref=payment)
    balance = round(balance + round(net * RATES[currency], 2), 2)
    record(day, "GBP", round(net * RATES[currency], 2), balance, "T0200", ref=payment)


CLIENTS = {  # month: [(day, client, currency, amount)]
    5: [(2, "Northwind Studio Ltd", "GBP", 1400), (9, "Brightline Inc", "USD", 1800), (21, "Kaya Design GmbH", "EUR", 1100)],
    6: [(2, "Northwind Studio Ltd", "GBP", 1400), (11, "Brightline Inc", "USD", 1500), (19, "Atlas Media", "GBP", 650)],
    7: [(2, "Northwind Studio Ltd", "GBP", 1400), (17, "Kaya Design GmbH", "EUR", 1300), (26, "Atlas Media", "GBP", 480)],
    8: [(2, "Northwind Studio Ltd", "GBP", 1400), (8, "Brightline Inc", "USD", 2100), (23, "Kaya Design GmbH", "EUR", 900)],
    9: [(2, "Northwind Studio Ltd", "GBP", 1400), (10, "Brightline Inc", "USD", 1650), (20, "Atlas Media", "GBP", 900)],
    10: [(2, "Northwind Studio Ltd", "GBP", 1400), (9, "Brightline Inc", "USD", 1500), (22, "Kaya Design GmbH", "EUR", 1250)],
}

record("2026-04-30", "GBP", 0.0, balance, "T0000", subject="Opening balance")
for month, payments in CLIENTS.items():
    m = f"2026-{month:02d}"
    events = [(day, lambda d=day, c=c, cur=cur, v=v: paid(f"{m}-{d:02d}", c, cur, v)) for day, c, cur, v in payments]
    events += [
        (1, lambda: out(f"{m}-01", -950.00, "Rent - Flat 4, Mare Street", "T0001")),
        (8, lambda: out(f"{m}-08", -68.40, "Octopus Energy")),
        (12, lambda: out(f"{m}-12", -18.00, "Three Mobile")),
        (15, lambda: out(f"{m}-15", -1200.00, "Transfer to Thames Bank", "T0400")),
        (24, lambda: out(f"{m}-24", -11.99, "Spotify")),
        (25, lambda: out(f"{m}-25", -1150.00, "Transfer to Harbour Savings", "T0400")),
    ]
    for _, event in sorted(events, key=lambda e: e[0]):
        event()

OUT.write_text(json.dumps({"transaction_details": rows}, indent=1) + "\n")
print(len(rows), "rows, closing balance", balance)
