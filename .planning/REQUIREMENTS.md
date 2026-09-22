# Requirements: Cognyx BOM Reuse Explorer (PoC)

**Defined:** 2026-09-22
**Core Value:** Surface which sub-assemblies are reused — or reusable — across train variants, and where the data has inconsistencies that block safe reuse, in a reviewable way that engineers trust.

## v1 Requirements

Requirements for initial PoC release. Each maps to roadmap phases.

### Ingestion

- [ ] **INGEST-01**: Ingest all 6 source CSV files (PLM BOM export, PLM assembly master, PLM variant configuration, ERP material master, ERP supplier master, engineering technical notes) into source tables with file hash, source row number, and raw column preservation
- [ ] **INGEST-02**: Hard validation rejects/quarantines structurally malformed rows (wrong column count, unparseable numbers)
- [ ] **INGEST-03**: Soft validation keeps rows but emits warnings (missing description, unknown UOM, empty supplier)

### Normalization

- [ ] **NORM-01**: Normalize PLM BOM lines: whitespace collapse, casing standardization for identifiers, punctuation harmonization
- [ ] **NORM-02**: Apply UOM aliases (e.g. `pcs` → `EA`, `units` → `EA`)
- [ ] **NORM-03**: Apply supplier name aliases (e.g. `SIEMENS` → `SIEMENS MOBILITY`)
- [ ] **NORM-04**: Apply reference aliases (e.g. `CTRL-AIR01` → `CTRL-AIR-01`)
- [ ] **NORM-05**: Normalize ERP materials: supplier ID mapping, UOM standardization
- [ ] **NORM-06**: Normalize engineering notes: language detection (FR/EN/DE), text extraction for evidence

### Reconciliation

- [ ] **RECON-01**: Perform entity resolution: detect identity/alias relationships (same entity, different source IDs) with confidence scoring and match method recording
- [ ] **RECON-02**: Detect functional similarity candidates (different entities, possibly interchangeable in context) without merging — surface for review
- [ ] **RECON-03**: Detect variant-specific intentional differences (e.g. Nordic cold-rated parts) and exclude from generic reuse suggestions
- [ ] **RECON-04**: Each reconciliation record includes: source system, raw ID, canonical ID, status (pending/accepted/rejected), match method, confidence, rationale, evidence

### Review Workflow

- [ ] **REVIEW-01**: Human-in-the-loop review interface: accept/reject/redirect reconciliation proposals with optional rationale
- [ ] **REVIEW-02**: Pending reconciliations are visible and filterable by confidence, match method, source system
- [ ] **REVIEW-03**: Accepted reconciliations propagate to canonical model; rejected ones are recorded with rejection reason

### Cross-Variant Reuse Analysis

- [ ] **ANALYSIS-01**: Generate "already reused" report: which sub-assemblies/components are shared across variants (based on accepted canonical model)
- [ ] **ANALYSIS-02**: Generate "reusable candidates" report: different-looking assemblies that are close enough to investigate (functional similarity + context)
- [ ] **ANALYSIS-03**: Generate "blockers" report: where specs, lifecycle state, or evidence prevent safe reuse
- [ ] **ANALYSIS-04**: Generate "data-quality issues" report: inconsistent references, suppliers, units, quantities, attributes
- [ ] **ANALYSIS-05**: Each analysis result includes explainability: why the system considered two records equivalent, similar, or conflicting

### Scenario Coverage

- [ ] **SCEN-A**: Obvious cross-variant reuse — same sub-assembly appears in multiple variant BOMs → surfaced as "already reused"
- [ ] **SCEN-B**: Hidden cross-source reuse — same entity has different PLM/ERP/note IDs → reconciled via entity resolution
- [ ] **SCEN-C**: Typo/alias reconciliation — minor variations (CTRL-AIR-01 vs CTRL-AIR01) → normalized and reconciled
- [ ] **SCEN-D**: Similar-but-not-identical — different entities that look alike but are not interchangeable → NOT merged, flagged for review
- [ ] **SCEN-E**: Variant-specific intentional differences — e.g. Nordic cold-rated parts → detected and excluded from generic reuse
- [ ] **SCEN-F**: Potential reuse requiring review — functional similarity candidates surfaced with evidence
- [ ] **SCEN-G**: Conflicting evidence — surface, don't normalize away (e.g. one source says qualified, another says not)
- [ ] **SCEN-H**: Multilingual evidence — FR/EN/DE technical notes used as reconciliation context
- [ ] **SCEN-I**: Data-quality issues — units, duplicate BOM lines, invalid quantities detected and reported
- [ ] **SCEN-J**: Lifecycle mismatch — components with different lifecycle states across sources → reported as separate issue

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Web UI

- **UI-01**: React/TypeScript web UI for reconciliation review (planned per blueprint, not in PoC scope)
- **UI-02**: Interactive cross-variant comparison view
- **UI-03**: Export analysis reports to PDF/Excel for client meeting

### Production Evolution

- **PROD-01**: Migration from SQLite to PostgreSQL (noted in production evolution doc)
- **PROD-02**: Authentication and user management
- **PROD-03**: Multi-user review workflow with assignment and tracking

### Advanced Reconciliation

- **ADV-01**: LLM-assisted reconciliation proposals (beyond rule-based matching)
- **ADV-02**: Automated confidence calibration based on review outcomes

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Production auth / user management | PoC scope; production evolution path noted but not implemented |
| Distributed / graph database | SQLite sufficient for PoC scale; PostgreSQL migration noted for production |
| Complex multi-agent framework | Single pipeline with human review, not autonomous agent swarm |
| Full deployment automation | PoC is a working tool, not a deployed service |
| OCR / PDF extraction | Source data is CSV, no document extraction needed |
| General-purpose chatbot | Focused engineering workbench, not a conversational AI |
| Client-facing ground truth exposure | `data/ground_truth/` exists for pipeline validation only — never shown to client |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

|| Requirement | Phase | Status |
|-------------|-------|--------|
|| INGEST-01 | Phase 1 | Pending |
|| INGEST-02 | Phase 1 | Pending |
|| INGEST-03 | Phase 1 | Pending |
|| NORM-01 | Phase 1 | Pending |
|| NORM-02 | Phase 1 | Pending |
|| NORM-03 | Phase 1 | Pending |
|| NORM-04 | Phase 1 | Pending |
|| NORM-05 | Phase 2 | Pending |
|| NORM-06 | Phase 2 | Pending |
|| RECON-01 | Phase 2 | Pending |
|| RECON-02 | Phase 2 | Pending |
|| RECON-03 | Phase 2 | Pending |
|| RECON-04 | Phase 2 | Pending |
|| REVIEW-01 | Phase 3 | Pending |
|| REVIEW-02 | Phase 3 | Pending |
|| REVIEW-03 | Phase 3 | Pending |
|| ANALYSIS-01 | Phase 3 | Pending |
|| ANALYSIS-02 | Phase 3 | Pending |
|| ANALYSIS-03 | Phase 3 | Pending |
|| ANALYSIS-04 | Phase 3 | Pending |
|| ANALYSIS-05 | Phase 3 | Pending |
|| SCEN-A | Phase 3 | Pending |
|| SCEN-B | Phase 2 | Pending |
|| SCEN-C | Phase 1 | Pending |
|| SCEN-D | Phase 2 | Pending |
|| SCEN-E | Phase 2 | Pending |
|| SCEN-F | Phase 3 | Pending |
|| SCEN-G | Phase 3 | Pending |
|| SCEN-H | Phase 2 | Pending |
|| SCEN-I | Phase 3 | Pending |
|| SCEN-J | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓
- Phase 1: 8 requirements (INGEST-01–03, NORM-01–04, SCEN-C)
- Phase 2: 10 requirements (NORM-05–06, RECON-01–04, SCEN-B, D, E, H)
- Phase 3: 13 requirements (REVIEW-01–03, ANALYSIS-01–05, SCEN-A, F, G, I, J)
- Phase 4: 0 new requirements — deepens ANALYSIS-01–04 from Phase 3
- Phase 5: 0 new requirements — deepens SCEN-G, H, I, J and ANALYSIS-05 from Phase 3

**Phase summary:**
| Phase | Name | Requirements | Success Criteria |
|-------|------|-------------|-----------------|
| 1 | Data Foundation: Ingest & Normalize | 8 | 6 |
| 2 | Entity Resolution & Reconciliation Engine | 10 | 5 |
| 3 | Human Review Workflow + Core Analysis | 13 | 6 |
| 4 | Cross-Variant Reuse Analysis — Deep Reports | (deepens Phase 3) | 4 |
| 5 | Explainability, Edge Cases & Final Scenario Coverage | (deepens Phase 3) | 5 |

**Total success criteria: 26**

---

*Requirements defined: 2026-09-22*
*Last updated: 2026-09-22 after initial definition*
