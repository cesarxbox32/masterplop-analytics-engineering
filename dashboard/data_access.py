from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class DashboardDataError(RuntimeError):
    """Error controlado al cargar la capa agregada del dashboard."""


QUERIES = {
    "executive": "SELECT * FROM dashboard.executive_summary",
    "volume": """
        SELECT * FROM dashboard.volume_quarterly
        ORDER BY period_year, period_quarter, product_type
    """,
    "quarterly_ticket": """
        SELECT * FROM dashboard.credit_ticket_quarterly
        ORDER BY period_year, period_quarter
    """,
    "regional_ticket": """
        SELECT * FROM dashboard.credit_ticket_south_america
        ORDER BY issuer_country, product_name
    """,
    "top_mcg": "SELECT * FROM dashboard.top_10_mcg_spend ORDER BY spend_rank",
    "contactless": """
        SELECT * FROM dashboard.contactless_adoption
        ORDER BY contactless_net_spend_pct DESC NULLS LAST, issuer_country
    """,
    "cashback": "SELECT * FROM dashboard.cashback_summary",
    "cashback_sensitivity": "SELECT * FROM dashboard.cashback_sensitivity",
    "cashback_is_xb": "SELECT * FROM dashboard.cashback_is_xb_diagnostic",
    "cashback_diagnostic": """
        SELECT * FROM dashboard.cashback_eligibility_diagnostic
        ORDER BY diagnostic_status
    """,
    "quality": "SELECT * FROM dashboard.data_quality_summary",
}

AGGREGATE_FILES = {name: f"{name}.csv" for name in QUERIES}


def load_dashboard_data(
    database_path: Path,
    aggregate_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    database_path = database_path.resolve()
    aggregate_dir = (aggregate_dir or database_path.parent / "dashboard").resolve()

    if database_path.is_file():
        try:
            connection = duckdb.connect(str(database_path), read_only=True)
            try:
                datasets = {
                    name: connection.execute(query).fetch_df()
                    for name, query in QUERIES.items()
                }
            finally:
                connection.close()
        except (duckdb.Error, OSError) as error:
            raise DashboardDataError(
                "No fue posible leer las tablas agregadas desde DuckDB. "
                "Reconstruye la base con src/pipeline.py."
            ) from error
    else:
        missing = [
            file_name
            for file_name in AGGREGATE_FILES.values()
            if not (aggregate_dir / file_name).is_file()
        ]
        if missing:
            raise DashboardDataError(
                "No existe DuckDB ni una exportación agregada completa. "
                f"Faltan en {aggregate_dir}: {missing}. Ejecuta src/pipeline.py primero."
            )
        try:
            datasets = {
                name: pd.read_csv(aggregate_dir / file_name, encoding="utf-8-sig")
                for name, file_name in AGGREGATE_FILES.items()
            }
        except (OSError, pd.errors.ParserError) as error:
            raise DashboardDataError(
                "No fue posible leer los CSV agregados del dashboard."
            ) from error

    empty = [name for name, frame in datasets.items() if frame.empty]
    if empty:
        raise DashboardDataError(f"Las siguientes tablas agregadas están vacías: {empty}")

    exposed_ids = {
        name: [column for column in frame.columns if column.lower() == "card_id"]
        for name, frame in datasets.items()
    }
    exposed_ids = {name: columns for name, columns in exposed_ids.items() if columns}
    if exposed_ids:
        raise DashboardDataError(
            f"La capa pública contiene identificadores individuales: {exposed_ids}"
        )
    return datasets
