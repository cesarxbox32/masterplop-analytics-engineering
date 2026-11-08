from __future__ import annotations

import re
import subprocess
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
    assert "*.pbix" in entries
    assert "!powerbi/Masterplop_Executive.pbix" in entries
    assert "powerbi/**/.pbi/" in entries
    assert "powerbi/" not in entries


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
    assert "https://github.com/cesarxbox32/masterplop-analytics-engineering" in readme
    assert "https://cesarxbox32.github.io/masterplop-analytics-engineering/" in readme
    assert "powerbi/Masterplop_Executive.pbix" in readme
    assert "powerbi/Masterplop_Executive.pdf" in readme
    assert "powerbi/source/Masterplop_Executive.pbip" in readme
    assert "## Power BI Desktop" in readme


def test_public_static_dashboard_is_versioned() -> None:
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "MASTERPLOP" in page
    assert "data/processed/dashboard/manifest.json" in page
    assert "plotly" in page.lower()
    assert "card_id" not in page.lower()
    assert "@media(max-width:700px)" in page
    assert 'aria-selected="true"' in page
    assert 'role="tablist"' in page
    assert 'role="tabpanel"' in page
    assert "prefers-reduced-motion" in page
    assert "ResizeObserver" in page
    assert "IntersectionObserver" in page
    assert 'class="scroll-progress"' in page
    assert 'class="status-pill"' in page
    assert 'class="panel loading-shell"' in page
    assert "setupHeroSpotlight" in page
    assert "@keyframes orbDrift" in page
    assert "motion-ready" in page
    assert "data-details" in page
    assert "campaignWaterfall" in page
    assert "campaignMatrix" in page
    assert 'src="Masterplop%20logo.png"' in page
    assert "raw.githubusercontent.com" not in page
    assert "Código y metodología" in page

    workflow = ROOT / ".github" / "workflows" / "pages.yml"
    assert workflow.is_file()
    assert 'href="powerbi/Masterplop_Executive.pdf"' in page
    assert 'href="powerbi/Masterplop_Executive.pbix"' in page


def test_powerbi_public_package_is_complete_and_portable() -> None:
    powerbi = ROOT / "powerbi"
    source = powerbi / "source"
    report = source / "Masterplop_Executive.Report"
    model = source / "Masterplop_Executive.SemanticModel"

    assert (powerbi / "Masterplop_Executive.pbix").read_bytes()[:2] == b"PK"
    assert (powerbi / "Masterplop_Executive.pdf").read_bytes()[:4] == b"%PDF"
    previews = sorted((ROOT / "docs" / "assets" / "powerbi").glob("*.png"))
    assert len(previews) == 3
    assert all(path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for path in previews)

    pages = [path for path in (report / "definition" / "pages").iterdir() if path.is_dir()]
    visuals = list((report / "definition" / "pages").rglob("visual.json"))
    tables = list((model / "definition" / "tables").glob("*.tmdl"))
    csv_files = list((source / "data").glob("*.csv"))
    executive_tmdl = (model / "definition" / "tables" / "executive.tmdl").read_text(
        encoding="utf-8-sig"
    )

    assert len(pages) == 3
    assert len(visuals) == 49
    assert len(tables) == 15
    assert len(csv_files) == 15
    assert len(re.findall(r"^\s*measure ", executive_tmdl, flags=re.MULTILINE)) == 39

    restricted = (
        "card_id",
        "db_transac.csv",
        "c:\\users",
        "file.contents",
        "password",
        "secret",
        "token",
    )
    text_extensions = {".json", ".pbir", ".pbip", ".tmdl", ".csv", ".txt"}
    for path in source.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_extensions:
            content = path.read_text(encoding="utf-8-sig").lower()
            assert not any(term in content for term in restricted), path

    for path in csv_files:
        header = path.read_text(encoding="utf-8-sig").splitlines()[0].lower()
        assert "card_id" not in header


def test_powerbi_git_publication_policy() -> None:
    def is_ignored(relative_path: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--quiet", "--no-index", "--", relative_path],
            check=False,
        )
        return result.returncode == 0

    public_paths = (
        "powerbi/Masterplop_Executive.pbix",
        "powerbi/Masterplop_Executive.pdf",
        "powerbi/source/Masterplop_Executive.pbip",
        "docs/assets/powerbi/01-resumen-ejecutivo.png",
    )
    assert all(not is_ignored(path) for path in public_paths)

    private_paths = (
        "powerbi/Masterplop_Executive.pbip",
        "powerbi/data/executive.csv",
        "powerbi/Masterplop_Executive.SemanticModel/.pbi/cache.abf",
    )
    assert all(is_ignored(path) for path in private_paths)

