"""
Tests for already-reused and reusable-candidate reports (Plan 03-04).
"""
from datetime import datetime, timezone
import json

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


def _insert_erp_material(
    conn,
    *,
    source_file_id: int,
    material_id: str,
    description: str,
    category: str,
    source_row: int = 1,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO erp_material (
            source_file_id, source_row, material_id_raw, description_raw,
            category_raw, material_id_normalized
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_file_id, source_row, material_id, description, category, material_id),
    )
    conn.commit()
    return cur.lastrowid


def _insert_note(
    conn,
    *,
    source_file_id: int,
    note_id: str,
    object_reference: str,
    note_text: str = "qualification note",
    source_row: int = 1,
) -> int:
    """Insert an engineering note; note_id is stored in author for fixture labeling."""
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


# ---------------------------------------------------------------------------
# already_reused
# ---------------------------------------------------------------------------


def test_already_reused_component_on_two_variants(conn):
    from app.services.analysis import already_reused
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
        source_row=1,
    )
    line2 = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=2,
    )

    build_canonical_model(conn)
    rows = already_reused(conn)

    components = [r for r in rows if r["entity_type"] == "component"]
    assert len(components) == 1
    row = components[0]
    assert row["variant_count"] == 2
    assert row["variant_refs"] == ["REGIO-NORD", "REGIO-STD"]
    assert sorted(row["source_bom_line_ids"]) == sorted([line1, line2])
    assert row["canonical_id"] is not None
    assert row["name"]
    assert "same canonical component" in row["explanation"].lower()
    assert "REGIO-STD" in row["explanation"] or "REGIO-NORD" in row["explanation"]


def test_already_reused_omits_single_variant_component(conn):
    from app.services.analysis import already_reused
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
        source_row=1,
    )

    build_canonical_model(conn)
    rows = already_reused(conn)

    assert [r for r in rows if r["entity_type"] == "component"] == []


def test_pending_identity_omitted_until_accepted(conn):
    from app.services.analysis import already_reused
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
        variant_ref="REGIO-NORD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-O1",
        source_row=2,
    )

    build_canonical_model(conn)
    pending_rows = already_reused(conn)
    assert [r for r in pending_rows if r["entity_type"] == "component"] == []

    decide_reconciliation(conn, "component", rid_a, "accept", rationale="same part")
    decide_reconciliation(conn, "component", rid_b, "accept", rationale="same part")
    build_canonical_model(conn)

    accepted_rows = already_reused(conn)
    components = [r for r in accepted_rows if r["entity_type"] == "component"]
    assert len(components) == 1
    row = components[0]
    assert row["variant_count"] == 2
    explanation = row["explanation"]
    assert "CTRL-AIR01" in explanation
    assert "CTRL-AIR-O1" in explanation


def test_already_reused_assembly_on_two_variants(conn):
    from app.services.analysis import already_reused
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_variant(conn, sf, "REGIO-COMFORT")
    _insert_source_assembly(conn, source_reference="HVAC-M01")
    _insert_source_component(conn, source_reference="CTRL-AIR-01")
    _insert_source_component(conn, source_reference="FAN-AIR01")
    line1 = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-STD",
        assembly_ref="HVAC-M01",
        component_ref="CTRL-AIR-01",
        source_row=1,
    )
    line2 = _insert_bom_line(
        conn,
        source_file_id=sf,
        variant_ref="REGIO-COMFORT",
        assembly_ref="HVAC-M01",
        component_ref="FAN-AIR01",
        source_row=2,
    )

    build_canonical_model(conn)
    rows = already_reused(conn)

    assemblies = [r for r in rows if r["entity_type"] == "assembly"]
    assert len(assemblies) == 1
    row = assemblies[0]
    assert row["variant_count"] == 2
    assert row["variant_refs"] == ["REGIO-COMFORT", "REGIO-STD"]
    assert sorted(row["source_bom_line_ids"]) == sorted([line1, line2])
    assert row["canonical_id"] is not None
    assert row["name"]
    assert row["explanation"]


# ---------------------------------------------------------------------------
# reusable_candidates
# ---------------------------------------------------------------------------


def test_functional_similarity_appears_once_not_in_already_reused(conn):
    from app.services.analysis import already_reused, reusable_candidates
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_variant(conn, sf, "REGIO-STD")
    _insert_source_assembly(conn, source_reference="DOOR-M01")
    sc_a = _insert_source_component(conn, source_reference="CTRL-DOOR-01")
    sc_b = _insert_source_component(conn, source_reference="CTRL-DOOR-EXP")
    rid = _insert_pending_relationship(
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
        variant_ref="REGIO-STD",
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
    row = door[0]
    assert row["relationship"] == "functional_similarity"
    assert row["review_needed"] is True
    assert isinstance(row["blocked_by"], list)
    assert rid in row["evidence"] or any(
        e == rid or (isinstance(e, str) and str(rid) in e) for e in row["evidence"]
    )
    assert "CTRL-DOOR-01" in row["explanation"]
    assert "CTRL-DOOR-EXP" in row["explanation"]
    assert "functional_similarity" in row["explanation"]

    reused = already_reused(conn)
    for r in reused:
        if r["entity_type"] == "component":
            assert r["name"] not in ("CTRL-DOOR-01", "CTRL-DOOR-EXP") or r["variant_count"] < 2


def test_variant_specific_not_a_candidate(conn):
    from app.services.analysis import reusable_candidates

    sc = _insert_source_component(conn, source_reference="CTRL-AIR-01-NORDIC")
    _insert_pending_relationship(
        conn,
        source_component_id=sc,
        relationship="variant_specific",
        extra={"component_ref": "CTRL-AIR-01-NORDIC", "review_needed": False},
        confidence=0.95,
    )

    candidates = reusable_candidates(conn)
    assert candidates == []


def test_rugged_camera_pair_with_notes(conn):
    from app.services.analysis import already_reused, reusable_candidates
    from app.services.canonicalization import build_canonical_model

    sf = _source_file(conn)
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-10033",
        description="Passenger Counting Camera",
        category="COUNTING",
        source_row=1,
    )
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-10034",
        description="Passenger Counting Camera Rugged",
        category="COUNTING",
        source_row=2,
    )
    # Dataset notes N-018 / N-019 (qualification evidence for SCEN-F)
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-018",
        object_reference="PASSCOUNT-CAMERA",
        note_text="Camera family is shared. Rugged preferred when qualification requires it.",
        source_row=18,
    )
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-019",
        object_reference="PASSCOUNT-CAMERA-RUGGED",
        note_text="Same protocol; housing and temperature qualification differ.",
        source_row=19,
    )

    candidates = reusable_candidates(conn)
    camera = [
        c
        for c in candidates
        if {c["left_ref"], c["right_ref"]} == {"MAT-10033", "MAT-10034"}
    ]
    assert len(camera) == 1
    row = camera[0]
    assert row["left_ref"] == "MAT-10033"
    assert row["right_ref"] == "MAT-10034"
    assert row["relationship"] == "functional_similarity"
    assert row["review_needed"] is True
    assert "N-018" in row["evidence"]
    assert "N-019" in row["evidence"]
    explanation = row["explanation"].lower()
    assert "qualification" in explanation
    assert "not merged" in explanation or "were not merged" in explanation

    # Not a canonical merge — no shared component id in already_reused for this pair
    build_canonical_model(conn)
    reused_names = {r["name"] for r in already_reused(conn)}
    assert "MAT-10033" not in reused_names
    assert "MAT-10034" not in reused_names


def test_nordic_fan_not_paired_by_rugged_rule(conn):
    from app.services.analysis import reusable_candidates

    sf = _source_file(conn)
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-FAN-STD",
        description="HVAC Fan Standard",
        category="HVAC",
        source_row=1,
    )
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-FAN-ND",
        description="HVAC Fan Nordic",
        category="HVAC",
        source_row=2,
    )

    candidates = reusable_candidates(conn)
    fan_pairs = [
        c
        for c in candidates
        if {c["left_ref"], c["right_ref"]} == {"MAT-FAN-STD", "MAT-FAN-ND"}
    ]
    assert fan_pairs == []


def test_candidates_ordered_by_left_then_right(conn):
    from app.services.analysis import reusable_candidates

    sf = _source_file(conn)
    sc_z = _insert_source_component(conn, source_reference="ZZZ-CTRL-01")
    sc_y = _insert_source_component(conn, source_reference="YYY-CTRL-EXP")
    sc_a = _insert_source_component(conn, source_reference="AAA-DOOR-01")
    sc_b = _insert_source_component(conn, source_reference="AAA-DOOR-EXP")
    _insert_pending_relationship(
        conn,
        source_component_id=sc_z,
        relationship="functional_similarity",
        extra={"review_needed": True, "reference_a": "ZZZ-CTRL-01", "reference_b": "YYY-CTRL-EXP"},
    )
    _insert_pending_relationship(
        conn,
        source_component_id=sc_a,
        relationship="functional_similarity",
        extra={"review_needed": True, "reference_a": "AAA-DOOR-01", "reference_b": "AAA-DOOR-EXP"},
    )
    # Extra ERP pair that sorts between AAA and ZZZ
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-10033",
        description="Passenger Counting Camera",
        category="COUNTING",
        source_row=1,
    )
    _insert_erp_material(
        conn,
        source_file_id=sf,
        material_id="MAT-10034",
        description="Passenger Counting Camera Rugged",
        category="COUNTING",
        source_row=2,
    )
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-018",
        object_reference="PASSCOUNT-CAMERA",
        source_row=18,
    )
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-019",
        object_reference="PASSCOUNT-CAMERA-RUGGED",
        source_row=19,
    )
    # silence unused
    assert sc_y and sc_b

    candidates = reusable_candidates(conn)
    keys = [(c["left_ref"], c["right_ref"]) for c in candidates]
    assert keys == sorted(keys)


def test_every_candidate_has_explanation_naming_refs_and_evidence(conn):
    from app.services.analysis import reusable_candidates

    sf = _source_file(conn)
    sc_a = _insert_source_component(conn, source_reference="CTRL-DOOR-01")
    rid = _insert_pending_relationship(
        conn,
        source_component_id=sc_a,
        relationship="functional_similarity",
        extra={
            "review_needed": True,
            "reference_a": "CTRL-DOOR-01",
            "reference_b": "CTRL-DOOR-EXP",
        },
    )
    _insert_note(
        conn,
        source_file_id=sf,
        note_id="N-005",
        object_reference="CTRL-DOOR-01",
        note_text="Do not merge the two material identities.",
        source_row=5,
    )

    candidates = reusable_candidates(conn)
    assert len(candidates) >= 1
    for row in candidates:
        assert isinstance(row["explanation"], str)
        assert row["explanation"].strip()
        assert row["left_ref"] in row["explanation"]
        assert row["right_ref"] in row["explanation"]
        assert row["relationship"] in row["explanation"]
        for eid in row["evidence"]:
            assert str(eid) in row["explanation"]

    door = next(
        c
        for c in candidates
        if {c["left_ref"], c["right_ref"]} == {"CTRL-DOOR-01", "CTRL-DOOR-EXP"}
    )
    assert rid in door["evidence"] or any(str(rid) == str(e) for e in door["evidence"])
    assert "N-005" in door["evidence"]
