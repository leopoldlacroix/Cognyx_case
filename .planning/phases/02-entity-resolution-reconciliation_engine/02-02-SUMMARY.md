---
phase: 02-entity-resolution-reconciliation_engine
plan: 02
subsystem: normalization
tags: [engineering-notes, language-detection, text-normalization, NORM-06, SCEN-H]

requires:
  - phase: 02-entity-resolution-reconciliation_engine
    plan: 01
    provides: normalize_erp_materials, normalize_whitespace, soft warnings pattern, db_connection fixture
provides:
  - engineering_note.language_normalized and note_text_normalized columns (CREATE + safe ALTER)
  - detect_language() heuristic (FR/EN/DE)
  - normalize_engineering_notes() language + text pass
  - soft warning undetectable_language for empty/blank note text
affects: [02-03, reconciliation-evidence, SCEN-H]

tech-stack:
  added: []
  patterns: [heuristic language detection, soft warning on undetectable language, preserve raw note_text]

key-files:
  created: []
  modified:
    - app/db/schema.py
    - app/services/normalization.py
    - tests/test_normalization.py

key-decisions:
  - "Added language_normalized/note_text_normalized in plan 02-02 schema (blocker vs waiting for 02-03) via CREATE + _ensure_column ALTER — no table drop"
  - "Accent check uses text.upper() so lowercase French diacritics (é, è, …) count"
  - "Accent-free French with ≥2 FR function words classified FR (covers real note without diacritics)"
  - "Soft warning only for empty/blank note text defaulting to EN — not for ordinary English"
  - "Note text punctuation trim is strip of leading/trailing .,:;!?-_ only — not normalize_punctuation (identifier rewriter)"

patterns-established:
  - "Engineering note normalization is a separate post-ingest pass writing *_normalized columns beside immutable raw text"
  - "undetectable_language warning type for blank notes"

issues-created: []

duration: 20min
completed: 2026-09-23
---

# Plan 02-02: Normalize Engineering Notes Summary

**Engineering notes get FR/EN/DE language detection into `language_normalized` and cleaned text into `note_text_normalized`, with raw `note_text` preserved and a soft warning only when language is undetectable (blank text).**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-23
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `language_normalized` and `note_text_normalized` on `engineering_note` (CREATE TABLE + safe ALTER if absent)
- Implemented `detect_language()` heuristic (French accents/words, German words with score ≥2, default EN)
- Implemented `normalize_engineering_notes()` writing language + normalized text; emits `undetectable_language` for empty/blank text
- Spot-checked heuristic against all 71 rows in `data/inputs/engineering/technical_notes.csv` — 0 FR/EN misclassifications (no DE rows in source; DE covered by unit tests)
- Text normalization: whitespace collapse + light leading/trailing punctuation trim; raw `note_text` unchanged

## Task Commits

Each task was committed atomically:

1. **Task 2.2.1: Language detection** - `942aae5` (feat)
2. **Task 2.2.2: Note text normalization** - `44e37ec` (feat)

## Files Created/Modified
- `app/db/schema.py` — `language_normalized`, `note_text_normalized` columns + `_ensure_column`
- `app/services/normalization.py` — `detect_language()`, `normalize_engineering_notes()`
- `tests/test_normalization.py` — language detection + text normalization tests

## Decisions Made
- Brought schema columns forward from 02-03 so this plan can UPDATE them without destructive recreate
- Tightened FR path for accent-free French with ≥2 common FR words (one real CSV note had no diacritics)
- Did not apply `normalize_punctuation` to note bodies (would rewrite underscores/dashes like identifiers)

## Deviations from Plan
1. **Schema columns added here (not deferred to 02-03)** — Required blocker fix so UPDATE of `language_normalized` / `note_text_normalized` works; used CREATE + safe ALTER, no data loss.
2. **FR without accents** — Plan required `has_french_char AND french_score`; one real FR note had no accents; added `french_score >= 2 and french_score > german_score` branch.
3. **Punctuation trim without `normalize_punctuation`** — Used light `strip('.,;:!?-_')` after whitespace so note prose is not identifier-rewritten.
4. **`sans` → `SANS` in word set** — Plan sample had lowercase token that would never match `text_upper` word set.

## Verification
```
python3 -m pytest tests/test_normalization.py -v --tb=short
→ 34 passed
```

## Self-Check: PASSED
- [x] detect_language identifies FR, EN, DE
- [x] language_normalized / note_text_normalized populated
- [x] original note_text preserved
- [x] blank → EN + soft warning
- [x] ERP tests from 02-01 still green
