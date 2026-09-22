# Cognyx — Alstom x Cognyx FDE Case

Working material for the Alstom x Cognyx Forward Deployed Engineer case: a 3-week pilot at Alstom's Valenciennes site (regional trains) to help engineering teams reuse existing sub-assemblies across train variants instead of re-designing from scratch at every tender.

## Case format

- **Deliverable**: 1 email + 1 in-person meeting (1h: 40min case + 20min Q&A)
- **Audience**: Bruno Maréchal (Engineering Director, pilot sponsor) and Thomas Lindqvist (lead data engineer) — in role for the demo segment; Cognyx team out-of-role for repo/AI-setup segments
- **Preparation timebox**: ~4 hours max — extract maximum value within a tight timebox using AI-assisted coding tools (Claude Code, Codex, Cursor…)
- **Email recipients**: deon@cognyx.io and francois@cognyx.io

## What to build

A small working tool that:

1. Ingests the pilot data (the synthetic dataset in this repo)
2. Normalizes it into a simple entity model (components, sub-assemblies, variants, suppliers)
3. Answers: **"which sub-assemblies are reused — or reusable — across variants, and where are the inconsistencies?"**

Format is free: CLI + report, small web app, agent. Deliver a git repo with a short README and **the trace of how you worked with AI** (commit history, prompts, CLAUDE.md, skills…).

## Repository structure (suggested, not frozen)

```
.
├── README.md                          # this file + case statement
├── AGENTS.md / CLAUDE.md              # AI coding instructions
├── docs/
│   ├── scenarios.md                   # the 10 engineered scenarios (A–J)
│   ├── architecture.md                # (future) architecture decisions
│   └── ai-worklog.md                 # (future) AI-assisted development trace
├── data/
│   ├── inputs/                        # raw client exports — IMMUTABLE
│   ├── processed/                     # normalized/canonical output
│   └── ground_truth/                  # testing only — NOT client-facing
├── src/
│   ├── ingestion/
│   ├── normalization/
│   ├── reconciliation/
│   ├── analysis/
│   └── ui/
└── tests/
```

## Data layout

```
data/inputs/
├── plm/
│   ├── bom_export.csv         # multi-variant BOM lines (parent/child, qty, units, descriptions, supplier text)
│   ├── assembly_master.csv    # variant-specific PLM assembly references + metadata
│   └── variant_configuration.csv  # 5 train variants + characteristics
├── erp/
│   ├── material_master.csv    # material IDs, descriptions, supplier IDs, units, categories, lifecycle status, costs
│   └── supplier_master.csv    # supplier master records
└── engineering/
    └── technical_notes.csv    # free-text notes (FR/EN) — equivalences, constraints, legacy refs, qualification notes
```

## Core modeling rules

**Three relationship types must stay separate** — never collapse into a single "match" concept:

1. **Identity/alias** — two source IDs refer to the same canonical entity (e.g. `CTRL-AIR-01` vs `CTRL-AIR01`)
2. **Functional similarity/potential substitution** — different entities, possibly interchangeable in context
3. **Variant-specific specialization** — intentional variant-specific component choice (e.g. Nordic cold-rated parts)

Reconciliation is modeled as a **reviewable, provenance-bearing relationship**, not a silent overwrite:

```
raw source record → candidate canonical entity → pending/accepted/rejected
```

Each reconciliation records: source system, raw ID, canonical ID, status, match method, confidence, rationale, evidence.

## Intended pipeline flow

```
Raw PLM / ERP / Engineering data
        ↓
Validation + normalization
        ↓
Entity resolution / reconciliation
        ↓
Canonical engineering model
        ↓
Cross-variant reuse analysis
        ↓
Evidence + inconsistencies + review workflow
```

## Key scenarios (see docs/scenarios.md for full detail)

| ID | Focus |
|----|-------|
| A  | Obvious cross-variant reuse |
| B  | Hidden cross-source reuse (same entity, different PLM/ERP/note IDs) |
| C  | Typo/alias reconciliation |
| D  | Similar-but-not-identical (must not merge) |
| E  | Variant-specific intentional differences |
| F  | Potential reuse requiring review |
| G  | Conflicting evidence — surface, don't normalize |
| H  | Multilingual evidence (FR/EN/DE) |
| I  | Data-quality issues (units, duplicate BOM lines, invalid quantity) |
| J  | Lifecycle mismatch as separate issue |

## Client-facing questions the tool should answer

- **Already reused**: which sub-assemblies/components are shared across variants?
- **Reusable candidates**: which different-looking assemblies are close enough to investigate?
- **Blockers**: where do specs, lifecycle state, or evidence prevent safe reuse?
- **Data-quality issues**: which references, suppliers, units, quantities, or attributes are inconsistent?
- **Explainability**: why did the system consider two records equivalent, similar, or conflicting?

## Scope discipline

The ~4-hour timebox means prioritize:

- working end-to-end ingestion path
- clear canonical entity model
- reviewable reconciliation mechanism
- useful cross-variant reuse analysis
- visible evidence/provenance
- concise, maintainable codebase
- trace of AI-assisted development

**Not required for PoC**: production auth, distributed/graph database, complex multi-agent framework, full deployment automation, OCR/PDF extraction, general-purpose chatbot.

## Rules

- **Do not edit `data/inputs/`** — immutable test fixture, intentionally messy
- **Do not expose `data/ground_truth/` in client/demo output** — exists only for pipeline validation
- Write normalized output to `data/processed/` (or equivalent), separate from source data
- Git history, prompts, coding instructions, and AI-worklog are part of the deliverable
