from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"
EXPECTED_TRANSACTION_COLUMNS = [
    "card_id",
    "product_name",
    "product_type",
    "amt",
    "is_xb",
    "is_contactless",
    "prch_date",
    "prch_time",
    "ctry_card",
    "ctry_mrch",
    "mrch",
    "mcg_id",
]
KPI_EXPORTS = {
    "volume_quarterly": """
        SELECT * FROM analytics.kpi_volume_quarterly
        ORDER BY period_year, period_quarter, product_type
    """,
    "credit_ticket_quarterly": """
        SELECT * FROM analytics.kpi_credit_ticket_quarterly
        ORDER BY period_year, period_quarter
    """,
    "credit_ticket_south_america": """
        SELECT * FROM analytics.kpi_credit_ticket_south_america
        ORDER BY issuer_country, product_name
    """,
    "top_10_mcg_spend": """
        SELECT * FROM analytics.kpi_top_10_mcg_spend
        ORDER BY spend_rank
    """,
    "contactless_adoption": """
        SELECT * FROM analytics.kpi_contactless_adoption
        ORDER BY contactless_net_spend_pct DESC NULLS LAST, issuer_country
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construye la base analítica y los controles de calidad de Masterplop."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio de salida (por defecto: data/processed).",
    )
    return parser.parse_args()


def sql_literal(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def execute_sql_file(
    connection: duckdb.DuckDBPyConnection,
    file_name: str,
    replacements: dict[str, str] | None = None,
) -> None:
    sql = (SQL_DIR / file_name).read_text(encoding="utf-8")
    for key, value in (replacements or {}).items():
        sql = sql.replace(key, value)
    connection.execute(sql)


def validate_csv_header(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream))
    if header != EXPECTED_TRANSACTION_COLUMNS:
        raise ValueError(
            "El encabezado de db_transac.csv no coincide con las 12 columnas esperadas. "
            f"Recibido: {header}"
        )


def load_mcg(connection: duckdb.DuckDBPyConnection, workbook_path: Path) -> None:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows or tuple(rows[0]) != ("mcg", "mcg_name"):
        raise ValueError("mcg_list.xlsx debe comenzar con las columnas mcg y mcg_name.")

    connection.execute(
        """
        CREATE TABLE raw.mcg (
            source_row_number BIGINT NOT NULL,
            mcg_raw VARCHAR,
            mcg_name_raw VARCHAR
        )
        """
    )
    values = [
        (index, None if mcg is None else str(mcg), None if name is None else str(name))
        for index, (mcg, name) in enumerate(rows[1:], start=2)
        if mcg is not None or name is not None
    ]
    connection.executemany("INSERT INTO raw.mcg VALUES (?, ?, ?)", values)
    workbook.close()


def insert_source_metadata(
    connection: duckdb.DuckDBPyConnection, source_paths: list[Path]
) -> None:
    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = []
    for path in source_paths:
        stat = path.stat()
        modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(tzinfo=None)
        rows.append(
            (path.name, sha256(path), stat.st_size, modified_at, ingested_at)
        )
    connection.executemany(
        "INSERT INTO audit.source_files VALUES (?, ?, ?, ?, ?)", rows
    )


def fetch_quality_checks(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[list[str], list[tuple[object, ...]]]:
    result = connection.execute(
        """
        SELECT check_name, severity, actual_value, expected_value, status, details
        FROM audit.quality_checks
        ORDER BY
            CASE status WHEN 'FAIL' THEN 0 ELSE 1 END,
            check_name
        """
    )
    return [column[0] for column in result.description], result.fetchall()


def fetch_kpi_checks(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[list[str], list[tuple[object, ...]]]:
    result = connection.execute(
        """
        SELECT check_name, severity, actual_value, expected_value, status, details
        FROM audit.kpi_checks
        ORDER BY
            CASE status WHEN 'FAIL' THEN 0 ELSE 1 END,
            check_name
        """
    )
    return [column[0] for column in result.description], result.fetchall()


def fetch_cashback_checks(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[list[str], list[tuple[object, ...]]]:
    result = connection.execute(
        """
        SELECT check_name, severity, actual_value, expected_value, status, details
        FROM audit.cashback_checks
        ORDER BY
            CASE status WHEN 'FAIL' THEN 0 ELSE 1 END,
            check_name
        """
    )
    return [column[0] for column in result.description], result.fetchall()


def fetch_kpi_results(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, tuple[list[str], list[tuple[object, ...]]]]:
    datasets = {}
    for dataset_name, query in KPI_EXPORTS.items():
        result = connection.execute(query)
        headers = [column[0] for column in result.description]
        datasets[dataset_name] = (headers, result.fetchall())
    return datasets


def fetch_cashback_results(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, tuple[list[str], list[tuple[object, ...]]]]:
    queries = {
        "official_summary": "SELECT * FROM analytics.cashback_may_2024_summary",
        "positive_only_sensitivity": (
            "SELECT * FROM analytics.cashback_may_2024_sensitivity_summary"
        ),
        "incorrect_is_xb_summary": (
            "SELECT * FROM analytics.cashback_may_2024_is_xb_summary"
        ),
        "eligibility_diagnostic": """
            SELECT *
            FROM analytics.cashback_may_2024_eligibility_diagnostic
            ORDER BY diagnostic_status
        """,
        "boundary_tests": """
            SELECT test_name, net_spend_usd, actual_cashback_usd,
                   expected_cashback_usd, status
            FROM audit.cashback_boundary_tests
            ORDER BY test_name
        """,
    }
    datasets = {}
    for dataset_name, query in queries.items():
        result = connection.execute(query)
        headers = [column[0] for column in result.description]
        datasets[dataset_name] = (headers, result.fetchall())
    return datasets


def json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_quality_outputs(
    output_dir: Path,
    headers: list[str],
    rows: list[tuple[object, ...]],
    source_metadata: list[tuple[object, ...]],
) -> None:
    csv_path = output_dir / "quality_summary.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)

    checks = [dict(zip(headers, row, strict=True)) for row in rows]
    json_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "source_files": [
            {
                "file_name": row[0],
                "sha256": row[1],
                "size_bytes": row[2],
            }
            for row in source_metadata
        ],
    }
    (output_dir / "quality_summary.json").write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Resumen de calidad de datos",
        "",
        "Este archivo se genera con `src/pipeline.py`. Contiene solo resultados agregados; no publica identificadores de tarjeta.",
        "",
        "| Control | Severidad | Actual | Esperado | Estado | Detalle |",
        "|---|---:|---:|---:|:---:|---|",
    ]
    for row in rows:
        escaped = [str(value).replace("|", "\\|") for value in row]
        lines.append(
            f"| {escaped[0]} | {escaped[1]} | {escaped[2]} | {escaped[3]} | {escaped[4]} | {escaped[5]} |"
        )
    lines.extend(
        [
            "",
            "## Reglas aplicadas",
            "",
            "- El CSV se ingiere inicialmente como texto UTF-8 y se tipa de forma explícita en `staging.transactions`.",
            "- `card_id` permanece como `VARCHAR`.",
            "- Los tipos Credit/Credito/Crédito y Debit/Debito/Débito se normalizan a Crédito y Débito.",
            "- Se unifican las variantes indicadas de Brasil, México, Perú, Panamá y República Dominicana.",
            "- Las fechas aceptan DD/MM/YYYY y DD-MM-YYYY. Las horas aceptan HH:MM:SS y HH.MM.SS.",
            "- `amt` se convierte a `DECIMAL(18,2)` y se conservan los montos negativos.",
            "- El maestro MCG se une con `LEFT JOIN`; las claves no encontradas quedan como `Sin clasificar` y conservan su código original.",
            "- `is_xb` original se conserva. Su comparación con países normalizados es únicamente un control de calidad y no una regla de cashback.",
        ]
    )
    (output_dir / "quality_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_kpi_outputs(
    output_dir: Path,
    datasets: dict[str, tuple[list[str], list[tuple[object, ...]]]],
) -> None:
    kpi_dir = output_dir / "kpis"
    kpi_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "grain": "Aggregated outputs only; no individual card identifiers.",
        "datasets": {},
    }

    for dataset_name, (headers, rows) in datasets.items():
        with (kpi_dir / f"{dataset_name}.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerows(rows)

        manifest["datasets"][dataset_name] = {
            "row_count": len(rows),
            "columns": headers,
            "records": [
                {
                    header: json_safe(value)
                    for header, value in zip(headers, row, strict=True)
                }
                for row in rows
            ],
        }

    (kpi_dir / "kpi_results.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_kpi_validation_outputs(
    output_dir: Path,
    headers: list[str],
    rows: list[tuple[object, ...]],
) -> None:
    with (output_dir / "kpi_validation.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": [dict(zip(headers, row, strict=True)) for row in rows],
    }
    (output_dir / "kpi_validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Validación de indicadores",
        "",
        "Los valores esperados se usan únicamente como pruebas; no forman parte de las fórmulas de los KPIs.",
        "",
        "| Control | Actual | Esperado | Estado | Detalle |",
        "|---|---:|---:|:---:|---|",
    ]
    for row in rows:
        escaped = [str(value).replace("|", "\\|") for value in row]
        lines.append(
            f"| {escaped[0]} | {escaped[2]} | {escaped[3]} | {escaped[4]} | {escaped[5]} |"
        )
    (output_dir / "kpi_validation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_cashback_outputs(
    output_dir: Path,
    datasets: dict[str, tuple[list[str], list[tuple[object, ...]]]],
    check_headers: list[str],
    check_rows: list[tuple[object, ...]],
) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "privacy": "Aggregated results only; no card_id values are exported.",
        "datasets": {},
        "checks": [dict(zip(check_headers, row, strict=True)) for row in check_rows],
    }
    for dataset_name, (headers, rows) in datasets.items():
        payload["datasets"][dataset_name] = {
            "columns": headers,
            "row_count": len(rows),
            "records": [
                {
                    header: json_safe(value)
                    for header, value in zip(headers, row, strict=True)
                }
                for row in rows
            ],
        }
    (output_dir / "cashback_may_2024.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    official = dict(
        zip(
            datasets["official_summary"][0],
            datasets["official_summary"][1][0],
            strict=True,
        )
    )
    sensitivity = dict(
        zip(
            datasets["positive_only_sensitivity"][0],
            datasets["positive_only_sensitivity"][1][0],
            strict=True,
        )
    )
    incorrect = dict(
        zip(
            datasets["incorrect_is_xb_summary"][0],
            datasets["incorrect_is_xb_summary"][1][0],
            strict=True,
        )
    )
    lines = [
        "# Cashback Masterplop — mayo 2024",
        "",
        "Este reporte contiene solo resultados agregados. Los cálculos individuales permanecen dentro de DuckDB.",
        "",
        "## Resultado oficial",
        "",
        f"- Transacciones elegibles: {official['eligible_transaction_count']}",
        f"- Transacciones positivas: {official['positive_eligible_transaction_count']}",
        f"- Transacciones negativas: {official['negative_eligible_transaction_count']}",
        f"- Tarjetas beneficiadas: {official['beneficiary_card_count']}",
        f"- Tarjetas topadas: {official['capped_card_count']}",
        f"- Gasto neto elegible (USD): {official['net_eligible_spend_usd']}",
        f"- Cashback sin tope, redondeado por tarjeta (USD): {official['uncapped_cashback_rounded_usd']}",
        f"- Ahorro por tope (USD): {official['cap_savings_usd']}",
        f"- Costo total oficial (USD): {official['total_cashback_usd']}",
        "",
        "## Sensibilidades",
        "",
        f"- Sin descontar devoluciones (USD): {sensitivity['positive_only_cashback_usd']}",
        f"- Incremento frente al escenario neto (USD): {sensitivity['incremental_cost_vs_net_usd']}",
        f"- Uso incorrecto de is_xb (USD): {incorrect['incorrect_is_xb_cashback_usd']}",
        f"- Diferencia is_xb frente al oficial (USD): {incorrect['difference_vs_official_usd']}",
        "",
        "## Controles",
        "",
        "| Control | Actual | Esperado | Estado |",
        "|---|---:|---:|:---:|",
    ]
    for row in check_rows:
        escaped = [str(value).replace("|", "\\|") for value in row]
        lines.append(f"| {escaped[0]} | {escaped[2]} | {escaped[3]} | {escaped[4]} |")
    (output_dir / "cashback_may_2024.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def build(output_dir: Path) -> Path:
    source_paths = [
        ROOT / "db_transac.csv",
        ROOT / "mcg_list.xlsx",
        ROOT / "Diccionario.xlsx",
        ROOT / "Instrucciones Desafío.pdf",
        ROOT / "Masterplop logo.png",
    ]
    missing = [str(path) for path in source_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Faltan archivos fuente: {missing}")

    csv_path = ROOT / "db_transac.csv"
    validate_csv_header(csv_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    final_db = output_dir / "masterplop.duckdb"
    building_db = output_dir / "masterplop.building.duckdb"
    if building_db.exists():
        building_db.unlink()

    connection = duckdb.connect(str(building_db))
    try:
        execute_sql_file(connection, "00_schemas.sql")
        execute_sql_file(
            connection,
            "01_ingest_transactions.sql",
            {"{{DB_TRANSAC_PATH}}": sql_literal(csv_path)},
        )
        load_mcg(connection, ROOT / "mcg_list.xlsx")
        insert_source_metadata(connection, source_paths)
        execute_sql_file(connection, "10_staging.sql")
        execute_sql_file(connection, "20_analytics.sql")
        execute_sql_file(connection, "25_kpis.sql")
        execute_sql_file(connection, "27_cashback.sql")
        execute_sql_file(connection, "30_quality_checks.sql")
        execute_sql_file(connection, "35_kpi_checks.sql")
        execute_sql_file(connection, "37_cashback_checks.sql")
        execute_sql_file(connection, "40_dashboard_aggregates.sql")

        headers, rows = fetch_quality_checks(connection)
        kpi_check_headers, kpi_check_rows = fetch_kpi_checks(connection)
        cashback_check_headers, cashback_check_rows = fetch_cashback_checks(connection)

        expected_check_counts = {"data": 20, "kpi": 17, "cashback": 11}
        observed_check_counts = {
            "data": len(rows),
            "kpi": len(kpi_check_rows),
            "cashback": len(cashback_check_rows),
        }
        if observed_check_counts != expected_check_counts:
            raise RuntimeError(
                "Cobertura de controles incompleta. "
                f"Esperado={expected_check_counts}; observado={observed_check_counts}."
            )

        failed = [row for row in rows if row[4] != "PASS"]
        failed_kpis = [row for row in kpi_check_rows if row[4] != "PASS"]
        failed_cashback = [row for row in cashback_check_rows if row[4] != "PASS"]
        all_failures = failed + failed_kpis + failed_cashback
        if all_failures:
            failed_names = ", ".join(row[0] for row in all_failures)
            raise RuntimeError(
                "La base generada no reemplazará la última versión válida porque "
                f"fallaron estos controles: {failed_names}."
            )

        kpi_datasets = fetch_kpi_results(connection)
        cashback_datasets = fetch_cashback_results(connection)
        source_metadata = connection.execute(
            "SELECT file_name, sha256, size_bytes FROM audit.source_files ORDER BY file_name"
        ).fetchall()
        connection.execute("CHECKPOINT")
    finally:
        connection.close()

    os.replace(building_db, final_db)
    write_quality_outputs(output_dir, headers, rows, source_metadata)
    write_kpi_outputs(output_dir, kpi_datasets)
    write_kpi_validation_outputs(output_dir, kpi_check_headers, kpi_check_rows)
    write_cashback_outputs(
        output_dir,
        cashback_datasets,
        cashback_check_headers,
        cashback_check_rows,
    )

    print(f"Base creada: {final_db}")
    print(f"Controles ejecutados: {len(rows)}; PASS: {len(rows) - len(failed)}; FAIL: {len(failed)}")
    for row in failed:
        print(
            f"FAIL {row[0]}: actual={row[2]}, esperado={row[3]} ({row[5]})"
        )
    print(
        f"Controles KPI ejecutados: {len(kpi_check_rows)}; "
        f"PASS: {len(kpi_check_rows) - len(failed_kpis)}; FAIL: {len(failed_kpis)}"
    )
    for row in failed_kpis:
        print(
            f"FAIL KPI {row[0]}: actual={row[2]}, esperado={row[3]} ({row[5]})"
        )
    print(
        f"Controles cashback ejecutados: {len(cashback_check_rows)}; "
        f"PASS: {len(cashback_check_rows) - len(failed_cashback)}; "
        f"FAIL: {len(failed_cashback)}"
    )
    for row in failed_cashback:
        print(
            f"FAIL CASHBACK {row[0]}: actual={row[2]}, esperado={row[3]} ({row[5]})"
        )
    return final_db


if __name__ == "__main__":
    arguments = parse_args()
    build(arguments.output_dir)
