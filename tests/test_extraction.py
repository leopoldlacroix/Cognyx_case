"""
Tests for source entity extraction (Plan 02-03 Task 2.3.4).
"""
from datetime import datetime, timezone

import pytest


def _insert_source_file(conn, system: str = "PLM", name: str = "test.csv") -> int:
    cur = conn.execute(
        "INSERT INTO source_file (source_system, file_name, file_hash, ingested_at) "
        "VALUES (?, ?, ?, ?)",
        (system, name, f"hash-{system}-{name}", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def test_extract_source_components_from_plm_bom(conn):
    from app.services.extraction import extract_source_components

    sf = _insert_source_file(conn, "PLM", "bom_export.csv")
    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, description_raw, quantity_raw, uom_raw, supplier_raw, "
        "variant_ref_normalized, assembly_ref_normalized, component_ref_normalized, "
        "description_normalized, quantity_normalized, uom_normalized, supplier_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 2, "VAR-A", "ASM-1", "CTRL-AIR-01", "HVAC Control", "1", "EA", "Siemens",
            "VAR-A", "ASM-1", "CTRL-AIR-01", "HVAC Control", 1.0, "EA", "SIEMENS",
        ),
    )
    conn.commit()

    counts = extract_source_components(conn)
    assert counts["PLM"] == 1
    assert counts["ERP"] == 0

    row = conn.execute(
        "SELECT * FROM source_component WHERE source_system = 'PLM'"
    ).fetchone()
    assert row["source_reference"] == "CTRL-AIR-01"
    assert row["normalized_reference"] == "CTRL-AIR-01"
    assert row["description"] == "HVAC Control"
    assert row["source_record_type"] == "BOM_LINE"
    assert row["source_record_id"] == 1


def test_extract_source_components_from_erp_material(conn):
    from app.services.extraction import extract_source_components

    sf = _insert_source_file(conn, "ERP", "material_master.csv")
    conn.execute(
        "INSERT INTO erp_material ("
        "source_file_id, source_row, material_id_raw, description_raw, "
        "material_type_raw, base_unit_raw, supplier_id_raw, category_raw, "
        "status_raw, cost_raw, material_id_normalized, description_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 2, "MAT-10001", "HVAC Control Unit", "COMPONENT", "EA", "SUP-001",
            "HVAC", "ACTIVE", 1850.0, "MAT-10001", "HVAC Control Unit",
        ),
    )
    conn.commit()

    counts = extract_source_components(conn)
    assert counts["ERP"] == 1
    assert counts["PLM"] == 0

    row = conn.execute(
        "SELECT * FROM source_component WHERE source_system = 'ERP'"
    ).fetchone()
    assert row["source_reference"] == "MAT-10001"
    assert row["normalized_reference"] == "MAT-10001"
    assert row["source_record_type"] == "MATERIAL_MASTER"


def test_extract_source_components_deduplicates(conn):
    from app.services.extraction import extract_source_components

    sf = _insert_source_file(conn, "PLM", "bom_export.csv")
    for source_row, variant in ((2, "VAR-A"), (3, "VAR-B")):
        conn.execute(
            "INSERT INTO plm_bom_line ("
            "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
            "component_ref_raw, component_ref_normalized, description_normalized"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sf, source_row, variant, "ASM-1", "CTRL-AIR-01", "CTRL-AIR-01", "HVAC"),
        )
    conn.commit()

    counts = extract_source_components(conn)
    assert counts["PLM"] == 1
    total = conn.execute("SELECT COUNT(*) AS c FROM source_component").fetchone()["c"]
    assert total == 1


def test_extract_source_assemblies_creates_junction_records(conn):
    from app.services.extraction import extract_source_assemblies

    sf = _insert_source_file(conn, "PLM", "assembly_master.csv")
    conn.execute(
        "INSERT INTO plm_assembly ("
        "source_file_id, source_row, assembly_ref_raw, assembly_description_raw, "
        "variant_ref_raw, revision_raw, lifecycle_raw, "
        "assembly_ref_normalized, assembly_description_normalized, variant_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 2, "ASM-HVAC-01", "HVAC Assembly", "VAR-NORDIC", "A", "RELEASED",
            "ASM-HVAC-01", "HVAC Assembly", "VAR-NORDIC",
        ),
    )
    conn.execute(
        "INSERT INTO plm_assembly ("
        "source_file_id, source_row, assembly_ref_raw, assembly_description_raw, "
        "variant_ref_raw, revision_raw, lifecycle_raw, "
        "assembly_ref_normalized, assembly_description_normalized, variant_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sf, 3, "ASM-HVAC-01", "HVAC Assembly", "VAR-STD", "A", "RELEASED",
            "ASM-HVAC-01", "HVAC Assembly", "VAR-STD",
        ),
    )
    conn.commit()

    counts = extract_source_assemblies(conn)
    assert counts["PLM"] == 1  # same assembly_ref_raw → one source_assembly
    assert counts["variants"] == 2

    asm = conn.execute("SELECT * FROM source_assembly").fetchone()
    assert asm["source_reference"] == "ASM-HVAC-01"
    assert asm["source_record_type"] == "ASSEMBLY_MASTER"
    # Flat table — no variant column
    assert "variant_ref" not in asm.keys()

    variants = {
        r["variant_ref_normalized"]
        for r in conn.execute(
            "SELECT variant_ref_normalized FROM source_assembly_variant "
            "WHERE source_assembly_id = ?",
            (asm["id"],),
        ).fetchall()
    }
    assert variants == {"VAR-NORDIC", "VAR-STD"}


def test_extract_source_suppliers_from_both_sources(conn):
    from app.services.extraction import extract_source_suppliers

    plm_sf = _insert_source_file(conn, "PLM", "bom_export.csv")
    erp_sf = _insert_source_file(conn, "ERP", "supplier_master.csv")

    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, supplier_raw, supplier_normalized, "
        "component_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (plm_sf, 2, "V1", "A1", "C1", "Siemens", "SIEMENS", "C1"),
    )
    conn.execute(
        "INSERT INTO erp_supplier ("
        "source_file_id, source_row, supplier_id_raw, supplier_name_raw, "
        "country_raw, supplier_id_normalized, supplier_name_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            erp_sf, 2, "SUP-001", "Siemens Mobility GmbH", "DE",
            "SUP-001", "SIEMENS MOBILITY",
        ),
    )
    conn.commit()

    counts = extract_source_suppliers(conn)
    assert counts["PLM"] == 1
    assert counts["ERP"] == 1

    plm = conn.execute(
        "SELECT * FROM source_supplier WHERE source_system = 'PLM'"
    ).fetchone()
    erp = conn.execute(
        "SELECT * FROM source_supplier WHERE source_system = 'ERP'"
    ).fetchone()
    assert plm["source_reference"] == "Siemens"
    assert plm["normalized_reference"] == "SIEMENS"
    assert plm["source_record_type"] == "BOM_LINE"
    assert erp["source_reference"] == "SUP-001"
    assert erp["normalized_reference"] == "SIEMENS MOBILITY"
    assert erp["source_record_type"] == "SUPPLIER_MASTER"


def test_source_extraction_is_idempotent(conn):
    from app.services.extraction import run_source_extraction

    plm_sf = _insert_source_file(conn, "PLM", "plm.csv")
    erp_sf = _insert_source_file(conn, "ERP", "erp.csv")

    conn.execute(
        "INSERT INTO plm_bom_line ("
        "source_file_id, source_row, variant_ref_raw, assembly_ref_raw, "
        "component_ref_raw, component_ref_normalized, supplier_raw, supplier_normalized"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (plm_sf, 2, "V1", "A1", "CTRL-1", "CTRL-1", "Acme", "ACME"),
    )
    conn.execute(
        "INSERT INTO plm_assembly ("
        "source_file_id, source_row, assembly_ref_raw, "
        "assembly_ref_normalized, variant_ref_normalized"
        ") VALUES (?, ?, ?, ?, ?)",
        (plm_sf, 2, "ASM-1", "ASM-1", "V1"),
    )
    conn.execute(
        "INSERT INTO erp_material ("
        "source_file_id, source_row, material_id_raw, material_id_normalized"
        ") VALUES (?, ?, ?, ?)",
        (erp_sf, 2, "MAT-1", "MAT-1"),
    )
    conn.execute(
        "INSERT INTO erp_supplier ("
        "source_file_id, source_row, supplier_id_raw, supplier_id_normalized, "
        "supplier_name_normalized"
        ") VALUES (?, ?, ?, ?, ?)",
        (erp_sf, 2, "SUP-1", "SUP-1", "ACME"),
    )
    conn.commit()

    first = run_source_extraction(conn)
    second = run_source_extraction(conn)

    assert first["components"]["PLM"] == 1
    assert first["components"]["ERP"] == 1
    assert first["assemblies"]["PLM"] == 1
    assert first["assemblies"]["variants"] == 1
    assert first["suppliers"]["PLM"] == 1
    assert first["suppliers"]["ERP"] == 1

    # Second run inserts nothing
    assert second["components"]["PLM"] == 0
    assert second["components"]["ERP"] == 0
    assert second["assemblies"]["PLM"] == 0
    assert second["assemblies"]["variants"] == 0
    assert second["suppliers"]["PLM"] == 0
    assert second["suppliers"]["ERP"] == 0

    assert conn.execute("SELECT COUNT(*) AS c FROM source_component").fetchone()["c"] == 2
    assert conn.execute("SELECT COUNT(*) AS c FROM source_assembly").fetchone()["c"] == 1
    assert conn.execute(
        "SELECT COUNT(*) AS c FROM source_assembly_variant"
    ).fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) AS c FROM source_supplier").fetchone()["c"] == 2
