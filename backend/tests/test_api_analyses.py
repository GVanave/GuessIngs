import uuid

import pytest
from sqlalchemy.exc import OperationalError

from app.schemas import AnalysisOut

SAMPLE = ("Ingredients: Whole Grain Oats, Sugar, Chocolate Chips (Sugar, Cocoa Butter, Soy Lecithin), "
          "Salt, Natural Flavor.")


def analyze(client, text=SAMPLE, **extra):
    res = client.post("/api/analyses", json={"ingredients_text": text, **extra})
    assert res.status_code == 201, res.text
    return res.json()


def test_full_analysis_result(auth_client):
    data = analyze(auth_client, product_name="Choco Oat Bar", brand="Acme")
    AnalysisOut.model_validate(data)  # JSON schema validation
    # 100 − 25 (sugar 2nd) − 5 (soy lecithin) − 20 (NOVA 4) + 5 (oats) = 55
    assert data["score"] == 55
    assert data["verdict"] == "YELLOW"
    assert data["nova_group"] == 4
    codes = {line["code"]: line["points"] for line in data["breakdown"]}
    assert codes == {"start": 100, "added_sugar": -25, "emulsifier": -5, "nova4": -20, "fiber_protein": 5}
    assert sum(codes.values()) == data["score"]
    assert data["product"]["name"] == "Choco Oat Bar"
    assert data["product"]["category"] == "snack_bar"
    assert {c["canonical_name"] for c in data["concerns"]} == {"sugar", "soy lecithin"}
    assert "whole grain oats" in {p["canonical_name"] for p in data["positives"]}
    assert data["scoring_version"] == "1.0.0"
    assert data["alternatives"] and data["explanation"]["summary"].startswith("This product scored 55/100")
    dup = [i for i in data["ingredients"] if i["is_duplicate"]]
    assert [i["canonical_name"] for i in dup] == ["sugar"]


def test_same_input_produces_identical_result(auth_client):
    a = analyze(auth_client)
    b = analyze(auth_client, text=SAMPLE.upper().replace("INGREDIENTS:", "ingredients :"))
    for key in ("score", "verdict", "breakdown", "input_hash", "nova_group"):
        assert a[key] == b[key], key


def test_empty_and_invalid_input_give_friendly_errors(auth_client):
    res = auth_client.post("/api/analyses", json={"ingredients_text": ""})
    assert res.status_code == 422 and res.json()["error"]["code"] == "validation_error"
    res = auth_client.post("/api/analyses", json={"ingredients_text": "   ,,, 123"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "no_ingredients"
    assert "Traceback" not in res.text
    res = auth_client.post("/api/analyses", json={"ingredients_text": "oats", "sodium_mg_per_100g": -5})
    assert res.status_code == 422
    res = auth_client.post("/api/analyses", json={"ingredients_text": "x" * 6000})
    assert res.status_code == 422


def test_sodium_rule_via_api(auth_client):
    low = analyze(auth_client, text="potatoes, sunflower oil, salt", sodium_mg_per_100g=300)
    high = analyze(auth_client, text="potatoes, sunflower oil, salt", sodium_mg_per_100g=900)
    assert low["score"] - high["score"] == 10
    assert any(line["code"] == "sodium" for line in high["breakdown"])


def test_green_and_red_examples(auth_client):
    green = analyze(auth_client, text="rolled oats, almonds, chia seeds, cinnamon")
    assert green["verdict"] == "GREEN" and green["score"] == 100
    red = analyze(auth_client, text=("high fructose corn syrup, partially hydrogenated soybean oil, "
                                     "artificial flavor, red 40, yellow 6, sodium benzoate, sucralose"))
    assert red["verdict"] == "RED" and red["score"] == 0


def test_history_list_filter_search_and_pagination(auth_client):
    analyze(auth_client, text="rolled oats", product_name="Oats")
    analyze(auth_client, text="sugar, red 40", product_name="Candy")
    analyze(auth_client, text="sugar, salt", product_name="Sweet Crackers")
    page = auth_client.get("/api/analyses?limit=2").json()
    assert page["total"] == 3 and len(page["items"]) == 2
    assert page["items"][0]["product"]["name"] == "Sweet Crackers"  # newest first
    assert auth_client.get("/api/analyses?verdict=GREEN").json()["total"] == 1
    assert auth_client.get("/api/analyses?q=cand").json()["items"][0]["product"]["name"] == "Candy"
    assert auth_client.get("/api/analyses?verdict=PURPLE").status_code == 422


def test_users_cannot_access_each_others_data(make_client):
    alice, bob = make_client(), make_client()
    a = analyze(alice)
    assert bob.get(f"/api/analyses/{a['id']}").status_code == 404
    assert bob.request("DELETE", f"/api/analyses/{a['id']}").status_code == 404
    assert bob.patch(f"/api/products/{a['product']['id']}", json={"is_saved": True}).status_code == 404
    assert bob.get("/api/analyses").json()["total"] == 0
    assert alice.get(f"/api/analyses/{a['id']}").status_code == 200


def test_verify_endpoint_confirms_reproducibility(auth_client):
    a = analyze(auth_client)
    v = auth_client.get(f"/api/analyses/{a['id']}/verify").json()
    assert v["matches"] is True and v["recomputed_score"] == a["score"]


def test_save_product_and_saved_list(auth_client):
    a = analyze(auth_client, product_name="Granola")
    pid = a["product"]["id"]
    assert auth_client.patch(f"/api/products/{pid}", json={"is_saved": True, "notes": "kids like it"}).json()["is_saved"]
    saved = auth_client.get("/api/products/saved").json()
    assert len(saved) == 1 and saved[0]["notes"] == "kids like it" and saved[0]["latest"]["id"] == a["id"]
    auth_client.patch(f"/api/products/{pid}", json={"is_saved": False})
    assert auth_client.get("/api/products/saved").json() == []


def test_reanalyzing_same_product_reuses_product(auth_client):
    a = analyze(auth_client, product_name="Granola")
    b = analyze(auth_client, product_name="granola")
    assert a["product"]["id"] == b["product"]["id"]


def test_delete_analysis(auth_client):
    a = analyze(auth_client)
    assert auth_client.request("DELETE", f"/api/analyses/{a['id']}").status_code == 204
    assert auth_client.get(f"/api/analyses/{a['id']}").status_code == 404
    assert auth_client.get(f"/api/analyses/{uuid.uuid4()}").status_code == 404
    assert auth_client.get("/api/analyses/not-a-uuid").status_code == 422


def test_compare_products(auth_client):
    good = analyze(auth_client, text="rolled oats, almonds", product_name="Muesli")
    bad = analyze(auth_client, text="sugar, corn flakes, red 40", product_name="Frosted Flakes")
    res = auth_client.get(f"/api/compare?ids={good['id']}&ids={bad['id']}").json()
    assert res["best_id"] == good["id"]
    assert [i["id"] for i in res["items"]] == [good["id"], bad["id"]]
    assert auth_client.get(f"/api/compare?ids={good['id']}").status_code == 422
    assert auth_client.get(f"/api/compare?ids={good['id']}&ids={good['id']}").status_code == 422


def test_history_alternatives_suggest_better_products(auth_client):
    good = analyze(auth_client, text="rolled oats, almonds", product_name="Plain Muesli")
    bad = analyze(auth_client, text="sugar, corn flakes, red 40", product_name="Frosted Cereal")
    history = [a for a in bad["alternatives"] if a["kind"] == "history"]
    assert history and history[0]["analysis_id"] == good["id"]


def test_dashboard_stats(auth_client):
    analyze(auth_client, text="rolled oats")
    analyze(auth_client, text="sugar, red 40")
    d = auth_client.get("/api/dashboard").json()
    assert d["total_analyses"] == 2
    assert d["verdict_counts"]["GREEN"] == 1
    assert len(d["recent"]) == 2 and d["average_score"] is not None


def test_public_scoring_rules_and_health(client):
    rules = client.get("/api/meta/scoring-rules").json()
    assert rules["start"] == 100 and len(rules["deductions"]) == 9
    assert client.get("/api/health").json() == {"status": "ok"}


def test_unexpected_errors_do_not_leak_details(auth_client, monkeypatch):
    from app.services import analysis as svc

    def boom(*a, **k):
        raise RuntimeError("secret internal detail at /srv/app.py line 42")

    monkeypatch.setattr(svc, "run_analysis", boom)
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        c.cookies.update(auth_client.cookies)
        res = c.post("/api/analyses", json={"ingredients_text": "oats"}, headers=dict(auth_client.headers))
    assert res.status_code == 500
    assert "secret" not in res.text and "Traceback" not in res.text
    assert res.json()["error"]["code"] == "internal_error"


def test_database_failure_returns_503(auth_client, monkeypatch):
    from app.services import analysis as svc

    def db_down(*a, **k):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(svc, "run_analysis", db_down)
    res = auth_client.post("/api/analyses", json={"ingredients_text": "oats"})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "database_unavailable"
    assert "refused" not in res.text


@pytest.mark.parametrize("payload", [
    {"ingredients_text": "oats", "source": "telepathy"},
    {"ingredients_text": "oats", "product_name": "x" * 200},
    {"ingredients_text": 123},
])
def test_invalid_payloads_rejected(auth_client, payload):
    assert auth_client.post("/api/analyses", json=payload).status_code == 422


@pytest.mark.parametrize("name", ["Coke Classic", "Untitled product"])
def test_soft_drinks_are_detected_from_name_or_label(auth_client, name):
    data = analyze(auth_client, text="Carbonated water, sugar, colour (150d), food acid (338), flavour, caffeine",
                   product_name=name)
    assert data["product"]["category"] == "soft_drink"
    assert (data["score"], data["verdict"]) == (34, "RED")
    assert any("Sparkling water" in a["title"] for a in data["alternatives"])
