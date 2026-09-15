from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
archive_path = ROOT / "data" / "trips" / "archive_2025-09_2026-08.json"
current_path = ROOT / "data" / "trips" / "current_2026-09_2027-08.json"

archive = json.loads(archive_path.read_text(encoding="utf-8"))
archive["total_days_used"] = 250
archive["allocation_note"] = (
    "Final prior-pool accounting: Myrsini Andreou 16-18 Sep 2026 charged the last 3 days "
    "to reach 250/250. Pierre Loth 1-4 Sep 2026 was approved separately by Pulse as goodwill "
    "with zero additional pool charge."
)

by_name = {e["name"]: e for e in archive["employees"]}

myrsini = by_name["MYRSINI ANDREOU"]
if not any(t.get("dates") == "16/09/2026 - 18/09/2026" and t.get("route") == "ATH-GVA-ATH" for t in myrsini["trips"]):
    myrsini["trips"].append({
        "days": 3,
        "pool_charge_days": 3,
        "dates": "16/09/2026 - 18/09/2026",
        "route": "ATH-GVA-ATH",
        "policy_allocation": "prior",
        "final_pool_trip": True,
        "allocation_note": "Final 3-day deduction from the previous 250-day administrative pool; pool exhausted to 250/250."
    })

pierre = by_name["PIERRE LOTH"]
if not any(t.get("dates") == "01/09/2026 - 04/09/2026" and t.get("route") == "ATH-GVA-ATH" for t in pierre["trips"]):
    pierre["trips"].append({
        "days": 4,
        "pool_charge_days": 0,
        "dates": "01/09/2026 - 04/09/2026",
        "route": "ATH-GVA-ATH",
        "policy_allocation": "prior",
        "goodwill_exception": True,
        "approval_note": "Pulse goodwill extension approved by Oliver Slaney to assist renewal; no additional charge to the exhausted 250-day pool."
    })

archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

current = json.loads(current_path.read_text(encoding="utf-8"))
for employee in current.get("employees", []):
    employee["trips"] = []

seed = {
    "KOSTOPOULOS KONSTANTINOS": [{
        "days": 3, "pool_charge_days": 3,
        "start_date": "2026-09-02", "end_date": "2026-09-04",
        "dates": "02/09/2026 - 04/09/2026", "route": "ATH-GVA-ATH",
        "policy_allocation": "current", "notes": "ANTAEUS"
    }],
    "MAXIMILLIAN KATSAROS": [{
        "days": 4, "pool_charge_days": 4,
        "start_date": "2026-09-15", "end_date": "2026-09-18",
        "dates": "15/09/2026 - 18/09/2026", "route": "ATH-GVA-ATH",
        "policy_allocation": "current", "notes": "ANTAEUS"
    }],
    "ODYSSEAS RENIERIS": [{
        "days": 7, "pool_charge_days": 7,
        "start_date": "2026-10-24", "end_date": "2026-10-30",
        "dates": "24/10/2026 - 30/10/2026", "route": "ATH-SIN-ATH",
        "policy_allocation": "current"
    }],
    "CONSTANTINE MARK HADJIPATERAS": [{
        "days": 9, "pool_charge_days": 9,
        "start_date": "2026-11-07", "end_date": "2026-11-15",
        "dates": "07/11/2026 - 15/11/2026", "route": "ATH-DXB-ATH",
        "policy_allocation": "current"
    }],
}
for employee in current.get("employees", []):
    if employee["name"] in seed:
        employee["trips"] = seed[employee["name"]]

current["note"] = (
    "2026/27 seed contains the four confirmed renewal-period trips supplied by CHI. "
    "Live changes are stored in PostgreSQL. Initial seeded pool charge is 23 days, leaving 227."
)
current_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("v3.6 data allocation applied:")
print("- prior archive: 250/250, Myrsini final 3 days, Pierre goodwill 0 pool days")
print("- current seed: 4 employees / 4 trips / 23 pool days / 227 remaining")
