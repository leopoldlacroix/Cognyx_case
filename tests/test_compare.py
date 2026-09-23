"""
Tests for assembly-level variant comparison (Plan 04-01).
"""
from datetime import datetime, timezone
import json

import pytest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_file(conn, file_name: str = "bom_export.csv") -> int:
    cur = conn.execute(
        """
        INSERT INTO source_file (source_system, file_name, file_hash, ingested_at)
        VALUES ('PLM', ?, 'hash-test', ?)
        """,
        (file_name, _now()),
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
    method: str = "STRUCTURED",
    confidence: float = 0.50,
) -> int:
    evidence = {"relationship": relationship, **(extra or {})}
    cur = conn.execute(
        """
        INSERT INTO component_reconciliation (
            source_component_id, component_id, status, method, confidence,
            rationale, evidence_json, created_at
        ) VALUES (?, NULL, 'PENDING', ?, ?, ?, ?, ?)
        """,
        (
            source_component_id,
            method,
            confidence,
            relationship,
            json.dumps(evidence, sort_keys=True, separators=(",", ":")),
            _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_note(
    conn,
    *,
    source_file_id: int,
    note_id: str,
    object_reference: str,
    note_text: str,
    source_row: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO engineering_note (
            source_file_id, source_row, object_reference_raw, object_type,
            language, author, date, note_text
        ) VALUES (?, ?, ?, 'component', 'en', ?, '2026-03-03', ?)
        """,
        (source_file_id, source_row, object_reference, note_id, note_text),
    )
    conn.commit()
    return cur.lastrowid


def _assembly(result: dict, assembly_ref: str) -> dict:
    matches = [a for a in result["assemblies"] if a["assembly_ref"] == assembly_ref]
    assert len(matches) == 1, f"expected one assembly {assembly_ref}, got {result['assemblies']}"
    return matches[0]


def _component(assembly: dict, ref: str) -> dict:
    matches = [c for c in assembly["components"] if c["ref"] == ref]
    assert len(matches) == 1, f"expected one component {ref}, got {assembly['components']}"
    return matches[0]


# ---------------------------------------------------------------------------
# compare_variants — overlap cases
# ---------------------------------------------------------------------------


def test_shared_and_right_only_overlap_half(conn):
    """A on both, B only on NORDIC → ratio 0.5, high_overlap true."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(conn, source_reference="FAN-NORDIC-01")
    line_a_std = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    line_a_nord = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    line_b = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="FAN-NORDIC-01",
        source_row=3,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")

    assert result["left_ref"] == "REGIO-STD"
    assert result["right_ref"] == "REGIO-NORDIC"
    asm = _assembly(result, "HVAC-M01")
    assert asm["shared_count"] == 1
    assert asm["left_only_count"] == 0
    assert asm["right_only_count"] == 1
    assert asm["overlap_ratio"] == 0.5
    assert asm["high_overlap"] is True
    assert asm["canonical_assembly_id"] is not None

    a = _component(asm, "CTRL-AIR-01")
    assert a["label"] == "reused"
    assert a["side"] == "both"
    assert a["canonical_id"] is not None
    assert sorted(a["source_bom_line_ids"]) == sorted([line_a_std, line_a_nord])
    assert a["anchor"] == "REGIO-STD-REGIO-NORDIC-HVAC-M01-CTRL-AIR-01"
    assert a["records"]
    for rec in a["records"]:
        assert rec["source_table"] == "plm_bom_line"
        assert "source_id" in rec
        assert rec["source_file"] == "bom_export.csv"
        assert isinstance(rec["source_row"], int)

    b = _component(asm, "FAN-NORDIC-01")
    assert b["label"] == "right_only"
    assert b["side"] == "right"
    assert sorted(b["source_bom_line_ids"]) == [line_b]


def test_full_overlap_ratio_one(conn):
    """Only component A on both sides → ratio 1.0."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")
    assert asm["shared_count"] == 1
    assert asm["left_only_count"] == 0
    assert asm["right_only_count"] == 0
    assert asm["overlap_ratio"] == 1.0
    assert asm["high_overlap"] is True
    assert _component(asm, "CTRL-AIR-01")["label"] == "reused"


def test_one_side_only_ratio_zero(conn):
    """Component B only on one side → ratio 0.0, high_overlap false."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="FAN-NORDIC-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="FAN-NORDIC-01",
        source_row=1,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")
    assert asm["shared_count"] == 0
    assert asm["right_only_count"] == 1
    assert asm["overlap_ratio"] == 0.0
    assert asm["high_overlap"] is False
    assert _component(asm, "FAN-NORDIC-01")["label"] == "right_only"


def test_pending_identity_is_unresolved_outside_ratio(conn):
    """PENDING identity BOM line is unresolved; not in shared or ratio denominator."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    # Shared singleton on both sides (in ratio)
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    # Pending identity cluster — lines stay out of bom_relationship
    sc_a = _insert_source_component(
        conn, source_reference="CTRL-AIR01", normalized_reference="CTRL-AIR-PENDING"
    )
    sc_b = _insert_source_component(
        conn, source_reference="CTRL-AIR-O1", normalized_reference="CTRL-AIR-PENDING"
    )
    _insert_pending_identity(
        conn, source_component_id=sc_a, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-PENDING"
    )
    _insert_pending_identity(
        conn, source_component_id=sc_b, members=[sc_a, sc_b], canonical_ref="CTRL-AIR-PENDING"
    )
    pending_line = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR01",
        source_row=3,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")

    assert asm["shared_count"] == 1
    assert asm["unresolved_count"] >= 1
    # Pending line must not inflate the ratio denominator (still 1/1 = 1.0)
    assert asm["overlap_ratio"] == 1.0

    unresolved = [c for c in asm["components"] if c["label"] == "unresolved"]
    assert any(pending_line in c["source_bom_line_ids"] for c in unresolved)
    for c in unresolved:
        assert c["canonical_id"] is None
        assert c["label"] == "unresolved"


def test_variant_specific_nordic_not_candidate(conn):
    """Nordic variant_specific part is labeled variant_specific, not a candidate."""
    from app.services.analysis import compare_variants, reusable_candidates
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    sc_nordic = _insert_source_component(conn, source_reference="CTRL-AIR-01-NORDIC")
    _insert_pending_relationship(
        conn,
        source_component_id=sc_nordic,
        relationship="variant_specific",
        extra={"component_ref": "CTRL-AIR-01-NORDIC", "review_needed": False},
        confidence=0.95,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01-NORDIC",
        source_row=3,
    )

    build_canonical_model(conn)
    candidates = reusable_candidates(conn)
    assert not any(
        "CTRL-AIR-01-NORDIC" in (c["left_ref"], c["right_ref"]) for c in candidates
    )

    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")
    nordic = _component(asm, "CTRL-AIR-01-NORDIC")
    assert nordic["label"] == "variant_specific"
    assert nordic["side"] == "right"
    assert asm["variant_specific_count"] >= 1
    assert asm["candidate_count"] == 0
    # variant_specific is a subset of right_only, not an extra ratio term
    assert asm["right_only_count"] >= 1
    assert asm["overlap_ratio"] == 0.5  # 1 shared / (1 shared + 1 right_only)


def test_similarity_pair_both_reuse_candidate(conn):
    """Two different canonical components reported as a candidate pair stay separate."""
    from app.services.analysis import compare_variants, reusable_candidates
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="DOOR-M01")
    sc_a = _insert_source_component(conn, source_reference="CTRL-DOOR-01")
    sc_b = _insert_source_component(conn, source_reference="CTRL-DOOR-EXP")
    _insert_pending_relationship(
        conn,
        source_component_id=sc_a,
        relationship="functional_similarity",
        extra={
            "review_needed": True,
            "reference_a": "CTRL-DOOR-01",
            "reference_b": "CTRL-DOOR-EXP",
        },
    )
    _insert_pending_relationship(
        conn,
        source_component_id=sc_b,
        relationship="functional_similarity",
        extra={
            "review_needed": True,
            "reference_a": "CTRL-DOOR-01",
            "reference_b": "CTRL-DOOR-EXP",
        },
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="DOOR-M01",
        component_ref="CTRL-DOOR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="DOOR-M01",
        component_ref="CTRL-DOOR-EXP",
        source_row=2,
    )

    build_canonical_model(conn)
    candidates = reusable_candidates(conn)
    door = [
        c
        for c in candidates
        if {c["left_ref"], c["right_ref"]} == {"CTRL-DOOR-01", "CTRL-DOOR-EXP"}
    ]
    assert len(door) == 1

    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "DOOR-M01")
    assert asm["candidate_count"] == 1
    left = _component(asm, "CTRL-DOOR-01")
    right = _component(asm, "CTRL-DOOR-EXP")
    assert left["label"] == "reuse_candidate"
    assert right["label"] == "reuse_candidate"
    assert left["canonical_id"] is not None
    assert right["canonical_id"] is not None
    assert left["canonical_id"] != right["canonical_id"]


def test_blocked_shared_component_stays_in_shared_count(conn):
    """Blocker match labels blocked but still counts as shared; both values kept."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model
    from app.services.quality import blockers

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-064",
        object_reference="CTRL-AIR-01",
        note_text="Operating voltage listed as 24 V DC and also 48 V DC — conflict.",
        source_row=64,
    )

    build_canonical_model(conn)
    blocker_rows = blockers(conn)
    assert any(b["entity_ref"] == "CTRL-AIR-01" for b in blocker_rows)
    voltage_blocker = next(b for b in blocker_rows if b["entity_ref"] == "CTRL-AIR-01")
    assert "24 V DC" in voltage_blocker["values"]
    assert "48 V DC" in voltage_blocker["values"]

    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")
    assert asm["shared_count"] == 1
    assert asm["conflict_count"] >= 1
    blocked = _component(asm, "CTRL-AIR-01")
    assert blocked["label"] == "blocked"
    assert blocked["side"] == "both"
    # Blockers() still holds both values — compare does not drop one
    still = blockers(conn)
    volt = next(b for b in still if b["entity_ref"] == "CTRL-AIR-01")
    assert "24 V DC" in volt["values"] and "48 V DC" in volt["values"]


def test_assembly_only_on_one_variant_still_appears(conn):
    """Assembly present on only one of the two variants still appears in the list."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_assembly(conn, source_reference="DOOR-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(conn, source_reference="CTRL-DOOR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    # DOOR only on STD
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="DOOR-M01",
        component_ref="CTRL-DOOR-01",
        source_row=3,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    refs = [a["assembly_ref"] for a in result["assemblies"]]
    assert refs == sorted(refs)
    assert "HVAC-M01" in refs
    assert "DOOR-M01" in refs
    door = _assembly(result, "DOOR-M01")
    assert door["left_only_count"] == 1
    assert door["shared_count"] == 0


def test_swap_left_right_swaps_sides_keeps_ratio(conn):
    """Swapping left/right swaps left_only/right_only; shared and ratio unchanged."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(conn, source_reference="FAN-NORDIC-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="FAN-NORDIC-01",
        source_row=3,
    )

    build_canonical_model(conn)
    forward = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    swapped = compare_variants(conn, "REGIO-NORDIC", "REGIO-STD")

    f_asm = _assembly(forward, "HVAC-M01")
    s_asm = _assembly(swapped, "HVAC-M01")
    assert f_asm["shared_count"] == s_asm["shared_count"]
    assert f_asm["overlap_ratio"] == s_asm["overlap_ratio"]
    assert f_asm["left_only_count"] == s_asm["right_only_count"]
    assert f_asm["right_only_count"] == s_asm["left_only_count"]
    assert swapped["left_ref"] == "REGIO-NORDIC"
    assert swapped["right_ref"] == "REGIO-STD"


def test_mat_10001_not_treated_as_ctrl_air_01(conn):
    """MAT-10001 and CTRL-AIR-01 stay distinct canonical components."""
    from app.services.analysis import compare_variants
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(
        conn, source_reference="MAT-10001", source_system="ERP"
    )
    # Also need PLM source for MAT if it appears on BOM as PLM ref —
    # BOM joins on PLM source_component; insert PLM component with that ref.
    _insert_source_component(conn, source_reference="MAT-10001", source_system="PLM")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="MAT-10001",
        source_row=3,
    )

    build_canonical_model(conn)
    result = compare_variants(conn, "REGIO-STD", "REGIO-NORDIC")
    asm = _assembly(result, "HVAC-M01")
    ctrl = _component(asm, "CTRL-AIR-01")
    mat = _component(asm, "MAT-10001")
    assert ctrl["canonical_id"] != mat["canonical_id"]
    assert ctrl["label"] == "reused"
    assert mat["label"] == "left_only"


# ---------------------------------------------------------------------------
# all_variant_pairs
# ---------------------------------------------------------------------------


def test_all_variant_pairs_lexicographic_unordered(conn):
    """Pairs of distinct variant refs, left < right, sorted; not hardcoded."""
    from app.services.analysis import all_variant_pairs
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-NORDIC")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORDIC",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )
    build_canonical_model(conn)

    pairs = all_variant_pairs(conn)
    assert pairs == [("REGIO-NORDIC", "REGIO-STD")]

    # Three variants → C(3,2) = 3 pairs, sorted
    _insert_variant(conn, sf, "REGIO-EXPORT")
    _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-EXPORT",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=3,
    )
    build_canonical_model(conn)
    pairs3 = all_variant_pairs(conn)
    assert pairs3 == [
        ("REGIO-EXPORT", "REGIO-NORDIC"),
        ("REGIO-EXPORT", "REGIO-STD"),
        ("REGIO-NORDIC", "REGIO-STD"),
    ]
    for left, right in pairs3:
        assert left < right
