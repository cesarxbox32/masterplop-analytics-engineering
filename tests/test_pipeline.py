from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "masterplop.duckdb"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


@pytest.fixture(scope="module")
def connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.is_file():
        pytest.fail("Falta data/processed/masterplop.duckdb. Ejecuta src/pipeline.py primero.")
    db = duckdb.connect(str(DB_PATH), read_only=True)
    yield db
    db.close()


def test_all_documented_quality_checks_pass(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    failures = connection.execute(
        """
        SELECT check_name, actual_value, expected_value
        FROM audit.quality_checks
        WHERE status <> 'PASS'
        ORDER BY check_name
        """
    ).fetchall()
    assert failures == []


def test_card_id_is_text_and_amount_is_decimal(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    schema = dict(
        connection.execute(
            "SELECT column_name, data_type FROM duckdb_columns() WHERE schema_name = 'staging' AND table_name = 'transactions'"
        ).fetchall()
    )
    assert schema["card_id"] == "VARCHAR"
    assert schema["amt"] == "DECIMAL(18,2)"


def test_raw_and_normalized_fields_coexist(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    columns = {
        row[0]
        for row in connection.execute(
            "SELECT column_name FROM duckdb_columns() WHERE schema_name = 'analytics' AND table_name = 'transactions_enriched'"
        ).fetchall()
    }
    required = {
        "card_id_raw",
        "card_id",
        "product_type_raw",
        "product_type",
        "ctry_card_raw",
        "ctry_card",
        "ctry_mrch_raw",
        "ctry_mrch",
        "amt_raw",
        "amt",
        "mcg_code_original",
        "mcg_name",
    }
    assert required <= columns


def test_unclassified_mcg_preserves_code_and_rows(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    result = connection.execute(
        """
        SELECT mcg_name, mcg_code_original, count(*)
        FROM analytics.transactions_enriched
        WHERE NOT is_mcg_classified
        GROUP BY 1, 2
        """
    ).fetchall()
    assert result == [("Sin clasificar", "35", 12000)]


def test_country_normalization_variants(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    unexpected = connection.execute(
        """
        SELECT count(*)
        FROM staging.transactions
        WHERE ctry_card IN ('Brazil', 'Mexico', 'Peru', 'Panama', 'Republica Dominicana')
           OR ctry_mrch IN ('Brazil', 'Mexico', 'Peru', 'Panama', 'Republica Dominicana')
        """
    ).fetchone()[0]
    assert unexpected == 0


def test_public_quality_exports_have_no_card_level_fields() -> None:
    csv_path = ROOT / "data" / "processed" / "quality_summary.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream))
    assert header == [
        "check_name",
        "severity",
        "actual_value",
        "expected_value",
        "status",
        "details",
    ]


def test_source_hashes_match_current_originals(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    recorded = dict(
        connection.execute(
            "SELECT file_name, sha256 FROM audit.source_files"
        ).fetchall()
    )
    expected_files = {
        "db_transac.csv",
        "mcg_list.xlsx",
        "Diccionario.xlsx",
        "Instrucciones Desafío.pdf",
        "Masterplop logo.png",
    }
    assert set(recorded) == expected_files
    for file_name in expected_files:
        assert recorded[file_name] == file_sha256(ROOT / file_name)


def test_all_kpi_sql_checks_pass(connection: duckdb.DuckDBPyConnection) -> None:
    checks = connection.execute(
        """
        SELECT check_name, status, actual_value, expected_value
        FROM audit.kpi_checks
        ORDER BY check_name
        """
    ).fetchall()
    assert len(checks) == 17
    assert [row for row in checks if row[1] != "PASS"] == []


def test_volume_uses_distinct_cards_by_year_quarter_and_type(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    actual = {
        (year, quarter, product_type): active_cards
        for year, quarter, product_type, active_cards in connection.execute(
            """
            SELECT period_year, period_quarter, product_type, active_cards
            FROM analytics.kpi_volume_quarterly
            """
        ).fetchall()
    }
    assert actual == {
        (2024, 1, "Crédito"): 46747,
        (2024, 1, "Débito"): 8224,
        (2024, 2, "Crédito"): 51037,
        (2024, 2, "Débito"): 8960,
    }


def test_credit_ticket_is_net_spend_per_distinct_card(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    rows = connection.execute(
        """
        SELECT
            period_quarter,
            net_spend_usd,
            active_credit_cards,
            net_spend_per_active_card_usd
        FROM analytics.kpi_credit_ticket_quarterly
        WHERE period_year = 2024
        ORDER BY period_quarter
        """
    ).fetchall()
    assert rows == [
        (1, Decimal("150964927.10"), 46747, Decimal("3229.40")),
        (2, Decimal("256174004.20"), 51037, Decimal("5019.38")),
    ]
    for _, net_spend, cards, ticket in rows:
        assert ticket == (net_spend / cards).quantize(Decimal("0.01"))


def test_regional_ticket_is_transaction_average_by_issuer_market(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    reported = connection.execute(
        """
        SELECT transaction_count, net_spend_usd, avg_transaction_amount_usd
        FROM analytics.kpi_credit_ticket_south_america
        WHERE issuer_country = 'Chile' AND product_name = 'P2'
        """
    ).fetchone()
    recalculated = connection.execute(
        """
        SELECT count(*), sum(amt)::DECIMAL(38,2), cast(avg(amt) AS DECIMAL(18,2))
        FROM analytics.transactions_enriched
        WHERE product_type = 'Crédito'
          AND ctry_card = 'Chile'
          AND product_name = 'P2'
        """
    ).fetchone()
    assert reported == recalculated


def test_top_categories_use_global_net_spend_denominator(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    total = connection.execute(
        "SELECT sum(amt)::DECIMAL(38,2) FROM analytics.transactions_enriched"
    ).fetchone()[0]
    assert total == Decimal("430124709.40")
    top_three = connection.execute(
        """
        SELECT mcg_name, net_spend_share_pct
        FROM analytics.kpi_top_10_mcg_spend
        WHERE spend_rank <= 3
        ORDER BY spend_rank
        """
    ).fetchall()
    assert top_three == [
        ("Groceries and Supermarkets", Decimal("22.1646")),
        ("Restaurants and Dining", Decimal("17.1222")),
        ("Entertainment", Decimal("13.4029")),
    ]
    unclassified = connection.execute(
        """
        SELECT mcg_code_original, mcg_name, transaction_count
        FROM analytics.kpi_mcg_spend_all
        WHERE mcg_code = 35
        """
    ).fetchone()
    assert unclassified == ("35", "Sin clasificar", 12000)
    assert connection.execute(
        "SELECT sum(transaction_count) FROM analytics.kpi_mcg_spend_all"
    ).fetchone()[0] == 2400000


def test_contactless_share_reconciles_and_is_descending(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    rows = connection.execute(
        """
        SELECT issuer_country, contactless_net_spend_pct
        FROM analytics.kpi_contactless_adoption
        ORDER BY contactless_net_spend_pct DESC NULLS LAST, issuer_country
        """
    ).fetchall()
    percentages = [row[1] for row in rows if row[1] is not None]
    assert percentages == sorted(percentages, reverse=True)

    reported = connection.execute(
        """
        SELECT contactless_net_spend_usd, total_net_spend_usd, contactless_net_spend_pct
        FROM analytics.kpi_contactless_adoption
        WHERE issuer_country = 'Chile'
        """
    ).fetchone()
    numerator, denominator, percentage = reported
    assert percentage == (numerator * 100 / denominator).quantize(Decimal("0.0001"))


def test_kpi_measures_use_decimal_types(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    types = {
        (table_name, column_name): data_type
        for table_name, column_name, data_type in connection.execute(
            """
            SELECT table_name, column_name, data_type
            FROM duckdb_columns()
            WHERE schema_name = 'analytics'
              AND table_name LIKE 'kpi_%'
            """
        ).fetchall()
    }
    assert types[("kpi_credit_ticket_quarterly", "net_spend_usd")] == "DECIMAL(38,2)"
    assert types[("kpi_credit_ticket_quarterly", "net_spend_per_active_card_usd")] == "DECIMAL(18,2)"
    assert types[("kpi_top_10_mcg_spend", "net_spend_share_pct")] == "DECIMAL(9,4)"
    assert types[("kpi_contactless_adoption", "contactless_net_spend_pct")] == "DECIMAL(9,4)"


def test_dashboard_exports_are_aggregated_and_match_views(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    kpi_dir = ROOT / "data" / "processed" / "kpis"
    exports = {
        "volume_quarterly": "analytics.kpi_volume_quarterly",
        "credit_ticket_quarterly": "analytics.kpi_credit_ticket_quarterly",
        "credit_ticket_south_america": "analytics.kpi_credit_ticket_south_america",
        "top_10_mcg_spend": "analytics.kpi_top_10_mcg_spend",
        "contactless_adoption": "analytics.kpi_contactless_adoption",
    }
    for file_stem, view_name in exports.items():
        with (kpi_dir / f"{file_stem}.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.reader(stream)
            header = next(reader)
            exported_rows = list(reader)
        assert "card_id" not in header
        assert len(exported_rows) == connection.execute(
            f"SELECT count(*) FROM {view_name}"
        ).fetchone()[0]

    payload = json.loads((kpi_dir / "kpi_results.json").read_text(encoding="utf-8"))
    assert set(payload["datasets"]) == set(exports)
    assert all("card_id" not in dataset["columns"] for dataset in payload["datasets"].values())


def test_all_cashback_sql_checks_pass(connection: duckdb.DuckDBPyConnection) -> None:
    checks = connection.execute(
        """
        SELECT check_name, status, actual_value, expected_value
        FROM audit.cashback_checks
        ORDER BY check_name
        """
    ).fetchall()
    assert len(checks) == 11
    assert [row for row in checks if row[1] != "PASS"] == []


def test_cashback_official_summary_matches_independent_controls(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    summary = connection.execute(
        """
        SELECT
            eligible_transaction_count,
            positive_eligible_transaction_count,
            negative_eligible_transaction_count,
            beneficiary_card_count,
            capped_card_count,
            net_eligible_spend_usd,
            total_cashback_usd,
            cap_savings_usd
        FROM analytics.cashback_may_2024_summary
        """
    ).fetchone()
    assert summary == (
        28915,
        28885,
        30,
        4029,
        2676,
        Decimal("7319379.70"),
        Decimal("178471.62"),
        Decimal("333887.01"),
    )


def test_cashback_eligibility_uses_merchant_country_not_is_xb(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    violations = connection.execute(
        """
        SELECT count(*)
        FROM analytics.cashback_may_2024_eligible_transactions
        WHERE prch_date < DATE '2024-05-01'
           OR prch_date >= DATE '2024-06-01'
           OR product_type <> 'Crédito'
           OR ctry_card <> 'Chile'
           OR ctry_mrch = 'Chile'
        """
    ).fetchone()[0]
    assert violations == 0

    eligible_despite_flag = connection.execute(
        """
        SELECT count(*)
        FROM analytics.cashback_may_2024_eligible_transactions
        WHERE is_xb <> 1
        """
    ).fetchone()[0]
    assert eligible_despite_flag == 14521


def test_cashback_is_rounded_and_capped_per_card(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    invalid = connection.execute(
        """
        SELECT count(*)
        FROM analytics.cashback_may_2024_individual
        WHERE cashback_usd <> analytics.cashback_amount_usd(net_eligible_spend_usd)
           OR cashback_usd < 0
           OR cashback_usd > 50
        """
    ).fetchone()[0]
    assert invalid == 0
    individual_sum = connection.execute(
        "SELECT sum(cashback_usd)::DECIMAL(38,2) FROM analytics.cashback_may_2024_individual"
    ).fetchone()[0]
    assert individual_sum == Decimal("178471.62")


def test_cashback_sensitivity_and_is_xb_diagnostic(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    sensitivity = connection.execute(
        """
        SELECT positive_only_cashback_usd, incremental_cost_vs_net_usd
        FROM analytics.cashback_may_2024_sensitivity_summary
        """
    ).fetchone()
    assert sensitivity == (Decimal("178608.88"), Decimal("137.26"))

    incorrect = connection.execute(
        """
        SELECT incorrect_is_xb_cashback_usd, difference_vs_official_usd
        FROM analytics.cashback_may_2024_is_xb_summary
        """
    ).fetchone()
    assert incorrect == (Decimal("135160.88"), Decimal("-43310.74"))


def test_cashback_boundary_cases_pass(connection: duckdb.DuckDBPyConnection) -> None:
    results = connection.execute(
        """
        SELECT test_name, actual_cashback_usd, expected_cashback_usd, status
        FROM audit.cashback_boundary_tests
        ORDER BY test_name
        """
    ).fetchall()
    assert len(results) == 5
    assert all(actual == expected and status == "PASS" for _, actual, expected, status in results)


def test_cashback_monetary_types_are_decimal(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    types = {
        (table_name, column_name): data_type
        for table_name, column_name, data_type in connection.execute(
            """
            SELECT table_name, column_name, data_type
            FROM duckdb_columns()
            WHERE schema_name = 'analytics'
              AND table_name IN (
                  'cashback_may_2024_by_card',
                  'cashback_may_2024_individual',
                  'cashback_may_2024_summary'
              )
            """
        ).fetchall()
    }
    assert types[("cashback_may_2024_by_card", "net_eligible_spend_usd")] == "DECIMAL(38,2)"
    assert types[("cashback_may_2024_individual", "cashback_usd")] == "DECIMAL(18,2)"
    assert types[("cashback_may_2024_summary", "total_cashback_usd")] == "DECIMAL(38,2)"


def test_cashback_public_outputs_are_aggregated() -> None:
    output_path = ROOT / "data" / "processed" / "cashback_may_2024.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload["datasets"]) == {
        "official_summary",
        "positive_only_sensitivity",
        "incorrect_is_xb_summary",
        "eligibility_diagnostic",
        "boundary_tests",
    }
    for dataset in payload["datasets"].values():
        assert "card_id" not in dataset["columns"]
        assert all("card_id" not in record for record in dataset["records"])
