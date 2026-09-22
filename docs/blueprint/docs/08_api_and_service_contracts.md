# 08 — API and Service Contracts

This document defines behavioral contracts, not implementation code.

## 8.1 Service boundaries

Recommended backend services/modules:

- `IngestionService`
- `NormalizationService`
- `SourceEntityService`
- `ReconciliationService`
- `CanonicalizationService`
- `TechnicalFactService`
- `ReuseAnalysisService`
- `RunService`

The UI should call application services/API endpoints rather than directly manipulating tables.

## 8.2 Ingestion endpoints

### `POST /ingestion/files`

Purpose: register/upload/import one source file.

Input:

- file or file path reference;
- source system.

Output:

- source file ID;
- detected file type;
- row count;
- validation summary;
- ingestion status.

### `GET /ingestion/files`

Return recent source files and ingestion status.

## 8.3 Data explorer endpoints

### `GET /data/{entity_type}`

Supports:

- search;
- status filter;
- source-system filter;
- pagination.

### `GET /data/{entity_type}/{id}`

Returns:

- source/entity fields;
- normalized fields;
- provenance;
- related rows;
- reconciliation state.

## 8.4 Reconciliation endpoints

### `POST /reconciliation/runs`

Input:

- entity type;
- scope (`UNASSESSED`, `ALL_REASSESS`, explicit IDs);
- optional limits for demo safety.

Output:

- run ID;
- initial status.

### `GET /reconciliation/runs/{id}`

Returns run progress and summary.

### `GET /reconciliation/{entity_type}`

Returns source entities with reconciliation state.

### `POST /reconciliation/{entity_type}/{id}/assess`

Runs single-entity reconciliation and returns candidates.

### `POST /reconciliation/{entity_type}/{id}/decision`

Input:

- candidate reconciliation ID;
- decision (`ACCEPT`, `REJECT`);
- optional reviewer identity/comment.

Output:

- resulting reconciliation status;
- canonical entity if accepted;
- downstream canonicalization status.

## 8.5 Canonical endpoints

### `GET /canonical/components/{id}`

Return canonical entity and linked source references.

### `GET /canonical/assemblies/{id}`

Return assembly, its components and variant usage.

### `GET /canonical/bom`

Filters:

- variant;
- assembly;
- component.

## 8.6 Analysis endpoints

### `GET /analysis/overview`

Return factual aggregate counts.

### `GET /analysis/reuse`

Filters:

- variant;
- assembly;
- status.

### `GET /analysis/reuse/{assembly_id}`

Return detailed cross-variant comparison and evidence.

### `GET /analysis/data-quality`

Return detected quality issues.

## 8.7 Response principles

The API should expose IDs and provenance needed by the UI to navigate backward.

Errors should be structured enough for the UI to display a useful message.

## 8.8 Concurrency assumptions

PoC assumption: one active operator.

Nevertheless, mutation endpoints should validate current status before changing it, especially accept/reject decisions.

## 8.9 No business logic in the frontend

Do not duplicate reconciliation or reuse rules in React/TypeScript. Keep them server-side so the same logic can be tested independently.
