"""Follow-ups after the backlog review: KP closed-day hint, large-cap configs."""


def test_kp_report_on_a_closed_day_names_the_next_session(client):
    # 2026-10-04 is a Sunday; 2026-10-02 (Gandhi Jayanti) is a holiday.
    body = client.get("/api/kp_intraday_report?date=2026-10-04&format=json").get_json()
    assert body["holiday"] == "Weekend" and body["next_trading_day"] == "2026-10-05"
    body = client.get("/api/kp_intraday_report?date=2026-10-02&format=json").get_json()
    assert body["next_trading_day"] == "2026-10-05"


def test_largecap_configs_have_no_unchecked_conditions(client):
    body = client.get("/api/largecap_divergence?date=2026-09-14").get_json()
    names = [c["name"] for c in body["configs"]]
    assert not any("Adhik" in n for n in names)
    assert body["summary"].startswith(f"{body['active_count']}/{len(names)} ")
