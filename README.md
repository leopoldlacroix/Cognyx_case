# 📝 Case Statement — Alstom x Cognyx — FDE

> This repository contains the working material for the Alstom x Cognyx FDE case. The first part of this README reproduces the case statement; the remainder documents the interpretation, synthetic dataset, intended architecture, and working assumptions for the implementation.

---

## Case Statement

### Foreword

*This case (inspired by real events…) was designed to simulate a work situation close to our world, as part of a role-play representative of our projects. You are free to produce or use any presentation material, in the format of your choice, or to lead the conversation freely if that feels more appropriate.*

*For the purposes of this fictional exercise, feel free to invent any plausible figure, metric or detail about Cognyx or the client.*

*The deliverable will take the form of 1 email and 1 in-person meeting, generally in English, lasting 1 hour (40 minutes on the case, 20 minutes of questions about the Role and Cognyx). Cognyx team members will play the roles of the stakeholders mentioned below.*

*One precision on the format: the demo segment is a role-played client meeting — treat us strictly as Bruno and Thomas. The shipped-work and repo/AI-setup segments are with Cognyx, out of role. We will announce each switch.*

> 💡 *This case includes home preparation, part of which is something to build (unapologetic “vibe coding”). We recommend spending no more than 4 hours on it: the exercise is precisely about extracting maximum value within a tight timebox, using the AI-assisted coding tools of your choice (Claude Code, Codex, Cursor…). An imperfect but working, well-prioritized result beats a theoretically “complete” one.*

### Context

You are a **Forward Deployed Engineer at Cognyx**. Alstom is starting a **3-week pilot** of the Cognyx platform at its Valenciennes site (regional trains). The pilot scope: help engineering teams **reuse existing sub-assemblies across train variants** instead of re-designing (and re-costing) from scratch at every tender.

The client's data team has sent you an “as-is” export from their PLM/ERP environment: a **multi-variant Bill of Materials (BOM) CSV** and **free-text technical notes** about components. Kaïs, a Cognyx Deployment Strategist, owns the client relationship; you are the technical firepower of the pilot.

Next week's session with the client must demonstrate, with proof, that Cognyx can make sense of their real data.

### What the situation doesn't tell you…

- The data is dirtier than advertised: duplicated references with typos, mixed units, free-text fields switching between French and English.
- The site's lead data engineer is demanding about the quality and maintainability of what gets shipped — including when it's written with AI.
- The pilot sponsor will have very little time and expects a value story, not a technical demo.
- Eventually, nothing will be allowed to leave Alstom's network: the “how would you deploy this for real” question will come.
- A 3-week pilot is short: not everything can be done — you will have to choose.

### Your objectives

**Before the session — two preparations:**

1. **What you've already shipped.** Pick **1-2 concrete things** you have actually built and delivered: a repo (personal or professional, showable), a portfolio project, an automation or agent that ran in production, and/or your **AI-assisted coding setup** (CLAUDE.md, skills, agents, workflows…). Be ready to screen-share them and discuss: the problem, your choices, what broke, what's still running, what you would do differently.
2. **The build.** Using the AI tools of your choice, build a **small working tool** that:
   - ingests the pilot data — *generate your own plausible synthetic dataset* (multi-variant BOM + free-text notes);
   - normalizes it into a **simple entity model** (components, sub-assemblies, variants, suppliers… up to you);
   - can answer the client's question: **“which sub-assemblies are reused — or reusable — across variants, and where are the inconsistencies?”**

   Format is free: CLI + report, small web app, agent… Deliver a **git repo** (send the link with your email) with a short README and, above all, **the trace of how you worked with AI** (commit history, prompts, CLAUDE.md, skills…).
3. **1 email**: before the session, send **deon@cognyx.io** and **francois@cognyx.io** (playing Bruno Maréchal, the site's Engineering Director, and Thomas Lindqvist, its lead data engineer) a short email: what you built, what it demonstrates for the pilot, and what would be missing to go to production. Include the link to your repo.

**During the session (40 min + 20 min Q&A):**

- **Segment 1 — with Cognyx, out of role (10 min):** walkthrough of what you've already shipped.
- **Segment 2 — the client meeting, in role (≈ 20 min):** we are strictly Bruno and Thomas. Your email is on the table; demo your tool to them.
- **Segment 3 — with Cognyx, out of role (≈ 10 min):** guided tour of your repo and AI-assisted setup.
- **Q&A (20 min), out of role:** your questions about the role and Cognyx.

### Additional context on the stakeholders

- **Thomas Lindqvist — the site's lead data engineer.** Technically excellent, knows the data inside out, scrutinizes the quality and maintainability of anything that gets shipped.
- **Bruno Maréchal — the site's Engineering Director, pilot sponsor.** Secured the pilot budget, expects demonstrable results; short on time, allergic to jargon.

Good luck! 🚀

---

# Project Interpretation & Implementation Notes

## 1. Goal of the PoC

The working interpretation of the case is:

> **Take messy multi-source engineering data, build a traceable canonical representation, and identify sub-assemblies that are already reused, potentially reusable, or blocked by inconsistencies across train variants.**

The PoC should demonstrate engineering judgment rather than maximize technical complexity.

The intended value flow is:

```text
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

A central design principle is:

> **AI can propose/extract; business-critical conclusions remain auditable and, where possible, deterministic.**

## 2. Why multiple source files?

The pilot is modeled as several complementary exports rather than one perfect database extract.

- **PLM** answers mainly: *what is assembled into what, for which variant?*
- **ERP** answers mainly: *what are the materials/suppliers and their operational master-data attributes?*
- **Engineering notes** contain information that is difficult to represent structurally: equivalences, constraints, legacy references, qualification notes, and caveats.

The sources intentionally use different identifiers and schemas. The same real-world object may therefore appear with several references.

## 3. Raw data is immutable

Everything under `data/inputs/` represents what was supplied by the fictional client.

It should **not be modified during processing**.

Our interpreted/normalized representation belongs in a separate area such as:

```text
data/
├── inputs/        # raw client exports — immutable
├── processed/     # our normalized/canonical representation
└── ground_truth/  # synthetic truth used to test the pipeline
```

This separation lets us preserve provenance and makes it possible to explain exactly how a canonical entity was derived.

## 4. Entity resolution / reconciliation

The case intentionally contains situations such as:

```text
PLM:
    CTRL-AIR-01
    CTRL-AIR01
    CTRL-AIR-O1

Engineering note:
    CTRL-HVAC-001

ERP:
    MAT-10001
```

These may refer to one canonical component, but the application should not silently overwrite the raw values.

Instead, reconciliation is modeled as a separate, reviewable relationship:

```text
raw source record
       ↓
candidate canonical entity
       ↓
pending / accepted / rejected
```

Each reconciliation should retain provenance such as:

- source system
- raw reference / raw ID
- canonical entity
- status
- method
- confidence (when appropriate)
- rationale
- supporting evidence / source references

A mapping table is therefore preferable to a simple grouped-name JSON object.

Conceptually:

```text
resolution_id
entity_type
source_system
raw_id / raw_value
canonical_id
status
match_method
confidence
rationale
evidence
```

The later UI should allow a reviewer to:

- inspect why a match was proposed;
- accept it;
- reject/unlink it;
- redirect it to another canonical entity.

## 5. Important relationship distinctions

The model must distinguish at least these concepts:

### Identity / alias

Two source records refer to the **same entity**.

```text
CTRL-AIR-01
CTRL-AIR01
```

### Functional similarity / potential substitution

Two entities are **different**, but one may potentially substitute for the other in a particular context.

```text
standard fan
cold-rated fan
```

### Variant-specific specialization

Two variants intentionally use different engineering solutions.

```text
standard temperature sensor
Nordic temperature sensor
```

A similarity score must not automatically turn these into one canonical entity.

## 6. Intended client-facing questions

The prototype should ultimately help answer:

### Already reused

> Which sub-assemblies/components are already shared across several variants?

### Reusable candidates

> Which different-looking assemblies appear structurally or technically close enough to investigate for reuse?

### Blockers

> Where do technical specifications, lifecycle state, or other evidence prevent safe reuse?

### Data-quality issues

> Which references, suppliers, units, quantities, or attributes are inconsistent or ambiguous?

### Explainability

> Why did the system consider these two records equivalent, similar, or conflicting?

---

# Synthetic Dataset

## Source layout

```text
data/
└── inputs/
    ├── plm/
    │   ├── bom_export.csv
    │   ├── assembly_master.csv
    │   └── variant_configuration.csv
    │
    ├── erp/
    │   ├── material_master.csv
    │   └── supplier_master.csv
    │
    └── engineering/
        └── technical_notes.csv
```

### PLM

`plm/bom_export.csv`

Multi-variant BOM lines containing parent/child relationships, quantities, units, descriptions, and supplier text.

`plm/assembly_master.csv`

Variant-specific PLM assembly references and metadata.

`plm/variant_configuration.csv`

The five fictional train variants and their contextual characteristics.

### ERP

`erp/material_master.csv`

Material IDs, descriptions, supplier IDs, units, categories, lifecycle status and costs.

`erp/supplier_master.csv`

Supplier master records.

### Engineering

`engineering/technical_notes.csv`

Free-text notes in French and English containing equivalence statements, qualification constraints, legacy references, and other engineering context.

No PDF/DOC/OCR layer is intentionally included: document extraction is not the focus of this exercise. Complexity is introduced through the **data relationships and inconsistencies**, not through unnecessary file-format complexity.

## Dataset size

The current synthetic export contains:

- **5 train variants**
- **9 canonical sub-assemblies**
- **40 canonical components**
- **138 PLM BOM rows**
- **45 PLM assembly records**
- **44 ERP material records**
- **6 suppliers**
- **71 engineering notes**

The data is deliberately constructed to feel larger than a hand-made toy example while keeping the demo manageable.

## Core engineering scenarios

| ID | Scenario | What it should demonstrate |
|---|---|---|
| A | Obvious reuse | The same sub-assembly/component appears across multiple variants |
| B | Hidden cross-source reuse | PLM, ERP and engineering notes refer to the same physical entity using different identifiers |
| C | Typo / alias reconciliation | References such as `CTRL-AIR01` / `CTRL-AIR-O1` can become reviewable reconciliation candidates |
| D | Similar but not identical | A 48V export door controller must not be merged with a 24V standard controller merely because their function is similar |
| E | Variant-specific engineering difference | Nordic variants intentionally use cold-rated parts and should not be treated as duplicates |
| F | Potential reuse | Rugged and standard components share architecture/function but differ in qualification |
| G | Conflicting source/specification | Conflicting technical evidence must be surfaced rather than silently normalized |
| H | Multilingual evidence | French and English notes/descriptions describe overlapping entities |
| I | Data-quality issues | Unit inconsistencies, duplicate BOM lines, and invalid quantity values can be surfaced independently of entity resolution |
| J | Lifecycle mismatch | PLM/ERP status differences can appear as a separate operational/data-quality issue |

## Ground truth

The `data/ground_truth/` directory contains information used internally to validate the future ingestion/reconciliation pipeline:

```text
ground_truth/
├── canonical_components.csv
├── canonical_bom_structure.csv
├── variant_component_truth.csv
├── expected_reconciliations.csv
└── expected_conflicts.csv
```

This is **not intended to represent a real Alstom export** and should not be part of the client-facing ingestion path. It is there so that the implementation can be tested against known expected relationships while we develop it.

---

# Intended Demo Story

The eventual client-facing prototype is expected to remain small and focused.

A likely flow is:

```text
1. Import raw exports
2. Show high-level data quality / normalization result
3. Review reconciliation candidates
4. Accept/reject/redirect mappings
5. Recompute the canonical view
6. Compare sub-assembly reuse across variants
7. Drill into one reuse opportunity or inconsistency
8. Show the underlying evidence
```

A useful executive view might summarize:

```text
Variants analyzed
Assemblies identified
Already-reused assemblies
Potential reuse candidates
Blocked opportunities
Data-quality issues
```

A useful engineering view should make it possible to inspect:

```text
raw record
    ↓
canonical entity
    ↓
reconciliation decision
    ↓
supporting evidence
```

The goal is to demonstrate **proof and traceability**, not an autonomous black-box answer.

---

# Scope Discipline

The case explicitly recommends a maximum preparation time of approximately four hours.

Accordingly, the implementation should prioritize:

- a working end-to-end ingestion path;
- a clear canonical entity model;
- a reviewable reconciliation mechanism;
- useful cross-variant reuse analysis;
- visible evidence/provenance;
- a concise, maintainable codebase;
- a trace of AI-assisted development.

The prototype should deliberately avoid spending most of the time on infrastructure that does not materially improve the pilot demonstration.

Examples of things that are not required for the PoC:

- production authentication/user management;
- a distributed database;
- a graph database;
- a complex multi-agent framework;
- full enterprise deployment automation;
- OCR/PDF extraction;
- a general-purpose chatbot.

The architecture can still evolve toward these capabilities when discussing what would be required for a real Alstom deployment.

---

# Repository / Working Agreement

The repository should progressively contain:

```text
.
├── README.md
├── CLAUDE.md / equivalent AI coding instructions
├── docs/
│   ├── scenarios.md
│   ├── architecture.md
│   └── ai-worklog.md
├── data/
│   ├── inputs/
│   ├── processed/
│   └── ground_truth/
├── src/
│   ├── ingestion/
│   ├── normalization/
│   ├── reconciliation/
│   ├── analysis/
│   └── ui/
└── tests/
```

The exact structure is intentionally not frozen yet; it should evolve with the ingestion and UI design discussions.

The Git history, AI prompts, coding instructions, and other development traces are part of the case deliverable because Cognyx explicitly wants to understand **how the work was done with AI**, not only the final code.

---

# Next Design Step

Before implementing the complete pipeline, the next design exercise is to walk through **one concrete object end-to-end**, for example:

```text
Raw PLM rows
+ ERP material
+ supplier
+ engineering notes
        ↓
standardization
        ↓
candidate identity resolution
        ↓
human review
        ↓
canonical component
        ↓
canonical BOM relationships
        ↓
cross-variant reuse analysis
```

This should be used to validate the data model and reconciliation design before generalizing it to all entities and files.
