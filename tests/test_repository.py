from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_excludes_sensitive_and_heavy_artifacts() -> None:
    entries = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "db_transac.csv" in entries
    assert "**/*.duckdb" in entries
    assert ".streamlit/secrets.toml" in entries
    assert ".env" in entries


def test_sql_execution_order_is_unambiguous() -> None:
    sql_files = {path.name for path in (ROOT / "sql").glob("*.sql")}
    assert "40_dashboard_aggregates.sql" in sql_files
    assert "29_dashboard_aggregates.sql" not in sql_files

    pipeline = (ROOT / "src" / "pipeline.py").read_text(encoding="utf-8")
    assert 'execute_sql_file(connection, "40_dashboard_aggregates.sql")' in pipeline


def test_readme_contains_delivery_governance_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required_sections = (
        "## Contexto y objetivo de negocio",
        "## Diccionario breve del modelo final",
        "## Matriz de controles verificados",
        "## Riesgos, limitaciones y recomendaciones",
        "## AI Log",
        "## Enlace al dashboard",
    )
    for section in required_sections:
        assert section in readme
    assert "Pendiente de publicación tras la revisión final" in readme

