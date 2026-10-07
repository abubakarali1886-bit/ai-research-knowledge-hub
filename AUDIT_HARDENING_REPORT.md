# AI Research Knowledge Hub Audit and Hardening

Date: 2026-09-05

## Weaknesses Found and Fixed

- Public registration accepted a caller-supplied role, allowing privilege escalation to researcher or admin.
- The `/api/auth/create-admin` endpoint was unauthenticated and used a predictable default password.
- Search, chat, dashboard, and summarization routes were usable without backend authentication.
- Upload and delete operations were available to viewers.
- JWT subjects were converted to integers without safely rejecting malformed claims.
- Upload validation trusted the optional client-reported size, checked only the extension, and retained unsafe filename components in the storage path.
- Duplicate files could be uploaded and vector indexing retries could fail because Chroma records were added rather than upserted.
- Reprocessing could create duplicate PostgreSQL chunk rows.
- Fallback search could return chunks belonging to inactive documents.
- RAG citations exposed only document and chunk IDs; the response schema discarded richer metadata.
- Topics and keywords were stored in the same relationship.
- Text cleaning collapsed line structure, weakening title-page and publication metadata extraction.
- Publication year extraction preferred the first year found, which could be a cited or unrelated year.
- The upload route persisted chunks but did not attempt vector indexing.

## Changes Implemented

- Public registration always creates a viewer; elevated roles must be granted administratively.
- Admin creation now requires an authenticated admin. Existing CLI bootstrap remains available.
- Protected data and AI routes with active-user dependencies; restricted upload/delete to researcher or admin.
- Added safe JWT subject validation.
- Added byte-level upload size checks, MIME/extension agreement checks, empty-file rejection, UUID-based storage names, and SHA-256 duplicate detection against active stored files.
- Made vector writes idempotent with Chroma upsert and cleared stale chunk references during reprocessing.
- Added normalized `research_topics`, `document_topic`, and document topic relationships. Existing keyword data is preserved.
- Added separate `topics` and `keywords` fields to document responses.
- Improved line-preserving cleaning and publication-aware year extraction.
- Upload processing now attempts embeddings/vector indexing and records an indexing failure while preserving the database text-search fallback.
- Enriched semantic search and RAG source responses with title, author, year, document type, category, and topics.
- Added inactive-document filtering to database fallback search.
- Added fallback retrieval when the existing vector store contains stale document IDs after historical database changes.
- Fixed dashboard topic aggregation after topic normalization.
- Hardened Ollama response handling for thinking models and increased the RAG answer budget so final answers are produced.
- Fixed document-detail summary actions and viewer-facing upload permissions.
- Restored the upload metadata form for title, authors, publication year, department/category, document type, and research topics.
- Added reproducible backend/frontend Dockerfiles and development/production Compose configurations.

## API and Database Notes

No new public endpoint was required. Existing endpoints were hardened in place. The topic tables are additive and are created by the existing startup metadata creation path; no records are deleted or rewritten.

## BOT Alignment Reference

The official Bank of Tanzania homepage was reviewed for institutional vocabulary and publication organization. Relevant reference areas include Monetary Policy, Financial Stability, Financial Sector Supervision, Payment and Settlement Systems, Financial Markets, Currency Issuance, Financial Deepening and Inclusion, and regular publications such as Monthly Economic Review and economic-statistics releases. These were used as classification vocabulary only; no BOT documents were hardcoded or copied.

## Validation Performed

- Backend `compileall` and focused processor checks passed in `.venv311`.
- Upload validation and publication-year extraction smoke checks passed.
- SQLAlchemy in-memory schema smoke test passed, including the new topic tables.
- Frontend ESLint passed.
- Frontend production build passed.
- Backend pytest is installed in the live backend environment and the final suite passes with seven tests.
- Live FastAPI startup passed on port 8002 with PostgreSQL reachable.
- Live authenticated dashboard, search, summary-status, RAG, and document-summary requests passed.
- Live search returned three real results after stale-vector fallback was added.
- Live RAG returned a grounded answer with two sources.
- Live DOCX upload returned HTTP 200, persisted category/type/topics, created one chunk and one embedding, and was cleaned up after verification.
- Added and ran seven automated tests covering metadata extraction, BOT taxonomy, upload validation, password security, and dashboard values.
- Added automatic metadata backfill/import utilities for existing files and verified live dashboard statistics after browser uploads.
- Browser verification showed file-only upload, persisted document departments/types, three category groups, and six research topics.
- Completed a final BOT taxonomy pass against the homepage, Financial Sector Supervision, Payment Systems, Financial Markets, Currency, Financial Deepening and Inclusion, Monetary Policy, and Public Notices pages.
- Added BOT-aligned department areas, public-notice/statistics/regulatory publication types, government-finance, foreign-exchange, currency, banking, consumer-protection, fintech, AML, and housing-finance research topics.
- Live final API verification showed four departments, four publication types, eleven research topics, and complete title/year/type/department metadata for active documents.
- Replaced deprecated `PyPDF2` with `pypdf`; a real repository PDF extracted 79,621 characters successfully.
- Final diagnostics reported no backend or frontend errors.

## Remaining Limitations

- Processing and embedding generation still run synchronously inside the upload request; a production deployment should move this to a worker queue with retry state transitions.
- Existing documents whose topics were previously stored as keywords are not automatically reclassified without an explicit data migration or review step.
- Metadata confidence scores, human review UI, full multi-author normalization, page-aware chunk citations, advanced metadata/category filters, and comprehensive automated API tests remain to be implemented.
- The repository has no configured Alembic environment/version scripts; additive topic tables currently rely on the existing `create_all` startup behavior.
- Production deployment must provide a strong `SECRET_KEY`, restrict CORS origins, and remove predictable bootstrap credentials from operational scripts.
- Existing Chroma records from historical document IDs should be rebuilt when operationally convenient; runtime fallback currently keeps search functional.
- Author extraction intentionally leaves institutional staff labels such as "Bank staff" as NULL rather than presenting them as individual authors.
- Docker Compose syntax could not be executed on this workstation because the Docker CLI is not installed; the YAML and Dockerfiles are present for a Docker-enabled environment.
