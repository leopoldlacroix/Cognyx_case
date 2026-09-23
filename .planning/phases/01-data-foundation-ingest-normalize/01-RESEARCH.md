# Phase 01: Data Foundation - Research

**Researched:** 2026-09-22
**Domain:** Python SQLite data ingestion pipeline with deterministic normalization
**Confidence:** HIGH

## Summary

Phase 1 implements the data ingestion and normalization layer for the Cognyx BOM Reuse Explorer. The project ingests 6 CSV files from PLM/ERP/engineering systems into SQLite source tables with full provenance, applies hard validation (quarantine malformed rows) and soft validation (warnings), and produces deterministic normalized values alongside raw values using a config-driven alias system.

**Primary recommendation:** Use Python's built-in `csv` module with `sqlite3` for the ingestion pipeline. Use a simple JSON config for aliases. No external ORM required — SQLAlchemy adds complexity without benefit for this scale. Implement source entity extraction as a post-ingestion step using deterministic deduplication by `(source_system, source_reference)`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Create separate raw source tables per source system: `plm_bom_line`, `plm_assembly`, `plm_variant`, `erp_material`, `erp_supplier`, `engineering_note`. Each has `source_file_id` FK, `source_row`, raw columns (immutable), and normalized columns stored alongside. — **Reversibility:** costly
- **D-02:** `source_file.file_hash` is NOT NULL and unique per `(source_system, file_hash)`. Ingestion always computes the hash for reliable idempotency. — **Reversibility:** costly
- **D-03:** Normalization config lives in `config/normalization.json`. Aliases: UOM (`pcs/pc/piece/units → EA`), supplier (`SIEMENS* → SIEMENS MOBILITY`), reference (`CTRL-AIR01 → CTRL-AIR-01`, `CTRL-HVAC-001 → CTRL-AIR-01`), voltage (`24V/24VDC/24 VOLTS DC → 24 V DC`). Generic rules: whitespace collapse, casing standardization for identifiers, punctuation harmonization. — **Reversibility:** reversible
- **D-04:** Raw values are never overwritten. Each normalized column has a `_raw` counterpart. Unknown values: keep raw, leave normalized null/unchanged, emit warning, do not guess. — **Reversibility:** one-way
- **D-05:** Hard validation quarantines structurally malformed rows (wrong column count, unparseable numbers) and rows with missing required identifiers or unparseable quantities. Quarantined rows go to a separate `quarantine` table with rejection reason. — **Reversibility:** costly
- **D-06:** Soft validation keeps rows but emits warnings for missing description, unknown UOM, empty supplier, contradictory technical fields. Warnings stored in a separate `warnings` table linked to source rows. — **Reversibility:** costly
- **D-07:** For BOM lines, `quantity` is required. Unparseable quantity → hard-invalid → quarantined. `quantity_normalized` is REAL and contains a valid numeric for all accepted BOM rows. — **Reversibility:** costly
- **D-08:** Populate `source_component`, `source_assembly`, `source_supplier` in Phase 1. Deterministic deduplication by `(source_system, source_reference)`. This is NOT reconciliation. — **Reversibility:** costly
- **D-09:** Reconciliation eligibility is derived from reconciliation rows (not a redundant `processed` flag). Since no reconciliation records exist yet in Phase 1, all source entities start as "never assessed". — **Reversibility:** reversible
- **D-10:** Engineering notes are ingested raw in Phase 1. No language detection, no text normalization, no semantic processing of `note_text`. — **Reversibility:** reversible
- **D-11:** Variant references use only generic deterministic rules. No semantic aliasing unless explicitly configured. — **Reversibility:** reversible
- **D-12:** SQLite for storage. — **Reversibility:** costly
- **D-13:** Python as sole implementation language. — **Reversibility:** costly
- **D-14:** No LLM calls in Phase 1. All normalization and extraction is deterministic. — **Reversibility:** reversible

### Claude's Discretion

- Python web framework / API approach for the data explorer (if any in Phase 1) — blueprint specifies API endpoints but Phase 1 deliverable may be CLI + SQLite + report output. Planner should decide based on time budget.
- Whether to use an ORM (e.g., SQLAlchemy) or raw SQLite for schema management and queries.
- Exact `src/` directory layout — blueprint suggests `app/` structure with `backend/`, `worker/`, `domain/`, `services/`, `db/`, `tests/` subdirectories.
- Migration approach — single init script vs. versioned migrations.

### Deferred Ideas (OUT OF SCOPE)

- LLM-assisted reconciliation — Phase 2 (RECON-01 through RECON-04)
- Human review workflow (accept/reject UI) — Phase 3 (REVIEW-01 through REVIEW-03)
- Cross-variant reuse analysis reports — Phase 3+ (ANALYSIS-01 through ANALYSIS-05)
- ERP material normalization (supplier ID mapping, UOM standardization) — Phase 2 (NORM-05)
- Engineering note normalization (language detection, text extraction) — Phase 2 (NORM-06)
- Technical fact extraction and conflict detection — Phase 3+ (blueprint Phase 9)
- Canonical BOM materialization — Phase 3 (blueprint Phase 8)
- Web UI (React/TypeScript) — out of PoC scope; CLI + report output for demo

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | Ingest all 6 source CSV files with provenance | Python csv + sqlite3; file hash via hashlib; source_row preserved |
| INGEST-02 | Hard validation quarantine for malformed rows | Quarantine table with rejection_reason column; schema validation before insert |
| INGEST-03 | Soft validation warnings for missing description, unknown UOM, empty supplier | Warnings table with source_row FK; warning_type enum |
| NORM-01 | Normalize PLM BOM lines (whitespace, casing, punctuation) | Python string methods: strip, upper/lower, regex for punctuation |
| NORM-02 | UOM aliases (pcs/pc/piece/units → EA) | Config-driven lookup in normalization.json; apply after generic normalization |
| NORM-03 | Supplier name aliases (SIEMENS* → SIEMENS MOBILITY) | Config-driven lookup with prefix matching |
| NORM-04 | Reference aliases (CTRL-AIR01 → CTRL-AIR-01, CTRL-HVAC-001 → CTRL-AIR-01) | Exact match lookup in config; applied to normalized reference |
| SCEN-C | Typo/alias reconciliation (CTRL-AIR01 → CTRL-AIR-01) | Reference alias in config resolves this; demonstrated end-to-end |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| CSV file ingestion | Backend / CLI | — | File I/O, hash computation, database insertion |
| Schema validation | Backend | — | Row-level validation before database insert |
| Hard validation quarantine | Backend | — | Database insert to quarantine table |
| Soft validation warnings | Backend | — | Database insert to warnings table |
| Deterministic normalization | Backend / Domain | — | Pure functions: string transformation, config lookup |
| Source entity extraction | Backend / Domain | — | Deduplication query + insert |
| Configuration management | Backend | — | JSON file load, validation |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ | Implementation language | D-13: Python as sole implementation language |
| sqlite3 | built-in | Database operations | D-12: SQLite for storage; built-in, no install needed |
| csv | built-in | CSV parsing | Standard library, handles RFC 4180 |
| hashlib | built-in | File hashing (SHA-256) | Standard library, reliable content-addressed storage |
| json | built-in | Config loading | Standard library, normalization config is JSON |
| re | built-in | Regex for normalization | Standard library, pattern-based string transformation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | built-in | Path manipulation | Cross-platform file paths |
| dataclasses | built-in | Data structures | Clean data containers for source records |
| typing | built-in | Type hints | Code clarity, IDE support |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| raw sqlite3 | SQLAlchemy | SQLAlchemy adds dependency + abstraction layer; overkill for this scale |
| csv module | pandas | pandas adds heavy dependency; overkill for simple CSV ingestion |
| custom hashing | hashlib | hashlib is standard, well-tested, no reason to replace |

**Installation:** No external packages required. Python 3.10+ standard library is sufficient.

**Version verification:** Python 3.10+ available via `python3 --version`. sqlite3 built-in. All other libraries are standard library modules.

## Package Legitimacy Audit

> **Required** whenever this phase installs external packages. This phase uses only Python standard library — no external packages to audit.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PHASE 1 PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  data/inputs/*.csv                                               │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐                                                │
│  │ File Discovery│                                               │
│  │ - List CSV files│                                             │
│  │ - Compute SHA-256│                                           │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐        ┌──────────────┐                       │
│  │Source File Reg│──────▶│ source_file  │                       │
│  │ - file_hash   │        │ (file_name,  │                       │
│  │ - source_system│      │  file_hash,  │                       │
│  └──────┬───────┘        │  ingested_at)│                       │
│         │                └──────────────┘                       │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ Schema Valid  │◀─────────────────────────────────────────────│
│  │ - Required cols│                                              │
│  │ - Column count │                                              │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐      ┌──────────────────┐                     │
│  │ Raw Ingestion │─────▶│ plm_bom_line     │                     │
│  │ - Parse rows  │      │ plm_assembly     │                     │
│  │ - Preserve raw│      │ plm_variant      │                     │
│  │ - source_row  │      │ erp_material     │                     │
│  └──────┬───────┘      │ erp_supplier     │                     │
│         │               │ engineering_note │                     │
│         ▼               └──────────────────┘                     │
│  ┌──────────────┐                                                │
│  │ Normalization │◀────────── config/normalization.json          │
│  │ - Whitespace  │                                                │
│  │ - Casing      │                                                │
│  │ - Punctuation │                                                │
│  │ - Alias lookup│                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐      ┌──────────────────┐                     │
│  │ Normalized   │─────▶│ _normalized cols  │                     │
│  │ Values Stored│      │ in source tables  │                     │
│  └──────┬───────┘      └──────────────────┘                     │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐      ┌──────────────────┐                     │
│  │ Source Entity │─────▶│ source_component │                     │
│  │ Extraction    │      │ source_assembly  │                     │
│  │ - Dedup by    │      │ source_supplier  │                     │
│  │   (sys, ref)  │      └──────────────────┘                     │
│  └──────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
app/
├── backend/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point for ingestion commands
│   └── main.py             # FastAPI/Flask app if web UI needed
├── domain/
│   ├── __init__.py
│   ├── models.py           # Data classes for source records
│   ├── normalization.py    # Normalization functions
│   └── config.py           # Config loading
├── services/
│   ├── __init__.py
│   ├── ingestion.py        # CSV ingestion service
│   ├── validation.py       # Hard/soft validation
│   └── source_extraction.py # Source entity deduplication
├── db/
│   ├── __init__.py
│   ├── connection.py       # SQLite connection management
│   └── schema.py           # Schema creation, migrations
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Test fixtures, database setup
│   ├── test_ingestion.py   # Ingestion tests
│   ├── test_normalization.py # Normalization tests
│   └── test_validation.py  # Validation tests
├── config/
│   └── normalization.json  # Normalization aliases config
└── data/
    └── processed/          # Normalized output (if any files)
```

### Pattern 1: File Hash-Based Idempotency

**What:** Use SHA-256 file hash to detect duplicate imports. Same file = skip; changed file = new version.
**When to use:** Every file ingestion operation.
**Example:**

```python
import hashlib
from pathlib import Path

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### Pattern 2: Raw + Normalized Column Pattern

**What:** Every value has a `_raw` column (immutable) and a normalized column (computable).
**When to use:** All source tables with values that undergo normalization.
**Example:** See `docs/blueprint/docs/03_data_model.md` for column definitions — `component_ref_raw` + `component_ref_normalized`.

### Pattern 3: Validation Table Pattern

**What:** Separate tables for quarantine (hard failures) and warnings (soft failures), both linked to source rows.
**When to use:** Any validation that doesn't reject the entire file.
**Example:**

```sql
CREATE TABLE quarantine (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL,
    source_row INTEGER NOT NULL,
    raw_data TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE warnings (
    id INTEGER PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_row_id INTEGER NOT NULL,
    warning_type TEXT NOT NULL,
    warning_message TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
```

### Anti-Patterns to Avoid

- **Anti-pattern: Silent data loss.** Never drop malformed rows without recording them in quarantine.
- **Anti-pattern: Overwriting raw values.** Raw columns are immutable after ingestion.
- **Anti-pattern: Hardcoding aliases in code.** All aliases must be in config/normalization.json.
- **Anti-pattern: Guessing unknown values.** If normalization fails, leave null and emit warning.
- **Anti-pattern: ORM for simple queries.** SQLAlchemy is overkill for this scale; raw SQL is clearer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Custom CSV parser | Python `csv` module | Handles edge cases (quotes, escapes, line endings) |
| File hashing | Custom hash implementation | `hashlib.sha256()` | Cryptographically secure, standard library |
| JSON config parsing | Custom JSON parser | `json.load()` | Standard library, handles all edge cases |
| SQLite connection | Custom connection management | `sqlite3.connect()` | Built-in, connection pooling not needed for PoC |
| Test database setup | Manual SQL in each test | pytest fixtures with in-memory SQLite | Fast, isolated, repeatable |

**Key insight:** The Python standard library is sufficient for this entire phase. No external dependencies needed.

## Common Pitfalls

### Pitfall 1: Line Ending Inconsistency

**What goes wrong:** CSV files from different systems have different line endings (CRLF vs LF). Parser mishandles them.
**Why it happens:** Windows vs Unix line endings; some CSV exports use CRLF.
**How to avoid:** Python's `csv` module handles both; open files with `newline=''` per CSV module docs.
**Warning signs:** Rows with extra blank lines, truncated last column.

### Pitfall 2: Unicode in CSV Files

**What goes wrong:** Non-ASCII characters (e.g., French accents in engineering notes) cause decode errors.
**Why it happens:** Files may be UTF-8, Latin-1, or have BOM markers.
**How to avoid:** Open with `encoding='utf-8'` and handle `UnicodeDecodeError` gracefully; try fallback encodings if needed.
**Warning signs:** `UnicodeDecodeError` during file read.

### Pitfall 3: Quantity Parsing Ambiguity

**What goes wrong:** Quantity field has values like "1,000" (thousands separator) or "1-2" (range) that don't parse as numbers.
**Why it happens:** Real-world data has inconsistent numeric formats.
**How to avoid:** Use strict parsing: `float()` only accepts valid numeric strings. Anything else → hard quarantine.
**Warning signs:** `ValueError` from `float()` on quantity field.

### Pitfall 4: Config File Not Found or Invalid

**What goes wrong:** `config/normalization.json` is missing or has invalid JSON; pipeline crashes.
**Why it happens:** New project, config file not yet created; or manual edit introduced syntax error.
**How to avoid:** Check file existence before loading; validate JSON structure; provide clear error message with expected structure.
**Warning signs:** `FileNotFoundError` or `json.JSONDecodeError`.

### Pitfall 5: Duplicate Source Entity Creation

**What goes wrong:** Same `(source_system, source_reference)` pair inserted multiple times due to re-run or bug.
**Why it happens:** Missing UNIQUE constraint; or upsert logic error.
**How to avoid:** Add UNIQUE constraint on `(source_system, source_reference)`; use INSERT OR IGNORE or explicit upsert.
**Warning signs:** Duplicate rows in source_component/source_assembly/source_supplier.

## Code Examples

### CSV Ingestion with Provenance

```python
import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Any

def ingest_csv(
    file_path: Path,
    source_system: str,
    db_connection,
    source_file_id: int
) -> Dict[str, Any]:
    """
    Ingest a CSV file into the appropriate source table.
    Returns stats: row_count, quarantined_count, warnings_count.
    """
    stats = {"row_count": 0, "quarantined": 0, "warnings": 0}
    file_hash = compute_file_hash(file_path)
    
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for source_row, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            stats["row_count"] += 1
            
            # Schema validation
            if not validate_row(row, source_system):
                quarantine_row(db_connection, source_file_id, source_row, row, "Schema validation failed")
                stats["quarantined"] += 1
                continue
            
            # Hard validation
            hard_failure = check_hard_validation(row, source_system)
            if hard_failure:
                quarantine_row(db_connection, source_file_id, source_row, row, hard_failure)
                stats["quarantined"] += 1
                continue
            
            # Soft validation
            soft_warnings = check_soft_validation(row, source_system)
            for warning in soft_warnings:
                add_warning(db_connection, source_system, source_row, warning)
                stats["warnings"] += 1
            
            # Insert raw row
            insert_raw_row(db_connection, source_file_id, source_row, row, source_system)
    
    return stats
```

### Normalization Function

```python
import re
from typing import Optional

def normalize_reference(raw: str, alias_config: dict) -> str:
    """
    Apply deterministic normalization to a reference identifier.
    Order: generic rules first, then alias lookup.
    """
    if not raw:
        return raw
    
    # Step 1: Generic normalization
    normalized = raw.strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
    normalized = normalized.upper()  # Casing standardization for identifiers
    normalized = re.sub(r'[-_]+', '-', normalized)  # Punctuation harmonization
    
    # Step 2: Alias lookup (exact match on normalized value)
    if normalized in alias_config.get('reference_aliases', {}):
        return alias_config['reference_aliases'][normalized]
    
    return normalized

def normalize_uom(raw: str, alias_config: dict) -> Optional[str]:
    """Normalize unit of measure."""
    if not raw:
        return None
    
    normalized = raw.strip().lower()
    if normalized in alias_config.get('uom_aliases', {}):
        return alias_config['uom_aliases'][normalized]
    return normalized

def normalize_supplier(raw: str, alias_config: dict) -> Optional[str]:
    """Normalize supplier name with prefix matching."""
    if not raw:
        return None
    
    normalized = raw.strip()
    # Try exact match first
    if normalized in alias_config.get('supplier_aliases', {}):
        return alias_config['supplier_aliases'][normalized]
    
    # Try prefix matching (e.g., "SIEMENS MOBILITY GMBH" -> "SIEMENS MOBILITY")
    for alias, canonical in alias_config.get('supplier_aliases', {}).items():
        if normalized.upper().startswith(alias.upper()):
            return canonical
    
    return normalized
```

### Source Entity Deduplication

```python
def extract_source_entities(db_connection, source_system: str) -> Dict[str, int]:
    """
    Extract distinct source entities from raw tables.
    Returns mapping of (source_reference) -> entity_id.
    """
    entities = {}
    
    # Example for components from PLM BOM lines
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT DISTINCT component_ref_normalized
        FROM plm_bom_line
        WHERE component_ref_normalized IS NOT NULL
        AND source_file_id IN (
            SELECT id FROM source_file WHERE source_system = ?
        )
    """, (source_system,))
    
    for (ref,) in cursor.fetchall():
        if ref and ref not in entities:
            cursor.execute("""
                INSERT OR IGNORE INTO source_component 
                (source_system, source_reference, normalized_reference)
                VALUES (?, ?, ?)
            """, (source_system, ref, ref))
            
            cursor.execute("SELECT id FROM source_component WHERE source_reference = ?", (ref,))
            row = cursor.fetchone()
            if row:
                entities[ref] = row[0]
    
    return entities
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.10+ is available on the target system | Standard Stack | If Python 3.9 or earlier, some type hint syntax may not work |
| A2 | CSV files are UTF-8 encoded | Code Examples | If files are Latin-1, need encoding fallback |
| A3 | File hash (SHA-256) is sufficient for idempotency | Architectural Patterns | For PoC scale, SHA-256 is definitive; no known collisions |
| A4 | SQLite is sufficient for dataset scale (6 CSVs, ~200-300 BOM lines) | Standard Stack | Dataset is small; SQLite handles millions of rows easily |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **Web framework choice for Phase 1:** Should we include a simple web API (FastAPI/Flask) for the data explorer, or is CLI + SQLite + report output sufficient for Phase 1? The CONTEXT.md marks this as Claude's Discretion.

2. **ORM decision:** SQLAlchemy adds ~100KB dependency and abstraction layer. For this PoC scale with 6 simple tables, raw sqlite3 is clearer. Should we use raw SQLite for Phase 1 and potentially add SQLAlchemy later if complexity grows?

3. **Migration approach:** Single `init_db.py` script that creates all tables from scratch, or versioned migrations (e.g., alembic)? For PoC with SQLite and no production deployment, single init script is simpler.

4. **Test database strategy:** In-memory SQLite for tests (fast, isolated) vs file-based test database (closer to production behavior)?

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.10+ | All code | ✓ (assumed) | 3.x | — |
| sqlite3 | Database operations | ✓ (built-in) | — | — |
| csv module | CSV parsing | ✓ (built-in) | — | — |
| hashlib | File hashing | ✓ (built-in) | — | — |
| json | Config loading | ✓ (built-in) | — | — |
| config/normalization.json | Normalization | ✗ (needs creation) | — | Create from normalization.example.json |

**Missing dependencies with no fallback:** None — all required functionality is in Python standard library.

**Missing dependencies with fallback:** config/normalization.json — copy from docs/blueprint/config/normalization.example.json and customize.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml or pytest.ini (create in Phase 1) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INGEST-01 | All 6 files ingest with provenance | integration | `pytest tests/test_ingestion.py::test_ingest_all_files` | ❌ Wave 0 |
| INGEST-02 | Malformed rows quarantined | unit | `pytest tests/test_validation.py::test_hard_validation_quarantine` | ❌ Wave 0 |
| INGEST-03 | Soft warnings emitted | unit | `pytest tests/test_validation.py::test_soft_validation_warnings` | ❌ Wave 0 |
| NORM-01 | BOM lines normalized (whitespace/casing) | unit | `pytest tests/test_normalization.py::test_normalize_bom_lines` | ❌ Wave 0 |
| NORM-02 | UOM aliases applied | unit | `pytest tests/test_normalization.py::test_uom_aliases` | ❌ Wave 0 |
| NORM-03 | Supplier aliases applied | unit | `pytest tests/test_normalization.py::test_supplier_aliases` | ❌ Wave 0 |
| NORM-04 | Reference aliases applied | unit | `pytest tests/test_normalization.py::test_reference_aliases` | ❌ Wave 0 |
| SCEN-C | CTRL-AIR01 normalizes to CTRL-AIR-01 | integration | `pytest tests/test_scenarios.py::test_scenario_c` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q` (stop on first failure, quiet output)
- **Per wave merge:** `pytest tests/ -v` (verbose, full output)
- **Phase gate:** Full suite green before marking Phase 1 complete

### Wave 0 Gaps

- [ ] `tests/conftest.py` — shared fixtures (database setup, sample data)
- [ ] `tests/test_ingestion.py` — ingestion tests for all 6 file types
- [ ] `tests/test_normalization.py` — normalization tests for each alias type
- [ ] `tests/test_validation.py` — hard and soft validation tests
- [ ] `tests/test_scenarios.py` — scenario-specific tests (SCEN-C)
- [ ] `pyproject.toml` or `pytest.ini` — pytest configuration

## Sources

### Primary (HIGH confidence)

- `docs/blueprint/docs/03_data_model.md` — Complete ER schema specification (verified this session)
- `docs/blueprint/docs/04_ingestion_and_normalization.md` — Pipeline stages, validation levels, normalization principles (verified this session)
- `docs/blueprint/config/normalization.example.json` — Example normalization config structure (verified this session)
- `data/inputs/plm/bom_export.csv` — Sample BOM data (verified this session)
- `data/inputs/plm/assembly_master.csv` — Sample assembly data (verified this session)
- `data/inputs/plm/variant_configuration.csv` — Sample variant data (verified this session)
- `data/inputs/erp/material_master.csv` — Sample ERP material data (verified this session)
- `data/inputs/erp/supplier_master.csv` — Sample supplier data (verified this session)
- `data/inputs/engineering/technical_notes.csv` — Sample engineering notes (verified this session)

### Secondary (MEDIUM confidence)

- Python csv module documentation — standard library, well-established behavior
- Python sqlite3 module documentation — standard library, well-established behavior

### Tertiary (LOW confidence)

- None — all claims either verified against in-repo files or based on standard library behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python standard library is sufficient; no external packages needed
- Architecture: HIGH — Schema is specified in 03_data_model.md; patterns are standard
- Pitfalls: HIGH — Common CSV/SQLite pitfalls documented; config-driven approach reduces risk

**Research date:** 2026-09-22
**Valid until:** 2026-10-22 (30 days for stable technology choices)
