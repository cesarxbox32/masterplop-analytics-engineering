from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "masterplop.duckdb"
AGGREGATE_DIR = ROOT / "data" / "processed" / "dashboard"
sys.path.insert(0, str(ROOT / "dashboard"))

from data_access import DashboardDataError, QUERIES, load_dashboard_data  # noqa: E402


@pytest.fixture(scope="module")
def dashboard_data():
    return load_dashboard_data(DB_PATH)


def test_dashboard_reads_only_expected_aggregates(dashboard_data) -> None:
    assert {name: len(frame) for name, frame in dashboard_data.items()} == {
        "executive": 1,
        "volume": 4,
        "quarterly_ticket": 2,
        "regional_ticket": 45,
        "top_mcg": 10,
        "contactless": 17,
        "cashback": 1,
        "cashback_sensitivity": 1,
        "cashback_is_xb": 1,
        "cashback_diagnostic": 4,
        "quality": 1,
    }
    assert all(
        "card_id" not in frame.columns
        for frame in dashboard_data.values()
    )
    assert all("dashboard." in query.lower() for query in QUERIES.values())


def test_dashboard_missing_database_has_controlled_error(tmp_path: Path) -> None:
    with pytest.raises(DashboardDataError, match="Ejecuta src/pipeline.py primero"):
        load_dashboard_data(tmp_path / "missing.duckdb")


def test_dashboard_can_run_from_public_aggregates_without_duckdb(tmp_path: Path) -> None:
    data = load_dashboard_data(tmp_path / "missing.duckdb", AGGREGATE_DIR)
    reference = load_dashboard_data(DB_PATH)
    assert {name: len(frame) for name, frame in data.items()} == {
        name: len(frame) for name, frame in reference.items()
    }
    assert all("card_id" not in frame.columns for frame in data.values())


def test_public_dashboard_exports_are_complete_and_safe() -> None:
    expected = {f"{name}.csv" for name in QUERIES} | {"manifest.json"}
    assert {path.name for path in AGGREGATE_DIR.iterdir()} == expected
    for csv_path in AGGREGATE_DIR.glob("*.csv"):
        frame = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert "card_id" not in frame.columns

    manifest = json.loads((AGGREGATE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["datasets"]) == set(QUERIES)
    for dataset in manifest["datasets"].values():
        assert "card_id" not in dataset["columns"]
        assert all("card_id" not in record for record in dataset["records"])


def test_dashboard_schema_has_no_individual_card_identifier() -> None:
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        exposed = connection.execute(
            """
            SELECT table_name, column_name
            FROM duckdb_columns()
            WHERE schema_name = 'dashboard'
              AND lower(column_name) = 'card_id'
            """
        ).fetchall()
    finally:
        connection.close()
    assert exposed == []


def test_executive_summary_matches_validated_metrics(dashboard_data) -> None:
    summary = dashboard_data["executive"].iloc[0]
    assert summary.active_cards == 59997
    assert summary.transaction_count == 2400000
    assert summary.total_net_spend_usd == pytest.approx(430124709.40)
    assert summary.avg_transaction_amount_usd == pytest.approx(179.22)
    assert summary.total_cashback_usd == pytest.approx(178471.62)
    assert summary.beneficiary_card_count == 4029


def test_campaign_cards_remain_fixed(dashboard_data) -> None:
    campaign = dashboard_data["cashback"].iloc[0]
    assert campaign.total_cashback_usd == pytest.approx(178471.62)
    assert campaign.beneficiary_card_count == 4029
    assert campaign.capped_card_count == 2676
    assert campaign.net_eligible_spend_usd == pytest.approx(7319379.70)


def test_chart_source_values_match_validated_kpis(dashboard_data) -> None:
    volume = dashboard_data["volume"]
    values = {
        (row.period_year, row.period_quarter, row.product_type): row.active_cards
        for row in volume.itertuples(index=False)
    }
    assert values[(2024, 1, "Crédito")] == 46747
    assert values[(2024, 2, "Crédito")] == 51037
    assert set(volume["period_quarter"]) == {1, 2}

    top = dashboard_data["top_mcg"].sort_values("spend_rank").iloc[0]
    assert top.mcg_name == "Groceries and Supermarkets"
    assert top.net_spend_share_pct == pytest.approx(22.1646)

    contactless = dashboard_data["contactless"].sort_values(
        "contactless_net_spend_pct", ascending=False
    ).iloc[0]
    assert contactless.issuer_country == "México"
    assert contactless.contactless_net_spend_pct == pytest.approx(70.2698)


def test_streamlit_three_pages_render_without_exceptions() -> None:
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    assert len(app.sidebar.radio) == 1

    for page in ("Análisis Transaccional", "Campaña Mayo 2024", "Resumen Ejecutivo"):
        app.sidebar.radio[0].set_value(page)
        app.run()
        assert not app.exception
