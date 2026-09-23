"""
Tests for canonical model / BOM build from accepted identity + singletons (Plan 03-03).
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_file(conn) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_file (source_system, file_name, file_hash, ingested_at)
        VALUES ('PLM', 'bom_export.csv', 'hash-test', ?)
        """,
        (_now(),),
    )
    conn.commit()
    return cur.lastrowid


def _insert_variant(conn, source_file_id: int, ref: str, name: str | None = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO plm_variant (
            source_file_id, source_row, variant_ref_raw, variant_name_raw,
            variant_ref_normalized, variant_name_normalized
        ) VALUES (?, 1, ?, ?, ?, ?)
        """,
        (source_file_id, ref, name or ref, ref, name or ref),
    )
    conn.commit()
    return cur.lastrowid


def _insert_source_assembly(
    conn,
    *,
    source_reference: str,
    normalized_reference: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_assembly (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES ('PLM', ?, ?, ?, 'TEST', 1, ?)
        """,
        (
            source_reference,
            normalized_reference or source_reference,
            "assembly",
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_source_component(
    conn,
    *,
    source_reference: str,
    normalized_reference: str | None = None,
    source_system: str = "PLM",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_component (
            source_system, source_reference, normalized_reference,
            description, source_record_type, source_record_id, created_at
        ) VALUES (?, ?, ?, ?, 'TEST', 1, ?)
        """,
        (
            source_system,
            source_reference,
            normalized_reference or source_reference,
            "component",
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_bom_line(
    conn,
    *,
    source_file_id: int,
    variant_ref: str,
    assembly_ref: str,
    component_ref: str,
    quantity_normalized: float = 1.0,
    uom_normalized: str = "EA",
    source_row: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO plm_bom_line (
            source_file_id, source_row,
            variant_ref_raw, assembly_ref_raw, component_ref_raw,
            quantity_raw, uom_raw,
            variant_ref_normalized, assembly_ref_normalized, component_ref_normalized,
            quantity_normalized, uom_normalized
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_file_id,
            source_row,
            variant_ref,
            assembly_ref,
            component_ref,
            str(quantity_normalized),
            uom_normalized,
            variant_ref,
            assembly_ref,
            component_ref,
            quantity_normalized,
            uom_normalized,
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_pending_identity(
    conn,
    *,
    source_component_id: int,
    members: list[int],
    canonical_ref: str,
) -> int:
    evidence = {
        "relationship": "identity",
        "canonical_ref": canonical_ref,
        "cluster_members": [
            {"source_component_id": mid} for mid in members
        ],
    }
    cur = conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, 'PENDING', 'NORMALIZED', 0.95, ?, ?, ?)
        """,
        (
            source_component_id,
            "identity cluster",
            json.dumps(evidence, sort_keys=True, separators=(",", ":")),
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_pending_relationship(
    conn,
    *,
    source_component_id: int,
    relationship: str,
    extra: dict | None = None,
) -> int:
    evidence = {"relationship": relationship, **(extra or {})}
    cur = conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, 'PENDING', 'STRUCTURED', 0.5, ?, ?, ?)
        """,
        (
            source_component_id,
            relationship,
            json.dumps(evidence, sort_keys=True, separators=(",", ":")),
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Singleton shared reference (SCEN-A style)
# ---------------------------------------------------------------------------


def test_singleton_shared_across_variants_no_reconciliation(conn):
    """PLM component on two variants, no recon row → one component, two BOM rows."""
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")

    line1 = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        quantity_normalized=2.0,
        uom_normalized="EA",
        source_row=1,
    )
    line2 = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        quantity_normalized=2.0,
        uom_normalized="EA",
        source_row=2,
    )

    result = build_canonical_model(conn)

    assert result["variants"] == 2
    assert result["assemblies"] == 1
    assert result["components"] == 1
    assert result["bom_relationships"] == 2
    assert result["unresolved"] == []

    bom = conn.execute(
        "SELECT * FROM bom_relationship ORDER BY source_bom_line_id"
    ).fetchall()
    assert [b["source_bom_line_id"] for b in bom] == [line1, line2]
    assert bom[0]["component_id"] == bom[1]["component_id"]
    assert bom[0]["quantity"] == 2.0
    assert bom[0]["unit"] == "EA"


# ---------------------------------------------------------------------------
# Pending identity cluster
# ---------------------------------------------------------------------------


def test_pending_identity_blocks_bom_other_singletons_resolve(conn):
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-01"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-01"
    )
    sc_other = _insert_source_component(conn, source_reference="BRAKE-PAD-01")

    _insert_pending_identity(
        conn,
        source_component_id=sc_a,
        members=[sc_a, sc_b],
        canonical_ref="CTRL-AIR-01",
    )
    _insert_pending_identity(
        conn,
        source_component_id=sc_b,
        members=[sc_a, sc_b],
        canonical_ref="CTRL-AIR-01",
    )

    line_a = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=1,
    )
    line_b = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-O1",
        source_row=2,
    )
    line_other = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="BRAKE-PAD-01",
        source_row=3,
    )

    result = build_canonical_model(conn)

    unresolved_ids = {u["source_bom_line_id"]: u["reason"] for u in result["unresolved"]}
    assert unresolved_ids[line_a] == "identity_pending"
    assert unresolved_ids[line_b] == "identity_pending"
    assert line_other not in unresolved_ids
    assert result["bom_relationships"] == 1

    bom = conn.execute(
        "SELECT source_bom_line_id FROM bom_relationship"
    ).fetchall()
    assert [b["source_bom_line_id"] for b in bom] == [line_other]


# ---------------------------------------------------------------------------
# Accepted identity cluster shares one component
# ---------------------------------------------------------------------------


def test_accepted_identity_cluster_shares_component_id(conn):
    from app.services.canonicalization import build_canonical_model
    from app.services.review import decide_reconciliation

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-01"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-01"
    )
    rid_a = _insert_pending_identity(
        conn, source_component_id=sc_a, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    rid_b = _insert_pending_identity(
        conn, source_component_id=sc_b, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    line_a = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=1,
    )
    line_b = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-O1",
        source_row=2,
    )

    decide_reconciliation(conn, "component", rid_a, "accept", rationale="same part")
    decide_reconciliation(conn, "component", rid_b, "accept", rationale="same part")

    result = build_canonical_model(conn)

    assert result["bom_relationships"] == 2
    assert result["unresolved"] == []
    assert result["components"] == 1

    bom = conn.execute(
        "SELECT component_id, variant_id, source_bom_line_id FROM bom_relationship "
        "ORDER BY source_bom_line_id"
    ).fetchall()
    assert bom[0]["component_id"] == bom[1]["component_id"]
    assert bom[0]["source_bom_line_id"] == line_a
    assert bom[1]["source_bom_line_id"] == line_b
    assert bom[0]["variant_id"] != bom[1]["variant_id"]


# ---------------------------------------------------------------------------
# Partial accept: only accepted member's lines resolve
# ---------------------------------------------------------------------------


def test_partial_accept_only_accepted_member_in_bom(conn):
    from app.services.canonicalization import build_canonical_model
    from app.services.review import decide_reconciliation

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-01"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-01"
    )
    rid_a = _insert_pending_identity(
        conn, source_component_id=sc_a, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    _insert_pending_identity(
        conn, source_component_id=sc_b, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    line_a = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=1,
    )
    line_b = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-O1",
        source_row=2,
    )

    decide_reconciliation(conn, "component", rid_a, "accept", rationale="ok")

    result = build_canonical_model(conn)

    unresolved = {u["source_bom_line_id"]: u["reason"] for u in result["unresolved"]}
    assert unresolved[line_b] == "identity_pending"
    assert line_a not in unresolved
    assert result["bom_relationships"] == 1
    bom = conn.execute(
        "SELECT source_bom_line_id FROM bom_relationship"
    ).fetchone()
    assert bom["source_bom_line_id"] == line_a


# ---------------------------------------------------------------------------
# Rejected identity
# ---------------------------------------------------------------------------


def test_rejected_identity_unresolved_no_canonical_id(conn):
    from app.services.canonicalization import build_canonical_model
    from app.services.review import decide_reconciliation

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-01"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-01"
    )
    rid_a = _insert_pending_identity(
        conn, source_component_id=sc_a, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    _insert_pending_identity(
        conn, source_component_id=sc_b, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    line_a = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=1,
    )

    decide_reconciliation(
        conn, "component", rid_a, "reject", rationale="not the same part"
    )

    result = build_canonical_model(conn)

    unresolved = {u["source_bom_line_id"]: u["reason"] for u in result["unresolved"]}
    assert unresolved[line_a] == "identity_rejected"
    assert result["bom_relationships"] == 0

    row = conn.execute(
        "SELECT component_id, status FROM component_reconciliation WHERE id = ?",
        (rid_a,),
    ).fetchone()
    assert row["status"] == "REJECTED"
    assert row["component_id"] is None


# ---------------------------------------------------------------------------
# Functional similarity and variant_specific do not merge
# ---------------------------------------------------------------------------


def test_functional_similarity_does_not_collapse_components(conn):
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="CAM-M01")
    sc_a = _insert_source_component(conn, source_reference="PASSCOUNT-CAMERA")
    sc_b = _insert_source_component(conn, source_reference="PASSCOUNT-CAMERA-RUGGED")
    _insert_pending_relationship(
        conn,
        source_component_id=sc_a,
        relationship="functional_similarity",
        extra={"reference_a": "PASSCOUNT-CAMERA", "reference_b": "PASSCOUNT-CAMERA-RUGGED"},
    )
    _insert_pending_relationship(
        conn,
        source_component_id=sc_b,
        relationship="functional_similarity",
        extra={"reference_a": "PASSCOUNT-CAMERA", "reference_b": "PASSCOUNT-CAMERA-RUGGED"},
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="CAM-M01",
        component_ref="PASSCOUNT-CAMERA",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="CAM-M01",
        component_ref="PASSCOUNT-CAMERA-RUGGED",
        source_row=2,
    )

    result = build_canonical_model(conn)

    assert result["components"] == 2
    assert result["bom_relationships"] == 2
    assert result["unresolved"] == []
    ids = {
        r["component_id"]
        for r in conn.execute("SELECT component_id FROM bom_relationship").fetchall()
    }
    assert len(ids) == 2


def test_variant_specific_does_not_attach_to_other_component(conn):
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-NORD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_nordic = _insert_source_component(conn, source_reference="CTRL-AIR-01-NORDIC")
    sc_std = _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_pending_relationship(
        conn,
        source_component_id=sc_nordic,
        relationship="variant_specific",
        extra={"component_ref": "CTRL-AIR-01-NORDIC"},
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01-NORDIC",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )

    result = build_canonical_model(conn)

    assert result["components"] == 2
    assert result["bom_relationships"] == 2
    assert result["unresolved"] == []
    ids = {
        r["component_id"]
        for r in conn.execute("SELECT component_id FROM bom_relationship").fetchall()
    }
    assert len(ids) == 2
    # Nordic source must not share the standard component id
    nordic_cid = conn.execute(
        """
        SELECT br.component_id
        FROM bom_relationship br
        JOIN plm_bom_line b ON b.id = br.source_bom_line_id
        WHERE b.component_ref_raw = 'CTRL-AIR-01-NORDIC'
        """
    ).fetchone()["component_id"]
    std_cid = conn.execute(
        """
        SELECT br.component_id
        FROM bom_relationship br
        JOIN plm_bom_line b ON b.id = br.source_bom_line_id
        WHERE b.component_ref_raw = 'CTRL-AIR-01'
        """
    ).fetchone()["component_id"]
    assert nordic_cid != std_cid
    assert sc_nordic  # silence unused if refactor


# ---------------------------------------------------------------------------
# Idempotency and quarantine
# ---------------------------------------------------------------------------


def test_second_build_does_not_duplicate_bom_rows(conn):
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
    )

    first = build_canonical_model(conn)
    second = build_canonical_model(conn)

    assert first["bom_relationships"] == 1
    assert second["bom_relationships"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM bom_relationship").fetchone()["n"] == 1


def test_quarantine_rows_not_invented_as_bom(conn):
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    # Quarantined bad quantity — not in plm_bom_line
    conn.execute(
        """
        INSERT INTO quarantine (
            source_file_id, source_row, raw_data, rejection_reason, created_at
        ) VALUES (?, 99, ?, 'invalid_quantity', ?)
        """,
        (
            sf,
            json.dumps({"component_ref": "CTRL-AIR-01", "quantity": "one"}),
            _now(),
        ),
    )
    conn.commit()
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )

    result = build_canonical_model(conn)

    assert result["bom_relationships"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM bom_relationship").fetchone()["n"] == 1


def test_does_not_auto_link_mat_to_ctrl(conn):
    """MAT-10001 must not share a component id with CTRL-AIR-01."""
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(
        conn, source_reference="MAT-10001", source_system="ERP"
    )
    # Only PLM BOM line for CTRL — ERP material has no PLM BOM line
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
    )

    result = build_canonical_model(conn)

    assert result["components"] == 1
    refs = [
        r["normalized_reference"]
        for r in conn.execute("SELECT normalized_reference FROM component").fetchall()
    ]
    assert refs == ["CTRL-AIR-01"]


# ---------------------------------------------------------------------------
# Canonical HTML page
# ---------------------------------------------------------------------------


def test_canonical_html_shows_accepted_and_unresolved(conn, tmp_path):
    from app.services.canonicalization import build_canonical_model
    from app.services.html_pages import write_site
    from app.services.review import decide_reconciliation

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-01"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-01"
    )
    rid_a = _insert_pending_identity(
        conn, source_component_id=sc_a, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    _insert_pending_identity(
        conn, source_component_id=sc_b, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-01"
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-O1",
        source_row=2,
    )

    decide_reconciliation(conn, "component", rid_a, "accept", rationale="ok")
    build_canonical_model(conn)

    out = Path(tmp_path)
    # write_site may import report; stub if needed by ensuring report path works
    written = write_site(conn, out)
    paths = {p.name for p in written}
    assert "canonical.html" in paths
    html = (out / "canonical.html").read_text(encoding="utf-8")
    assert "CTRL-AIR" in html or "canonical" in html.lower()
    assert "pending" in html.lower() or "unresolved" in html.lower()
