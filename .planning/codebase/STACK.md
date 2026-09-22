---
last_mapped_commit: 92a308bb4f3975a737c94509b667c651a00285ba
last_mapped_at: 2026-09-22
---
# Cognyx — Technology Stack

**Analysis Date:** 2026-09-22

<!-- refreshed: 2026-09-22 -->

## Languages & Runtime

| Layer | Language | Runtime |
|---|---|---|
| Backend / Worker | Python | CPython 3.x (unspecified minor) |
| UI | Not yet built (planned: React/TypeScript per blueprint) | — |
| Data format | CSV (source), JSON (config, evidence) | — |

**Python is the sole implementation language.** No TypeScript, Go, Rust, or other languages are present in the repository.

## Frameworks & Libraries

No `requirements.txt`, `pyproject.toml`, `setup.py`, or other dependency manifest exists in the repository. The project is in the **blueprint/planning phase**, not yet implemented.

From the architecture blueprint (`docs/blueprint/README.md`, `docs/blueprint/docs/02_architecture.md`):

| Concern | Planned Choice | Notes |
|---|---|---|
| Database | SQLite | PoC-scale; migration path to PostgreSQL noted in `docs/blueprint/docs/12_production_evolution.md` |
| LLM Provider | One well-defined provider abstraction | Not yet implemented; the blueprint says "LLM is called through one well-defined provider abstraction" — no specific provider chosen |
| Web UI | Small web app (React/TypeScript implied) | Not yet built; `docs/blueprint/docs/07_ui_specification.md` specifies screens but no framework |
| CSV parsing | Standard library or lightweight library | Expected for ingestion |

## Package Management

No package manager configuration is present. The project does not yet have:

- `pyproject.toml` / `setup.py` / `requirements.txt`
- `Pipfile` / `poetry.lock` / `uv.lock`
- `Dockerfile` / `docker-compose.yml`
- `Makefile`

## Configuration

Configuration files present:

| File | Purpose |
|---|---|
| `docs/blueprint/config/normalization.example.json` | Example normalization rules: UOM aliases, supplier aliases, reference aliases, voltage aliases |

No environment configuration (`.env`, `config.yaml`, etc.) exists. `.gitignore` only excludes `.hermes`.

## Project Structure (Planned)

From `docs/blueprint/README.md` and `docs/blueprint/docs/11_execution_roadmap.md`:

```
app/
  backend/        # API services
  worker/         # Reconciliation worker
  frontend/       # UI (not built)
  domain/         # Domain models
  services/       # Application services
  db/             # Database / migrations
  tests/
config/
data/
  raw/
docs/
```

**Actual current structure** (pre-implementation):

```
.
├── data/
│   ├── inputs/          # Immutable raw CSV fixtures
│   ├── ground_truth/    # Testing fixtures (not client-facing)
│   └── README.md
├── docs/
│   ├── scenarios.md
│   └── blueprint/       # Full implementation specification
├── .hermes/             # Hermes Agent runtime + GSD
├── .planning/codebase/  # This analysis output
├── AGENTS.md
├── README.md
└── dataset_summary.json
```

No `src/`, `app/`, or `tests/` directories exist yet.

## Build & Run

No build system, no entry points, no CLI. The repository currently contains **specification documents and synthetic test data only**. There is no runnable code.

## Python Version

Not pinned. The blueprint does not specify a minimum version. Python 3.x assumed.

## Data

Source data is synthetic, provided as CSV files in `data/inputs/`:

| System | Files | Rows (approx.) |
|---|---|---|
| PLM | `bom_export.csv`, `assembly_master.csv`, `variant_configuration.csv` | 138 BOM rows, 45 assemblies, 5 variants |
| ERP | `material_master.csv`, `supplier_master.csv` | 44 materials, 6 suppliers |
| Engineering | `technical_notes.csv` | 71 notes |

See `dataset_summary.json` for exact counts.
