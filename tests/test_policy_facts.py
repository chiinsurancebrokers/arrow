"""These are the regression tests that matter most: they pin down the exact
renewal figures so a future edit can't silently drift from the certificate."""

from backend.app.knowledge.policy_facts import load_policy_facts


def test_certificate_identifiers():
    facts = load_policy_facts()
    cert = facts["certificate"]
    assert cert["certificate_no"] == "CGT P804302600"
    assert cert["binder_reference"] == "B1735ND0054525"
    assert cert["period_of_insurance"] == "1st September 2026 to 31st August 2027 (both dates inclusive)"


def test_renewed_benefit_amounts():
    facts = load_policy_facts()
    sections = facts["sections"]
    assert sections["2"]["sum_insured_eur_per_person"] == 15000
    assert sections["3"]["sum_insured_eur"] == 15000
    assert sections["3"]["business_equipment_max_eur"] == 3000
    assert sections["4"]["sum_insured_eur"] == 10000
    assert sections["4"]["cash_limit_eur"] == 3000
    assert sections["4"]["rental_vehicle_excess"]["per_event_eur"] == 1000


def test_unchanged_benefit_amounts_still_match():
    facts = load_policy_facts()
    sections = facts["sections"]
    assert sections["1"]["sum_insured_eur"] == 10000000
    assert sections["6"]["personal_liability_eur"] == 5000000
    assert sections["8"]["sum_insured_eur"] == 50000


def test_kidnap_country_list_is_complete():
    facts = load_policy_facts()
    countries = set(facts["endorsements"]["kidnap_exclusion"]["named_countries"])
    expected = {
        "Afghanistan", "Belarus", "Colombia", "Gaza", "Israel", "Iraq", "Lebanon",
        "Mexico", "Nigeria", "Pakistan", "Philippines", "Russia", "Somalia",
        "Ukraine", "Venezuela", "Yemen",
    }
    assert countries == expected


def test_any_one_accident_cap_present():
    facts = load_policy_facts()
    assert facts["any_one_accident_limit"]["limit_eur"] == 10000000
