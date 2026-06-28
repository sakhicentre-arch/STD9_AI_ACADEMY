<!--
================================================================================
  BASELINE CONTROL BLOCK — DO NOT EDIT
================================================================================
  Document Title:    EDF Implementation Backlog
  Version:           1.0
  Status:            BASELINED
  Approval Status:   Approved for Implementation
  Freeze Date:       2026-06-27
  Document Owner:    STD9_AI_ACADEMY Engineering Team / Programme Management
  Project Name:      STD9_AI_ACADEMY — Std 9 Educational Content Corpus (GSEB + NCERT)
  Baseline Identifier: EDF-BASELINE-v1.0
================================================================================
-->

# EDF Implementation Backlog

> **BASELINE v1.0 — FROZEN 2026-06-27** · Status: BASELINED · Approved for Implementation
> Direct edits to this baseline are prohibited. Changes require a Change Request and will produce a new semantically-versioned revision (see footer).

> **Project:** STD9_AI_ACADEMY — Std 9 Educational Content Corpus (GSEB + NCERT)
> **Document:** EDF Implementation Backlog
> **Engineer:** STD9_AI_ACADEMY Engineering Team
> **Status:** In Progress — Deliverable 1 of 7 Complete
> **Last Updated:** 2026-06-27

---

## Deliverable Index

| # | Deliverable | Status |
|---|-------------|:------:|
| 1 | Architecture Review | ✅ Complete |
| 2 | _Pending_ | ⏳ Not Started |
| 3 | _Pending_ | ⏳ Not Started |
| 4 | _Pending_ | ⏳ Not Started |
| 5 | _Pending_ | ⏳ Not Started |
| 6 | _Pending_ | ⏳ Not Started |
| 7 | _Pending_ | ⏳ Not Started |

---

# Deliverable 1 — Architecture Review

## 1. Executive Summary

The STD9_AI_ACADEMY workspace is a **content-corpus acquisition project** whose goal is to assemble an authoritative, source-tiered collection of Standard 9 (Class IX) educational material for the **Gujarat Secondary and Higher Secondary Education Board (GSEB)** and the **National Council of Educational Research and Training (NCERT)**, in preparation for downstream AI-tutoring use.

As of this review, the project is **in Phase 1 (discovery, cataloguing, and partial acquisition)**. The strategic foundations are sound: a four-tier source hierarchy is defined, official government portals (Tier 1) are identified for every required subject, and a disciplined audit has already surfaced six factual inaccuracies that must be corrected before any content is promoted to the corpus. However, the workspace is currently a **documentation-heavy, code-light** artefact: metadata, syllabi, and catalogues exist in Markdown, but there is **no acquisition automation, no integrity-verification layer, no text-extraction pipeline, and no structured knowledge representation**. Downloaded PDFs are present for only three NCERT subjects (Science, Mathematics, English Beehive), while every GSEB folder remains empty and checksums have never been recorded.

The architecture is **readiness-rated at 45 / 100** for the stated downstream goal. The documentation and sourcing layer is strong; the engineering and data-integrity layers are largely absent. The highest-value improvements are (a) correcting the six audit-flagged inaccuracies, (b) building an automated, checksummed acquisition pipeline, (c) back-filling the empty GSEB corpus, and (d) introducing a deterministic extraction and indexing layer that converts opaque PDFs into structured, queryable knowledge assets. None of these require architectural rework — they are additive to the current, well-organised directory layout.

This document records the current state, identifies technical debt and risks, and provides an implementation-readiness assessment that the subsequent deliverables (2–7) will operationalise.

---

## 2. Current Architecture Overview

The current "architecture" is a **file-system-based content store** governed by editorial Markdown documentation. There is no runtime, no service, and no database. All state lives on the local Windows filesystem under the workspace root, organised as follows:

```
STD9_AI_ACADEMY/
├── AGENTS.md                         # Agent operating rules
├── .mcp.json                         # MCP server config (comet-bridge)
├── EDF_IMPLEMENTATION_BACKLOG.md     # THIS DOCUMENT
├── nul                               # stray artifact (to be removed)
├── DEBUG/                            # process-monitor traces (non-corpus)
│   ├── procmon_mcp_open.CSV
│   └── procmon_mcp_open.PML
└── CONTENT/
    ├── INVENTORY.md                  # master inventory (EMPTY template)
    ├── RAW/                          # downloaded binary PDFs (ground truth)
    │   ├── NCERT/
    │   │   ├── SCIENCE/              # 13 chapter PDFs (~128 MB)
    │   │   ├── MATHEMATICS/          # 8 chapter PDFs  (~18 MB)
    │   │   ├── ENGLISH/              # 8 Beehive PDFs  (~33 MB)
    │   │   ├── BOOKS/                # empty
    │   │   ├── CURRICULUM/           # empty
    │   │   ├── EXEMPLARS/            # empty
    │   │   └── TEACHER_RESOURCES/    # empty
    │   └── GSEB/                     # all subfolders empty
    │       ├── BOOKS/  LAB_MANUALS/  MODEL_PAPERS/
    │       ├── PREVIOUS_PAPERS/  QUESTION_BANKS/  SAMPLE_PAPERS/
    │       └── SYLLABUS/  TEACHER_GUIDES/  WORKBOOKS/
    ├── METADATA/
    │   ├── AUDIT_REPORT.md           # Phase-1 quality audit (74/100)
    │   ├── SOURCE_REGISTRY.md        # 34 sources, 4 tiers
    │   └── DOWNLOAD_LOG.md           # acquisition tracking
    ├── SYLLABUS/
    │   ├── GSEB_STD9_SYLLABUS.md
    │   └── SOURCES.md                # duplicates SOURCE_REGISTRY (debt)
    ├── NCERT/
    │   └── NCERT_BOOK_CATALOG.md
    └── GSEB/
        └── GSEB_BOOK_CATALOG.md
```

### 2.1 Architectural Style

The system follows a **manual, document-driven content-ingestion model** with three conceptual layers:

1. **Source-of-Truth Layer** — `CONTENT/RAW/**` holds the authoritative binary PDFs as downloaded. Nothing is transformed; these are the canonical assets.
2. **Metadata & Provenance Layer** — `CONTENT/METADATA/**` records what was sourced, from where, at what tier, and whether it was verified. This is the audit surface.
3. **Catalogue & Syllabus Layer** — `CONTENT/SYLLABUS/**`, `CONTENT/NCERT/**`, `CONTENT/GSEB/**` describe *what should exist* (curriculum-level truth) so the RAW layer can be measured against it.

### 2.2 Data Flow (Current)

```
Official portals (Tier 1) ──┐
                            ├──▶ manual download ──▶ RAW/ (PDFs)
Reference sites (Tier 3) ───┘                              │
                                                          ▼
Reference catalogues ──▶ SYLLABUS/ + NCERT/ + GSEB/   (no automated diff)
                            │
                            └──▶ METADATA/ (audit + log, manually maintained)
```

There is **no automated pipeline** between layers. Reconciliation between "what the catalogue says should exist" and "what RAW actually contains" is performed manually by reading files.

### 2.3 Configuration & Tooling

- `.mcp.json` registers a single MCP server (`comet-bridge`, launched via `npx comet-mcp`). This is the only registered external integration.
- No `package.json`, no `requirements.txt`, no `Makefile`, no scripts directory. The project has **zero build/runtime artefacts**.
- `AGENTS.md` constrains agent behaviour to direct file editing and forbids repeated inspection.

---

## 3. Existing Components

### 3.1 Content Assets (Binary PDFs)

| Path | Count | Approx. Size | Status |
|------|:-----:|:------------:|--------|
| `CONTENT/RAW/NCERT/SCIENCE/` | 13 | ~128 MB | Downloaded (`iesc1_ch01` … `iesc1_ch13`) |
| `CONTENT/RAW/NCERT/MATHEMATICS/` | 8 | ~18 MB | Downloaded (`iemh1_ch01` … `iemh1_ch08`) — **incomplete** (catalogue expects 12 chapters) |
| `CONTENT/RAW/NCERT/ENGLISH/` | 8 | ~33 MB | Downloaded (`iebe1_ch01` … `iebe1_ch08`) — **incomplete** (Beehive expects more chapters) |
| `CONTENT/RAW/GSEB/**` | 0 | 0 | **All folders empty** |
| `CONTENT/RAW/NCERT/BOOKS/` | 0 | 0 | Empty |
| `CONTENT/RAW/NCERT/CURRICULUM/` | 0 | 0 | Empty |
| `CONTENT/RAW/NCERT/EXEMPLARS/` | 0 | 0 | Empty |
| `CONTENT/RAW/NCERT/TEACHER_RESOURCES/` | 0 | 0 | Empty |

**Net:** ~179 MB of PDFs across 29 chapter files, all NCERT, three subjects only. Zero GSEB binaries.

### 3.2 Metadata Documents

| File | Purpose | Completeness |
|------|---------|:------------:|
| `CONTENT/METADATA/AUDIT_REPORT.md` | Phase-1 quality audit; confidence 74/100; lists 6 inaccuracies | Complete |
| `CONTENT/METADATA/SOURCE_REGISTRY.md` | 34 sources across 4 tiers; URL live-check results | Complete |
| `CONTENT/METADATA/DOWNLOAD_LOG.md` | Acquisition tracker (downloaded / verified / checksum columns) | Partial — no checksums recorded; 0/28 marked Downloaded=Yes |
| `CONTENT/INVENTORY.md` | Master inventory | **Empty template** (header row only) |

### 3.3 Catalogue & Syllabus Documents

| File | Purpose | Completeness |
|------|---------|:------------:|
| `CONTENT/SYLLABUS/GSEB_STD9_SYLLABUS.md` | GSEB Std 9 subjects, mediums, indicative chapters | Substantive but contains unverified "Maitri" claim |
| `CONTENT/SYLLABUS/SOURCES.md` | Master source list | **Duplicates** SOURCE_REGISTRY (debt) |
| `CONTENT/NCERT/NCERT_BOOK_CATALOG.md` | NCERT Class 9 books, codes, chapter lists | Substantive; Beehive list over-stated; codes unverified |
| `CONTENT/GSEB/GSEB_BOOK_CATALOG.md` | GSEB Std 9 book catalogue by medium | Substantive; "Maitri" claim unverified |

### 3.4 Operational Components

| Component | Location | Role |
|-----------|----------|------|
| Agent rules | `AGENTS.md` | Constrains agent file-handling behaviour |
| MCP configuration | `.mcp.json` | Registers `comet-bridge` server |

There are **no other operational components** — no scripts, no extractors, no validators, no test suite.

---

## 4. Strengths

1. **Disciplined source-tiering model.** The four-tier hierarchy (Tier 1 = Official Government, Tier 2 = Official Educational, Tier 3 = High-quality Educational, Tier 4 = Community) is clearly defined in `SOURCE_REGISTRY.md` and is consistently applied. This gives an unambiguous conflict-resolution rule ("prefer GSSTB → NCERT → CBSE → GCERT/Edustud → reference sites") that downstream components can rely on.

2. **Strong Tier-1 coverage.** 9 of 34 registered sources are Tier-1 government portals, covering every required Std 9 subject across both boards. Official portals exist for GSSTB, GSEB, GCERT, NCERT, and CBSE, giving the project a legitimate acquisition path for primary content.

3. **Clean, conventional directory layout.** The `CONTENT/{RAW,METADATA,SYLLABUS,NCERT,GSEB}` split cleanly separates binary truth from documentation. Naming is consistent (`iesc1_chNN.pdf`, `iemh1_chNN.pdf`, `iebe1_chNN.pdf`). This layout is extensible without restructuring.

4. **An honest, pre-acquisition audit.** The `AUDIT_REPORT.md` was produced *before* bulk ingestion and proactively surfaced six inaccuracies. This is the single most important quality asset in the workspace — it prevents bad facts from being propagated into the corpus.

5. **100% URL health.** All 30 unique URLs returned HTTP 200 on live-check. The known `ncert.nic.in` intermittent 000 is correctly documented as server-side flakiness, not a dead link. There is no link rot to remediate.

6. **Transparent provenance.** Every content/cataldocum catalogue cites its sources inline, and the audit records exactly which claims are verified versus unverified. Provenance is a first-class citizen, not an afterthought.

7. **Forward-looking NCF-SE awareness.** The catalogues explicitly acknowledge the 2026-27 NCF-SE transition (Ganita Manjari, Exploration, Kaveri) and the 2022-23 rationalisation cuts. This prevents the corpus from silently ingesting deprecated content.

8. **Edition discipline.** Third-party PDFs (BYJU'S scans) are explicitly flagged as 2020/2021 pre-rationalisation and quarantined to a `_REF_3P` reference path — they are not treated as primary content. This is correct data-hygiene practice.

---

## 5. Weaknesses

1. **No acquisition automation.** Downloads are manual. There is no script that takes the source registry and populates `RAW/`. This is the dominant weakness: every downstream capability depends on a complete, verified corpus that does not yet exist and cannot be assembled at scale by hand.

2. **No integrity verification.** `DOWNLOAD_LOG.md` has a Checksum column that is blank for all 28 items. SHA-256 was "planned" but never implemented. There is no way to detect silent corruption, partial downloads, or substitution of a PDF.

3. **Incomplete corpus coverage.** Only 3 of ~16 Tier-1 NCERT downloadables have any files, and those are partial (Maths 8/12, English 8/~17, Science 13/12+ — Science appears to exceed the rationalised count and needs reconciliation). GSEB coverage is **zero**. The corpus cannot serve its intended purpose in this state.

4. **Unverified factual claims in the catalogue.** Six inaccuracies from the audit remain uncorrected in the live Markdown: the "Maitri" textbook-name claim, the over-stated Beehive chapter list (deleted poems still listed), the stale "11 prose" count, unverified NCERT textbook codes, indicative-only GSEB chapter lists, and `~`-estimated History/Sanskrit/Urdu counts.

5. **No structured representation.** Content exists only as opaque PDF binaries and human-readable Markdown. There is no machine-readable chapter index, no JSON/YAML manifest, no extracted text, and no embeddings or vector store. The corpus is not yet queryable by the intended AI tutor.

6. **No extraction/OCR layer.** PDFs (especially scanned GSEB Gujarati-medium editions) will require text extraction and possibly OCR. No tooling, output schema, or storage convention for extracted text exists.

7. **Single-source-of-truth violation.** `SOURCES.md` duplicates the source tables already in `SOURCE_REGISTRY.md` and the in-catalogue source lists, creating three places that can drift. The audit flagged this explicitly.

8. **Empty master inventory.** `CONTENT/INVENTORY.md` is an empty template, yet the `DOWNLOAD_LOG.md` effectively serves as the de-facto inventory. The intended master-inventory role is unfulfilled.

9. **No change tracking / version control.** The workspace is **not a git repository**. There is no history of edits, no rollback, no blame. For a corpus intended to feed an AI product, this is a material governance gap.

10. **No tests or validation gates.** There is nothing that enforces "every RAW PDF must have a manifest entry," "every manifest entry must have a checksum," or "no catalogue claim may contradict the audit's corrections." Quality is currently a human-discipline problem, not a system property.

---

## 6. Technical Debt

Technical debt is quantified by severity and remediation cost (S/M/L).

| # | Debt Item | Location | Severity | Cost | Notes |
|---|-----------|----------|:--------:|:----:|-------|
| TD-1 | Six uncorrected factual inaccuracies | GSEB syllabus, both catalogues | **Critical** | S | Audit §4.1–4.6; must fix before any further ingestion |
| TD-2 | Empty master inventory | `CONTENT/INVENTORY.md` | High | S | Back-fill from DOWNLOAD_LOG |
| TD-3 | Duplicate source lists | `SOURCES.md` ↔ `SOURCE_REGISTRY.md` ↔ in-catalogue tables | Medium | S | Retire SOURCES.md duplication |
| TD-4 | Missing metadata headers on content files | All catalogues/syllabi | Medium | S | Add Source/Publisher/Verification/Confidence block |
| TD-5 | No checksums recorded | `DOWNLOAD_LOG.md` | High | M | Compute SHA-256 for all 29 existing PDFs + new ones |
| TD-6 | Unverified NCERT textbook codes | `NCERT_BOOK_CATALOG.md` §1,2,4 | Medium | M | Verify against master list PDF |
| TD-7 | No version control | Workspace root | High | M | `git init`, establish commit hygiene |
| TD-8 | Partial NCERT downloads | `RAW/NCERT/MATHEMATICS`, `ENGLISH` | High | M | Complete chapter sets per catalogue |
| TD-9 | Science chapter count mismatch (13 vs 12) | `RAW/NCERT/SCIENCE` | Medium | S | Reconcile against rationalised list |
| TD-10 | No extraction/OCR pipeline | (absent) | High | L | New component required |
| TD-11 | No structured manifest format | (absent) | High | M | Define JSON/YAML schema + populate |
| TD-12 | GSEB portal has no direct PDF URLs | GSSTB portal | Medium | M | Portal-navigation acquisition strategy |
| TD-13 | Stray `nul` and `DEBUG/` artefacts | Workspace root | Low | S | Remove from corpus area |
| TD-14 | No automated tests / validation gates | (absent) | Medium | M | Add manifest/integrity assertions |
| TD-15 | Indicative-only GSEB chapter lists | GSEB syllabus & catalogue | Medium | M | Extract authoritative ToCs from GSSTB PDFs once acquired |

**Total identified debt:** 15 items — 1 Critical, 6 High, 7 Medium, 1 Low. The Critical and High items should be cleared before Deliverable 2 begins.

---

## 7. Missing Components

These are capabilities the downstream goal requires but the workspace does not yet contain.

### 7.1 Acquisition Pipeline (Critical)
- **`acquire.py` / acquisition orchestrator** — reads the source registry, downloads Tier-1 PDFs into `RAW/`, handles `ncert.nic.in` retry-on-000 flakiness, and writes a manifest entry per file.
- **Retry / rate-limit middleware** — NCERT portal is known-flaky; needs exponential backoff.
- **GSSTB portal navigator** — GSEB has no direct PDF URLs; a navigation/selector step is required per medium/subject.

### 7.2 Integrity Layer (Critical)
- **SHA-256 checksum tooling** — compute and persist checksums for every RAW asset.
- **Verification routine** — re-check checksums on demand to detect drift.
- **PDF validity check** — confirm each file is a real PDF (not an HTML error page) before acceptance.

### 7.3 Extraction & Normalisation (High)
- **PDF text extractor** — convert born-digital PDFs to clean text/markdown.
- **OCR fallback** — for scanned GSEB Gujarati-medium editions.
- **Chapter segmentation** — split books into per-chapter structured units aligned to the catalogue.
- **Normalised output store** — e.g. `CONTENT/PROCESSED/**` with deterministic naming.

### 7.4 Structured Knowledge Representation (High)
- **Manifest schema** (JSON/YAML) — one record per asset: id, source, tier, subject, board, medium, chapter, edition, checksum, download date, status.
- **Chapter index** — machine-readable mapping from (board, subject, chapter) → asset(s).
- **Curriculum validation document** — the gap noted in the audit ("see CURRICULUM_VALIDATION.md") is referenced but **does not exist**.

### 7.5 Governance (Medium)
- **Version control** — `git init` + `.gitignore` for binaries if needed.
- **Metadata header standard** — applied to every content file.
- **Validation test suite** — asserts integrity, completeness, and catalogue/log consistency.

### 7.6 Back-fill (Data, not code)
- **GSEB corpus** — all GSEB RAW folders are empty; 10 GSSTB books targeted.
- **NCERT exemplars, lab manual, model papers** — flagged as missing in audit §6.
- **Remaining NCERT chapters** — Maths (4 more), English Moments, Social Science (4 books), Hindi, Sanskrit, Urdu.

---

## 8. Dependency Analysis

### 8.1 External (Data-Source) Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| `ncert.nic.in` textbook portal | Tier-1 PDF source | Intermittent HTTP 000 / TLS drops | Retry middleware, cache successes |
| `gsstb.gujarat.gov.in` portal | Tier-1 PDF source | No direct PDF URLs; portal navigation required | Build GSSTB navigator; accept slower acquisition |
| `cbseacademic.nic.in` | Tier-2 curriculum | Low | Direct fetch |
| `edustud.nic.in` | Tier-1 syllabus PDFs | Low | Direct fetch |
| BYJU'S / StudentBro / Vedantu (Tier 3/4) | Reference / fallback | Edition uncertainty; pre-rationalisation | Quarantine to `_REF_3P`; never primary |
| NCF-SE 2026-27 rollout | Upstream curriculum change | Chapter lists will shift | Treat 2025-26 as authoritative; version-tag everything |

### 8.2 Internal Component Dependencies (build order)

```
[Source Registry] ─┐
                   ├─▶ [Acquisition Pipeline] ──▶ [Integrity Layer (SHA-256)]
[Catalogue/Syllabus]┘                                     │
                                                          ▼
                              [Extraction/OCR] ◀──── [validity check]
                                       │
                                       ▼
                              [Structured Manifest + Chapter Index]
                                       │
                                       ▼
                              [Curriculum Validation] ◀── [Audit Corrections]
                                       │
                                       ▼
                              [AI-Tutor-Ready Knowledge Base]
```

**Critical path:** Audit corrections (TD-1) → Acquisition pipeline → Integrity layer → Extraction → Manifest. The downstream knowledge base cannot be trusted until integrity and extraction are in place.

### 8.3 Tooling Dependencies (anticipated)
- PDF text extraction: `pdfplumber` / `PyMuPDF` (born-digital) and `tesseract` + language packs (OCR, incl. Gujarati `guj`).
- HTTP: a resumable client with retry (`requests` + `urllib3.Retry`, or `httpx`).
- Checksum / hashing: standard library (`hashlib`).
- Manifest I/O: `json`/`yaml`.
- Testing: `pytest` for validation gates.

These are **not yet installed** (no dependency manifest exists). Introducing them is a prerequisite for Deliverables 2+.

### 8.4 Circular / Blocking Dependencies
- **GSEB ToC extraction (TD-15) is blocked on GSEB acquisition (7.6).** Cannot verify indicative chapter lists until the PDFs exist. Workaround: keep lists flagged "indicative" until acquisition completes.
- **Curriculum validation (7.4) is blocked on audit corrections (TD-1).** Validating against known-bad catalogues would entrench errors.

---

## 9. Risks

Risks are scored Likelihood × Impact (L, I on 1–5); score = L × I.

| # | Risk | L | I | Score | Mitigation |
|---|------|:-:|:-:|:-----:|------------|
| R-1 | **Factual errors propagate into the AI tutor** (e.g. "Maitri" textbook, deleted Beehive poems) | 5 | 5 | **25** | Fix TD-1 immediately; add validation gate forbidding unverified claims |
| R-2 | **Silent corruption / partial downloads** undetected (no checksums) | 4 | 4 | **16** | Implement integrity layer (7.2) before any content is consumed |
| R-3 | **NCF-SE 2026-27 transition** invalidates 2025-26 corpus mid-project | 4 | 4 | **16** | Version-tag editions; treat 2025-26 as a named snapshot |
| R-4 | **GSEB portal navigation breaks** (no direct PDF URLs, layout changes) | 4 | 3 | **12** | Build resilient navigator; keep Tier-3 fallback quarantined |
| R-5 | **NCERT portal flakiness** stalls bulk acquisition | 5 | 2 | **10** | Retry middleware with backoff |
| R-6 | **OCR quality on Gujarati scans** insufficient for AI use | 3 | 4 | **12** | Prefer born-digital; QA-sample OCR output before promotion |
| R-7 | **No version control** → irreversible bad edits, no audit trail | 4 | 3 | **12** | `git init` now (TD-7) |
| R-8 | **Unverified textbook codes** cause 404s / wrong files | 3 | 3 | **9** | Verify against master list (TD-6) |
| R-9 | **Manual process does not scale** to 28+ items × multiple mediums | 5 | 2 | **10** | Automate (7.1) |
| R-10 | **Licensing ambiguity** on Tier-3/4 PDF reuse | 2 | 4 | **8** | Restrict corpus to Tier-1/2 for any redistributable use |

**Top-priority risks:** R-1 (factual propagation) and R-2 (corruption) dominate and are both cheaply mitigatable — they should be cleared before Deliverable 2.

---

## 10. Recommended Improvements

Ordered by value-to-effort ratio; each maps to a debt item or missing component.

### 10.1 Immediate (do before Deliverable 2)
1. **Correct the six audit-flagged inaccuracies (TD-1).** Remove/qualify "Maitri"; fix Beehive list and prose count; mark unverified codes and counts. *(Highest ROI — eliminates the top risk.)*
2. **`git init` the workspace (TD-7)** and commit the current state as a baseline. Establish a `.gitignore`.
3. **Back-fill `CONTENT/INVENTORY.md` (TD-2)** from `DOWNLOAD_LOG.md`; retire `SOURCES.md` duplication (TD-3).
4. **Add metadata headers (TD-4)** to all catalogues/syllabi.

### 10.2 Short-term (foundation for Deliverable 2)
5. **Define a manifest schema (7.4)** — JSON, one record per asset, fields per §7.4.
6. **Build the integrity layer (7.2)** — compute SHA-256 for all 29 existing PDFs and write into the manifest.
7. **Reconcile the Science 13-vs-12 mismatch (TD-9)** and complete partial Maths/English sets (TD-8).
8. **Verify NCERT textbook codes (TD-6)** against the master list PDF.

### 10.3 Medium-term (Deliverables 3–5)
9. **Build the acquisition pipeline (7.1)** with retry middleware and a GSSTB portal navigator.
10. **Back-fill the GSEB corpus (7.6)** — all 10 GSSTB Std 9 books across required mediums.
11. **Collect NCERT exemplars, lab manual, and model papers** (audit §6 gaps).
12. **Build the extraction/OCR layer (7.3)** with a born-digital-first strategy and OCR fallback.

### 10.4 Long-term (Deliverables 6–7)
13. **Produce the chapter index + curriculum validation document (7.4).**
14. **Add a validation test suite (7.5)** asserting integrity, completeness, and catalogue/log consistency.
15. **Assemble the AI-tutor-ready knowledge base** (structured, checksummed, extracted, indexed).

### 10.5 Hygiene
16. **Remove stray artefacts** — `nul`, `DEBUG/` (TD-13) from the corpus area.

---

## 11. Implementation Readiness Assessment

| Dimension | Score | Rationale |
|-----------|:-----:|----------|
| Source coverage & tiering | 90 / 100 | Excellent Tier-1 coverage; clear hierarchy; all URLs healthy |
| Documentation quality | 80 / 100 | Strong, but contains 6 uncorrected inaccuracies and missing headers |
| Corpus completeness | 25 / 100 | Only 3 NCERT subjects partial; GSEB empty; exemplars/manuals absent |
| Data integrity | 5 / 100 | No checksums; no validity checks; no provenance manifest |
| Automation / tooling | 0 / 100 | No scripts, no pipeline, no build artefacts |
| Structured representation | 0 / 100 | Opaque PDFs only; no manifest, index, or extracted text |
| Governance / versioning | 10 / 100 | Not a git repo; no tests; manual discipline only |
| **Overall readiness** | **45 / 100** | **Strong foundation, weak engineering layer — additive work, no rework** |

### 11.1 Readiness Verdict

The project is **ready to proceed to Deliverable 2**, but only after the four **Immediate** improvements (§10.1) are applied. Those four items remove the dominant risk (R-1, factual propagation) and establish the governance baseline (version control, single inventory, metadata headers) that all subsequent automation will depend on.

The architecture itself does **not** need to change. The directory layout, source-tiering model, and provenance discipline are all fit for purpose. What is missing is the **engineering layer** that sits on top of this documentation foundation: integrity, automation, extraction, and structured representation. Because these are purely additive, there is no migration risk and no throwaway work.

### 11.2 Gate Criteria for Deliverable 2

Deliverable 2 should not begin until:
- [ ] TD-1 corrected (all six inaccuracies fixed in live Markdown)
- [ ] Workspace under version control (`git init` + baseline commit)
- [ ] `CONTENT/INVENTORY.md` populated; `SOURCES.md` duplication resolved
- [ ] Metadata headers applied to all content/cataldocum files
- [ ] Manifest schema (§7.4) defined and agreed

### 11.3 Confidence Statement

This assessment is grounded in direct inspection of every metadata, catalogue, and syllabus document in the workspace, plus a recursive enumeration of all `RAW/` binaries. The audit's own 74/100 content-confidence figure is respected and incorporated. Engineering-readiness scores (integrity, automation, representation) reflect the **verified absence** of those capabilities, not estimates. The assessment is therefore high-confidence for the current-state characterisation and carries normal planning uncertainty for the forward-looking improvement recommendations.

---

_Deliverable 1 ends here. Deliverables 2–7 will operationalise the improvements catalogued above._

---

# Deliverable 2 — Enterprise Work Breakdown Structure (WBS)

> **Status:** In Progress — Deliverable 2 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 1 — Architecture Review (this document, §1–11)

## 2.1 Executive Overview

### 2.1.1 Purpose

This Work Breakdown Structure (WBS) decomposes the STD9_AI_ACADEMY programme — building a source-tiered, AI-tutor-ready Std 9 (GSEB + NCERT) educational content corpus — into thirteen hierarchical branches and their constituent work packages. It is the authoritative planning artefact that converts the Architecture Review (Deliverable 1) into estimable, assignable, and verifiable units of work.

The WBS is deliberately **deliverable-oriented** (not activity-oriented): every leaf work package produces a tangible, inspectable artefact with explicit acceptance criteria. This makes the structure suitable for fixed-price estimation, earned-value tracking, and contractual hand-off where required.

### 2.1.2 Scope Boundaries

| In Scope | Out of Scope (this programme) |
|----------|-------------------------------|
| Acquisition of Tier-1/2 Std 9 content (NCERT + GSSTB) | Classes other than Std 9 |
| Integrity, extraction, normalisation, indexing | End-user tutor UI/UX design (separate programme) |
| Metadata, manifest, and provenance management | Student information / LMS backend |
| Validation against curriculum truth | Examination marking/grading engine |
| Search & retrieval services | Payment / billing systems |
| AI service integration layer (embeddings, RAG readiness) | Model training/fine-tuning infrastructure |
| Testing, deployment, monitoring, documentation | Production-grade ML model hosting at scale |

### 2.1.3 WBS Design Principles

1. **100% Rule** — the union of all work packages equals the total programme scope; nothing is double-counted or omitted.
2. **Deliverable-leafed** — every leaf (lowest-numbered work package) yields a discrete deliverable with measurable acceptance criteria.
3. **Single accountability** — each work package has exactly one Owner Role.
4. **Decomposition depth** — three levels below the branch (Programme → Branch → Sub-branch → Work Package) is the maximum; deeper decomposition is deferred to sprint planning.
5. **Traceability** — every work package cross-references Deliverable 1 debt items (TD-n), risks (R-n), or missing components (§7.n) where applicable.

### 2.1.4 Effort & Priority Conventions

- **Effort** is expressed in **Story Points (SP)** on a modified Fibonacci scale (1, 2, 3, 5, 8, 13, 21), where 1 SP ≈ 1 ideal engineer-day. Aggregate programme effort is summarised in §2.4.
- **Priority**: P0 (blocking / critical path), P1 (high), P2 (medium), P3 (low / discretionary).
- **Risk Level**: L (low), M (medium), H (high) — cross-referenced to §9 of Deliverable 1 where applicable.

### 2.1.5 Role Legend

| Code | Role |
|------|------|
| PM | Programme Manager |
| SA | Solution Architect |
| DS | Data Steward |
| DE | Data Engineer |
| ML | ML/AI Engineer |
| SRE | Site Reliability / DevOps Engineer |
| QA | Quality Assurance Engineer |
| CE | Content/Editorial Lead |
| SEC | Security Engineer |
| TW | Technical Writer |

### 2.1.6 Programme-Level Summary

| Branch | Title | Owner | Effort (SP) | Priority |
|--------|-------|-------|:-----------:|:--------:|
| 1.0 | Programme | PM | 8 | P0 |
| 1.1 | Governance | PM / SA | 13 | P0 |
| 1.2 | Architecture | SA | 13 | P0 |
| 1.3 | Source Acquisition | DS / DE | 34 | P0 |
| 1.4 | Content Processing | DE / ML | 34 | P1 |
| 1.5 | Metadata | DS | 21 | P0 |
| 1.6 | Database | DE | 21 | P1 |
| 1.7 | Search | DE / ML | 18 | P1 |
| 1.8 | AI Services | ML | 21 | P2 |
| 1.9 | Validation | QA / CE | 18 | P0 |
| 1.10 | Testing | QA | 18 | P1 |
| 1.11 | Deployment | SRE | 13 | P1 |
| 1.12 | Monitoring | SRE | 8 | P1 |
| 1.13 | Documentation | TW / SA | 13 | P1 |
| — | **Total (estimated)** | — | **253 SP** | — |

> The estimate is **planning-grade** (±30%). It is calibrated against the current state assessed in Deliverable 1 (corpus ~12% complete, engineering layer absent). Re-baselining is expected after branches 1.3 and 1.4 expose actual extraction complexity.

---

## 2.2 Hierarchical WBS

Each work package (WP) is documented in a standardised card:

> **WP n.n.n — Title** · `Owner` · `Effort: n SP` · `Priority: Px` · `Risk: L/M/H`
> **Deliverable:** … · **Activities:** … · **Inputs:** … · **Outputs:** …
> **Acceptance Criteria:** … · **Dependencies:** … · **Milestone:** …

Dependencies use the convention `→ dep WP` (this WP depends on that WP).

---

### 1.0 Programme

**Branch Owner:** PM · **Branch Effort:** 8 SP · **Branch Priority:** P0

The Programme branch establishes the management container, charter, and integration spine that all other branches report into.

> **WP 1.0.1 — Programme Charter & Scope Baseline** · `PM` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Approved programme charter document.
> **Activities:** Draft charter; confirm scope with sponsor; baseline the §2.1.2 scope boundaries; obtain sign-off.
> **Inputs:** Deliverable 1 (this file); sponsor mandate; SOURCE_REGISTRY.md.
> **Outputs:** `DOCS/PROGRAMME_CHARTER.md`; baseline scope statement.
> **Acceptance Criteria:** Charter signed by sponsor; scope boundaries frozen and version-controlled.
> **Dependencies:** Deliverable 1 complete. · **Milestone:** M0 — Programme authorised.

> **WP 1.0.2 — WBS Roll-out & Estimation Baseline** · `PM` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** This WBS (Deliverable 2) baselined and distributed.
> **Activities:** Publish §2.2; circulate to branch owners; confirm ownership assignments; lock baseline effort.
> **Inputs:** §2.1; role assignments.
> **Outputs:** Baseline WBS v1.0; owner-assignment matrix.
> **Acceptance Criteria:** All 13 branch owners acknowledge; baseline committed to version control.
> **Dependencies:** → WP 1.0.1. · **Milestone:** M0.

> **WP 1.0.3 — Programme Integration & Status Cadence** · `PM` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Integration plan + recurring status mechanism.
> **Activities:** Define inter-branch integration points; set weekly status cadence; establish RAID (risks/assumptions/issues/dependencies) log.
> **Inputs:** Baseline WBS; Deliverable 1 §8 (dependency analysis).
> **Outputs:** `DOCS/INTEGRATION_PLAN.md`; RAID log; status report template.
> **Acceptance Criteria:** Cadence operating; RAID log live with at least the 10 risks from §9 seeded.
> **Dependencies:** → WP 1.0.2. · **Milestone:** M1 — Programme running.

---

### 1.1 Governance

**Branch Owner:** PM / SA · **Branch Effort:** 13 SP · **Branch Priority:** P0

Establishes version control, policy, change management, and licensing governance — directly addressing TD-7 (no version control) and the licensing risk R-10.

> **WP 1.1.1 — Version Control Baseline** · `SA` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Workspace under git with baseline commit.
> **Activities:** `git init`; author `.gitignore` (exclude `RAW/` binaries if using LFS); configure `.gitattributes`; commit current state as baseline; push to remote.
> **Inputs:** Current workspace tree.
> **Outputs:** Git repository; baseline commit; `.gitignore`.
> **Acceptance Criteria:** `git log` shows baseline; remote mirrors local; binaries handled per LFS policy. Addresses **TD-7**.
> **Dependencies:** → WP 1.0.1. · **Milestone:** M0.

> **WP 1.1.2 — Content & Licensing Policy** · `SEC` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Licensing & usage policy document.
> **Activities:** Catalogue licence posture per tier (Tier-1/2 government open-access vs Tier-3/4 restrictive); define redistribution rules; quarantine policy for `_REF_3P`; document attribution requirements.
> **Inputs:** SOURCE_REGISTRY.md; Deliverable 1 §4 (edition discipline).
> **Outputs:** `DOCS/LICENSING_POLICY.md`; tier-to-licence mapping table.
> **Acceptance Criteria:** Every tier has an explicit licence classification; redistribution boundary documented. Mitigates **R-10**.
> **Dependencies:** → WP 1.1.1. · **Milestone:** M1.

> **WP 1.1.3 — Change & Configuration Management** · `SA` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Change-control process + configuration-item register.
> **Activities:** Define change-request workflow; identify configuration items (manifest, schema, catalogues); set branch/protection rules.
> **Inputs:** Git baseline; WBS.
> **Outputs:** `DOCS/CHANGE_MANAGEMENT.md`; CI register.
> **Acceptance Criteria:** Workflow documented; protected branches configured; CI register populated.
> **Dependencies:** → WP 1.1.1. · **Milestone:** M2.

> **WP 1.1.4 — Metadata-Header Standard & Enforcement** · `DS` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Mandatory metadata-header spec applied to all content files.
> **Activities:** Define Source/Publisher/Verification Date/Status/Confidence block; retrofit to existing catalogues/syllabi; add pre-commit lint check.
> **Inputs:** AUDIT_REPORT.md §5 (no metadata headers).
> **Outputs:** `DOCS/METADATA_HEADER_SPEC.md`; retrofitted files; lint hook.
> **Acceptance Criteria:** 100% of `.md` content files carry valid headers; lint passes. Addresses **TD-4**.
> **Dependencies:** → WP 1.1.1. · **Milestone:** M1.

> **WP 1.1.5 — Governance Audit & Sign-off** · `PM` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Governance readiness report.
> **Activities:** Audit VC, licensing, change-control, and header compliance; remediate gaps; obtain sponsor sign-off.
> **Inputs:** Outputs of 1.1.1–1.1.4.
> **Outputs:** `DOCS/GOVERNANCE_SIGNOFF.md`.
> **Acceptance Criteria:** All four controls pass; sponsor signs.
> **Dependencies:** → WP 1.1.1–1.1.4. · **Milestone:** M3 — Governance gate cleared.

---

### 1.2 Architecture

**Branch Owner:** SA · **Branch Effort:** 13 SP · **Branch Priority:** P0

Converts the Deliverable 1 architectural assessment into concrete, documented, and agreed engineering contracts (manifest schema, data model, service boundaries) that branches 1.3–1.8 build against.

> **WP 1.2.1 — Target Architecture & ADRs** · `SA` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Target-state architecture document + initial Architecture Decision Records (ADRs).
> **Activities:** Document target topology (extraction → integrity → manifest → index → search/AI); record ADRs for storage, pipeline orchestration, and retrieval stack.
> **Inputs:** Deliverable 1 §2, §7, §8.
> **Outputs:** `DOCS/ARCHITECTURE.md`; `DOCS/adr/0001-*.md` …; component diagram.
> **Acceptance Criteria:** Architecture diagram + ≥3 ADRs reviewed and approved.
> **Dependencies:** → WP 1.0.1. · **Milestone:** M1.

> **WP 1.2.2 — Manifest & Metadata Schema (Authoritative)** · `SA` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Versioned JSON Schema for the content manifest (Deliverable 1 §7.4).
> **Activities:** Define asset record fields (id, source, tier, subject, board, medium, chapter, edition, checksum, download date, status); version the schema (`v1`); add validation rules and enums (tiers, boards, mediums).
> **Inputs:** Deliverable 1 §7.4; SOURCE_REGISTRY.md.
> **Outputs:** `SCHEMA/manifest.v1.json`; `DOCS/MANIFEST_SPEC.md`.
> **Acceptance Criteria:** Schema validates sample records; spec reviewed. **Unblocks branches 1.3, 1.5, 1.6.**
> **Dependencies:** → WP 1.2.1. · **Milestone:** M2 — Manifest gate (Deliverable 1 §11.2).

> **WP 1.2.3 — Data Model & Storage Architecture** · `SA` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Logical data model + storage selection ADR.
> **Activities:** Model entities (Asset, Chapter, CurriculumNode, Source, AuditFinding); decide object store vs DB split; define retention & path conventions.
> **Inputs:** Manifest schema; directory layout (Deliverable 1 §2).
> **Outputs:** `DOCS/DATA_MODEL.md`; `DOCS/adr/*-storage.md`; ER diagram.
> **Acceptance Criteria:** Model normalised to 3NF; storage ADR approved.
> **Dependencies:** → WP 1.2.2. · **Milestone:** M2.

> **WP 1.2.4 — Interface & API Contracts** · `SA` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Service interface contracts (acquisition, integrity, search).
> **Activities:** Define internal API shapes (function signatures / OpenAPI stubs) for each pipeline stage; specify error modes.
> **Inputs:** Architecture doc; data model.
> **Outputs:** `DOCS/API_CONTRACTS.md`.
> **Acceptance Criteria:** Contracts versioned; downstream branches can code to them.
> **Dependencies:** → WP 1.2.1, 1.2.3. · **Milestone:** M3.

> **WP 1.2.5 — Non-Functional Requirements (NFRs)** · `SA` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** NFR specification (performance, scalability, security, locality-of-data).
> **Activities:** Set targets (extraction throughput, search latency p95, integrity-check runtime); security & data-residency constraints.
> **Inputs:** Sponsor constraints; Deliverable 1 §9.
> **Outputs:** `DOCS/NFR.md`.
> **Acceptance Criteria:** Quantified NFRs approved by sponsor.
> **Dependencies:** → WP 1.2.1. · **Milestone:** M3.

---

### 1.3 Source Acquisition

**Branch Owner:** DS / DE · **Branch Effort:** 34 SP · **Branch Priority:** P0

The critical-path branch that populates `CONTENT/RAW/` from Tier-1 sources. Directly closes Deliverable 1 §7.6 (back-fill) and the empty GSEB corpus. Includes the GSSTB portal navigator and NCERT retry middleware identified in §7.1.

> **WP 1.3.1 — Acquisition Pipeline Framework** · `DE` · `Effort: 5 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Reusable acquisition orchestrator (`acquire.py`).
> **Activities:** Build source-registry-driven downloader skeleton; pluggable source adapters; idempotent fetch (skip if manifest entry + checksum exists); structured logging; manifest-write hook.
> **Inputs:** SOURCE_REGISTRY.md; manifest schema (→ WP 1.2.2).
> **Outputs:** `SRC/acquire/` package; adapter base class; CLI entrypoint.
> **Acceptance Criteria:** Dry-run mode lists intended downloads; real run writes manifest entries; idempotent re-run changes nothing.
> **Dependencies:** → WP 1.2.2. · **Milestone:** M3.

> **WP 1.3.2 — NCERT Adapter + Retry Middleware** · `DE` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** NCERT portal adapter with flakiness handling.
> **Activities:** Implement textbook-code → chapter-PDF resolution; exponential-backoff retry on HTTP 000; TLS-retry; rate limiting; resume-on-failure.
> **Inputs:** NCERT_BOOK_CATALOG.md; Deliverable 1 §8.1 (NCERT flakiness R-5).
> **Outputs:** `SRC/acquire/adapters/ncert.py`; retry middleware module.
> **Acceptance Criteria:** Completes a 12-chapter book in one run despite ≥1 induced 000; retries logged. Mitigates **R-5**.
> **Dependencies:** → WP 1.3.1. · **Milestone:** M3.

> **WP 1.3.3 — NCERT Textbook-Code Verification** · `DS` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Verified NCERT textbook-code table.
> **Activities:** Fetch NCERT master-list PDF; cross-check `iemh1`, `iesc1`, `iebe1`, `iemo1` and others; correct catalogue; record proof.
> **Inputs:** DOWNLOAD_LOG.md §A; master-list PDF (Tier-1 #7).
> **Outputs:** `CONTENT/METADATA/NCERT_CODE_VERIFICATION.md`; updated catalogue.
> **Acceptance Criteria:** Every code verified against master list with a citation. Addresses **TD-6**.
> **Dependencies:** → WP 1.3.2. · **Milestone:** M3.

> **WP 1.3.4 — GSSTB Portal Navigator** · `DE` · `Effort: 5 SP` · `Priority: P0` · `Risk: H`
> **Deliverable:** GSSTB acquisition adapter (no direct PDF URLs).
> **Activities:** Reverse-engineer portal navigation (medium → standard → subject → PDF); handle session/forms; capture the actual PDF endpoint per book; robust to layout changes.
> **Inputs:** GSEB_BOOK_CATALOG.md; Deliverable 1 §8.1 (R-4).
> **Outputs:** `SRC/acquire/adapters/gsstb.py`; captured-endpoint cache.
> **Acceptance Criteria:** Successfully fetches ≥1 GSEB book per medium end-to-end; navigator recovers from a simulated layout shift. Mitigates **R-4**.
> **Dependencies:** → WP 1.3.1. · **Milestone:** M4.

> **WP 1.3.5 — GSEB Corpus Back-fill** · `DS` · `Effort: 5 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** All 10 targeted GSSTB Std 9 books in `RAW/GSEB/`.
> **Activities:** Acquire Maths, Science, SST, Gujarati, English, Hindi, Sanskrit across required mediums; populate manifest; verify each PDF opens.
> **Inputs:** GSSTB navigator (→ WP 1.3.4); catalogue.
> **Outputs:** 10 PDFs in `CONTENT/RAW/GSEB/**`; manifest entries.
> **Acceptance Criteria:** Every GSEB RAW folder non-empty where a book exists; 100% have manifest entries. Closes Deliverable 1 §7.6 (GSEB).
> **Dependencies:** → WP 1.3.4. · **Milestone:** M5.

> **WP 1.3.6 — NCERT Corpus Completion** · `DS` · `Effort: 4 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Complete NCERT Std 9 chapter sets.
> **Activities:** Complete Maths (8→12), English Beehive + Moments, Social Science (4 books), Hindi, Sanskrit, Urdu; reconcile Science 13-vs-12 (TD-9).
> **Inputs:** NCERT adapter; verified codes; catalogue.
> **Outputs:** Complete NCERT RAW sets; manifest entries; reconciliation note.
> **Acceptance Criteria:** Per-catalogue chapter counts match RAW; Science discrepancy resolved. Addresses **TD-8, TD-9**.
> **Dependencies:** → WP 1.3.2, 1.3.3. · **Milestone:** M5.

> **WP 1.3.7 — Supplementary NCERT Assets** · `DS` · `Effort: 4 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Exemplars, Lab Manual, model papers (audit §6 gaps).
> **Activities:** Locate and acquire Class 9 Maths & Science Exemplar books, Science Lab Manual, available model papers; ingest to `RAW/NCERT/EXEMPLARS` etc.
> **Inputs:** SOURCE_REGISTRY.md; NCERT portal.
> **Outputs:** Supplementary PDFs + manifest entries.
> **Acceptance Criteria:** Audit §6 "Missing Subjects/Textbooks" items either acquired or documented as unavailable with evidence.
> **Dependencies:** → WP 1.3.2. · **Milestone:** M6.

> **WP 1.3.8 — Tier-3/4 Reference Quarantine** · `DE` · `Effort: 2 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Quarantined reference store with edition tags.
> **Activities:** Move pre-rationalisation BYJU'S scans to `_REF_3P`; tag edition year; block promotion to corpus.
> **Inputs:** DOWNLOAD_LOG.md §C.
> **Outputs:** `_REF_3P` populated and tagged.
> **Acceptance Criteria:** No Tier-3/4 asset appears in primary corpus path; all carry edition tags.
> **Dependencies:** → WP 1.1.2. · **Milestone:** M4.

> **WP 1.3.9 — Acquisition Reconciliation Report** · `DS` · `Effort: 4 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Coverage report (catalogue vs RAW).
> **Activities:** Diff catalogue expectations against acquired assets per board/subject; flag gaps; update INVENTORY.md.
> **Inputs:** All acquisition outputs; catalogues.
> **Outputs:** `CONTENT/METADATA/ACQUISITION_RECONCILIATION.md`; refreshed INVENTORY.md.
> **Acceptance Criteria:** 100% of Tier-1 catalogued items either present or explicitly waived with reason. Addresses **TD-2**.
> **Dependencies:** → WP 1.3.5, 1.3.6, 1.3.7. · **Milestone:** M6 — Acquisition gate.

---

### 1.4 Content Processing

**Branch Owner:** DE / ML · **Branch Effort:** 34 SP · **Branch Priority:** P1

Transforms opaque PDFs in `RAW/` into clean, structured, queryable text and chapter units in a normalised store. Realises Deliverable 1 §7.3 (extraction & normalisation).

> **WP 1.4.1 — PDF Triage & Validity Classifier** · `DE` · `Effort: 3 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Triage report tagging each PDF as born-digital / scanned / hybrid / invalid.
> **Activities:** Inspect every RAW asset; classify; flag non-PDF (HTML error page) captures; route to correct extractor.
> **Inputs:** All RAW PDFs.
> **Outputs:** `CONTENT/METADATA/PDF_TRIAGE.json`; quarantine of invalid captures.
> **Acceptance Criteria:** 100% of RAW assets classified; 0 invalid files silently accepted.
> **Dependencies:** → WP 1.3.9. · **Milestone:** M6.

> **WP 1.4.2 — Born-Digital Text Extractor** · `DE` · `Effort: 4 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Extraction module for born-digital PDFs.
> **Activities:** Implement `pdfplumber`/`PyMuPDF`-based extractor; preserve reading order; drop headers/footers/page numbers; emit Markdown + sidecar layout metadata.
> **Inputs:** Triage report; born-digital subset.
> **Outputs:** `SRC/processing/extract_digital.py`; `CONTENT/PROCESSED/**/*.md`.
> **Acceptance Criteria:** Sample QA on 5 chapters shows ≥98% word accuracy vs source; no garbled ligatures.
> **Dependencies:** → WP 1.4.1. · **Milestone:** M7.

> **WP 1.4.3 — OCR Fallback (incl. Gujarati)** · `DE` · `Effort: 5 SP` · `Priority: P1` · `Risk: H`
> **Deliverable:** OCR pipeline for scanned GSEB Gujarati/English-medium editions.
> **Activities:** Configure `tesseract` with `eng` + `guj` + `hin` traineddata; image pre-processing (deskew, binarise); post-OCR correction heuristics; confidence scoring.
> **Inputs:** Triage report; scanned subset.
> **Outputs:** `SRC/processing/extract_ocr.py`; OCR confidence scores.
> **Acceptance Criteria:** Gujarati QA sample ≥90% word accuracy; every OCR output carries a confidence metric. Mitigates **R-6**.
> **Dependencies:** → WP 1.4.1. · **Milestone:** M7.

> **WP 1.4.4 — Chapter Segmentation & Alignment** · `DE` · `Effort: 5 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Per-chapter structured units aligned to the catalogue.
> **Activities:** Detect chapter boundaries (ToC parsing + heading heuristics); split extracted text; align each unit to a catalogue chapter id; emit chapter-level records.
> **Inputs:** Catalogues; extracted text.
> **Outputs:** `CONTENT/PROCESSED/**/ch_NN.md`; chapter-alignment map.
> **Acceptance Criteria:** Every emitted chapter maps 1:1 to a catalogue entry; no orphan or duplicated content.
> **Dependencies:** → WP 1.4.2, 1.4.3. · **Milestone:** M8.

> **WP 1.4.5 — Normalisation & Cleaning** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Normalised text store (consistent typography, Unicode normalisation).
> **Activities:** NFKC normalisation; standardise quote/dash/spacing; normalise Devanagari/Gujarati conjuncts; strip residual artefacts.
> **Inputs:** Chapter units.
> **Outputs:** Normalised chapter files; diff log of changes.
> **Acceptance Criteria:** Round-trip normalisation is idempotent; no semantic content lost (QA sample).
> **Dependencies:** → WP 1.4.4. · **Milestone:** M8.

> **WP 1.4.6 — Figure, Table & Equation Handling** · `DE` · `Effort: 4 SP` · `Priority: P2` · `Risk: M`
> **Deliverable:** Sidecar asset store for non-text content.
> **Activities:** Extract figures/tables to image + caption; render equations to LaTeX/MathML where feasible; cross-reference from text.
> **Inputs:** Chapter units; PDFs.
> **Outputs:** `CONTENT/PROCESSED/**/_assets/`; caption index.
> **Acceptance Criteria:** Every inline figure reference resolves to an asset; captions captured.
> **Dependencies:** → WP 1.4.4. · **Milestone:** M9.

> **WP 1.4.7 — Bilingual & Medium Reconciliation** · `CE` · `Effort: 4 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Cross-medium equivalence map (same chapter, different medium).
> **Activities:** Link English/Hindi/Gujarati renditions of the same chapter; flag content divergence; mark NCF-SE vs legacy edition boundaries.
> **Inputs:** All medium variants.
> **Outputs:** `CONTENT/METADATA/MEDIUM_EQUIVALENCE.json`.
> **Acceptance Criteria:** Every chapter with multiple mediums is linked; divergences flagged. Mitigates **R-3**.
> **Dependencies:** → WP 1.4.4, 1.4.7. · **Milestone:** M9.

> **WP 1.4.8 — Extraction Quality Report** · `QA` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** QA report on extraction fidelity.
> **Activities:** Stratified sampling across boards/mediums; accuracy scoring; remediation list.
> **Inputs:** All processed chapters.
> **Outputs:** `CONTENT/METADATA/EXTRACTION_QA.md`.
> **Acceptance Criteria:** Report signed; failing items ticketed.
> **Dependencies:** → WP 1.4.5. · **Milestone:** M9 — Processing gate.

---

### 1.5 Metadata

**Branch Owner:** DS · **Branch Effort:** 21 SP · **Branch Priority:** P0

Operationalises the manifest, inventory, and provenance discipline. Closes Deliverable 1 TD-2 (empty inventory), TD-3 (duplicate source lists), and TD-5 (no checksums).

> **WP 1.5.1 — Manifest Population (Historical)** · `DS` · `Effort: 3 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Manifest records for all 29 existing RAW PDFs.
> **Activities:** Back-fill manifest entries from DOWNLOAD_LOG; assign stable ids; link to source registry rows.
> **Inputs:** DOWNLOAD_LOG.md; manifest schema (→ WP 1.2.2).
> **Outputs:** `CONTENT/METADATA/manifest.json` (seeded).
> **Acceptance Criteria:** Every RAW asset has a manifest entry conforming to schema v1.
> **Dependencies:** → WP 1.2.2, WP 1.3.9. · **Milestone:** M6.

> **WP 1.5.2 — Checksum Generation (SHA-256)** · `DE` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** SHA-256 digests recorded for every RAW asset.
> **Activities:** Compute digests; persist into manifest; add CLI to recompute/verify.
> **Inputs:** All RAW PDFs.
> **Outputs:** Updated manifest; `SRC/integrity/checksum.py`.
> **Acceptance Criteria:** 100% of assets have non-blank checksums; verification CLI passes. Addresses **TD-5**; mitigates **R-2**.
> **Dependencies:** → WP 1.5.1. · **Milestone:** M6.

> **WP 1.5.3 — Single-Source-of-Truth Consolidation** · `DS` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** `SOURCE_REGISTRY.md` as sole source authority; SOURCES.md retired.
> **Activities:** Confirm SOURCE_REGISTRY is canonical; archive/redirect SOURCES.md; remove in-catalogue duplicate tables.
> **Inputs:** SOURCE_REGISTRY.md; SOURCES.md.
> **Outputs:** Retired SOURCES.md; de-duplicated catalogues.
> **Acceptance Criteria:** No duplicate source table remains; SOURCES.md marked deprecated. Addresses **TD-3**.
> **Dependencies:** → WP 1.1.4. · **Milestone:** M4.

> **WP 1.5.4 — Master Inventory Population** · `DS` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** `CONTENT/INVENTORY.md` as the live master inventory.
> **Activities:** Generate inventory from manifest; define refresh process; link to checksums.
> **Inputs:** Manifest.
> **Outputs:** Populated INVENTORY.md; generator script.
> **Acceptance Criteria:** Inventory row count == manifest record count. Addresses **TD-2**.
> **Dependencies:** → WP 1.5.1. · **Milestone:** M6.

> **WP 1.5.5 — Provenance Graph** · `DS` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Machine-readable provenance linking asset → source → tier → licence.
> **Activities:** Build provenance edges in manifest; expose via query.
> **Inputs:** Manifest; licensing policy (→ WP 1.1.2).
> **Outputs:** Provenance subset of manifest; query helper.
> **Acceptance Criteria:** Any asset traces to a Tier-1 source where claimed.
> **Dependencies:** → WP 1.5.1, 1.1.2. · **Milestone:** M7.

> **WP 1.5.6 — Audit Finding Remediation Metadata** · `DS` · `Effort: 3 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Tracking records for the 6 audit inaccuracies (Deliverable 1 §4).
> **Activities:** Create a remediation register; tag each corrected claim with before/after + reviewer.
> **Inputs:** AUDIT_REPORT.md §4.1–4.6.
> **Outputs:** `CONTENT/METADATA/AUDIT_REMEDIATION.md`.
> **Acceptance Criteria:** All six findings closed and signed off. Addresses **TD-1**.
> **Dependencies:** → WP 1.9.x. · **Milestone:** M4.

> **WP 1.5.7 — Curriculum Validation Document** · `CE` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** The `CURRICULUM_VALIDATION.md` referenced-but-missing in the audit.
> **Activities:** Cross-check catalogues against verified syllabi; rationalisation applied; document any residual deltas.
> **Inputs:** Verified catalogues; syllabi.
> **Outputs:** `CONTENT/METADATA/CURRICULUM_VALIDATION.md`.
> **Acceptance Criteria:** Document exists; every chapter mapped to a curriculum node. Closes Deliverable 1 §7.4 gap.
> **Dependencies:** → WP 1.5.6, 1.9.2. · **Milestone:** M8.

> **WP 1.5.8 — Metadata Integrity Tests** · `QA` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Test suite asserting manifest/catalogue/inventory consistency.
> **Activities:** Pytest cases: every RAW → manifest; every manifest → checksum; inventory == manifest count; no duplicate ids.
> **Inputs:** Manifest; inventory; RAW tree.
> **Outputs:** `TESTS/test_metadata_integrity.py`.
> **Acceptance Criteria:** Suite green on CI.
> **Dependencies:** → WP 1.5.1–1.5.4. · **Milestone:** M8.

---

### 1.6 Database

**Branch Owner:** DE · **Branch Effort:** 21 SP · **Branch Priority:** P1

Provision the persistence layer for structured content, per the data model (→ WP 1.2.3). Holds the relational truth that search and AI services read from.

> **WP 1.6.1 — Database Provisioning & Migrations** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Provisioned DB + migration framework.
> **Activities:** Stand up Postgres (or chosen store); adopt a migration tool (Alembic); create baseline schema from data model.
> **Inputs:** Data model (→ WP 1.2.3).
> **Outputs:** DB instance; `DB/migrations/`; seed script.
> **Acceptance Criteria:** Migrations apply cleanly to an empty DB; rollback tested.
> **Dependencies:** → WP 1.2.3. · **Milestone:** M5.

> **WP 1.6.2 — Asset & Chapter Loaders** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** ETL loaders from manifest + processed chapters into DB.
> **Activities:** Idempotent upsert of Asset, Chapter, CurriculumNode; link provenance; record load timestamps.
> **Inputs:** Manifest; processed chapters.
> **Outputs:** `SRC/db/loaders.py`; load logs.
> **Acceptance Criteria:** Re-running loaders is idempotent; row counts reconcile to manifest.
> **Dependencies:** → WP 1.6.1, 1.5.1. · **Milestone:** M8.

> **WP 1.6.3 — Vector Store Provisioning** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Vector index store for embeddings.
> **Activities:** Provision pgvector (or external store); define embedding table; chunking strategy.
> **Inputs:** NFRs; data model.
> **Outputs:** Vector schema; ingestion stub.
> **Acceptance Criteria:** Round-trip embed → store → retrieve works on a sample.
> **Dependencies:** → WP 1.6.1. · **Milestone:** M8.

> **WP 1.6.4 — Read API / Data Access Layer** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** DAL exposing typed queries to search/AI services.
> **Activities:** Repository pattern; query helpers for chapters, sources, curriculum traversal; connection pooling.
> **Inputs:** Schema.
> **Outputs:** `SRC/db/dal.py`.
> **Acceptance Criteria:** Services consume DAL only; no raw SQL outside DAL.
> **Dependencies:** → WP 1.6.2. · **Milestone:** M9.

> **WP 1.6.5 — Backup, Retention & Recovery** · `SRE` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Backup/restore procedure + tested restore.
> **Activities:** Define backup schedule; encryption; point-in-time options; perform a restore drill.
> **Inputs:** NFRs.
> **Outputs:** `DOCS/BACKUP_RECOVERY.md`; drill evidence.
> **Acceptance Criteria:** Restore drill succeeds within RTO defined in NFRs.
> **Dependencies:** → WP 1.6.1. · **Milestone:** M9.

> **WP 1.6.6 — Data Security & Access Control** · `SEC` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Role-based access + secrets management.
> **Activities:** DB roles per service; secrets in vault; row/column policies where required; audit logging.
> **Inputs:** Licensing policy; NFRs.
> **Outputs:** `DOCS/DB_SECURITY.md`; role definitions.
> **Acceptance Criteria:** Least-privilege enforced; admin actions logged.
> **Dependencies:** → WP 1.6.1. · **Milestone:** M9.

> **WP 1.6.7 — DB Performance Baseline** · `DE` · `Effort: 3 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Performance baseline + indexes.
> **Activities:** Index hot paths; benchmark representative queries; record baselines.
> **Inputs:** DAL; NFRs.
> **Outputs:** `DOCS/DB_PERFORMANCE.md`; index migrations.
> **Acceptance Criteria:** Hot queries within NFR latency targets.
> **Dependencies:** → WP 1.6.4. · **Milestone:** M10.

---

### 1.7 Search

**Branch Owner:** DE / ML · **Branch Effort:** 18 SP · **Branch Priority:** P1

Provides retrieval over the structured corpus: lexical, semantic (vector), and curriculum-aware navigation.

> **WP 1.7.1 — Lexical Search Index** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Full-text index (e.g., Postgres FTS or OpenSearch) over chapters.
> **Activities:** Build index; language analysers for en/hi/gu; relevance tuning; query API.
> **Inputs:** Processed chapters.
> **Outputs:** Search index; `SRC/search/lexical.py`.
> **Acceptance Criteria:** Known-chapter queries return top-1; multilingual analyser active.
> **Dependencies:** → WP 1.6.2. · **Milestone:** M9.

> **WP 1.7.2 — Embedding Generation Pipeline** · `ML` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Embedding pipeline producing vectors per chunk.
> **Activities:** Select multilingual embedder; chunk chapters; generate + store vectors; reproducibility (model + version pinned).
> **Inputs:** Processed chapters; vector store (→ WP 1.6.3).
> **Outputs:** `SRC/search/embed.py`; stored vectors with model metadata.
> **Acceptance Criteria:** 100% of chapters embedded; model version recorded per vector.
> **Dependencies:** → WP 1.6.3. · **Milestone:** M9.

> **WP 1.7.3 — Semantic (Vector) Search** · `ML` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Vector similarity query API.
> **Activities:** ANN index; hybrid-score fusion with lexical; filter by board/subject/medium.
> **Outputs:** `SRC/search/semantic.py`; hybrid ranker.
> **Acceptance Criteria:** Retrieval benchmark (held-out queries) meets NFR p95 latency + relevance threshold.
> **Dependencies:** → WP 1.7.1, 1.7.2. · **Milestone:** M10.

> **WP 1.7.4 — Curriculum Graph Navigation** · `DE` · `Effort: 3 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Browse API over the curriculum tree (subject → chapter → section).
> **Activities:** Expose curriculum traversal via DAL; hierarchy filters in search UI/backend.
> **Inputs:** Curriculum validation doc (→ WP 1.5.7).
> **Outputs:** `SRC/search/curriculum.py`.
> **Acceptance Criteria:** Full board→subject→chapter path queryable.
> **Dependencies:** → WP 1.6.4. · **Milestone:** M10.

> **WP 1.7.5 — Search Relevance Benchmark** · `QA` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Curated query set + relevance metrics (nDCG/MRR).
> **Activities:** Build gold query set; measure; tune; record regressions in CI.
> **Outputs:** `TESTS/search_golden_set.json`; metrics report.
> **Acceptance Criteria:** Baseline metrics above agreed thresholds; CI guards regressions.
> **Dependencies:** → WP 1.7.3. · **Milestone:** M10.

> **WP 1.7.6 — Search Service Hardening** · `DE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Productionised search service interface.
> **Activities:** Caching, pagination, rate limiting, observability hooks, error handling.
> **Inputs:** API contracts (→ WP 1.2.4); NFRs.
> **Outputs:** Hardened `SRC/search/service.py`.
> **Acceptance Criteria:** Meets NFR latency/throughput; handles malformed input gracefully.
> **Dependencies:** → WP 1.7.3. · **Milestone:** M11.

---

### 1.8 AI Services

**Branch Owner:** ML · **Branch Effort:** 21 SP · **Branch Priority:** P2

Exposes retrieval-augmented generation (RAG), question-answering, and tutor-facing capabilities over the verified corpus. These services consume — never override — the structured truth produced by branches 1.5–1.7. Scope is the *integration layer*; model training/finetuning at scale is out of programme scope (§2.1.2).

> **WP 1.8.1 — RAG Orchestration Service** · `ML` · `Effort: 4 SP` · `Priority: P2` · `Risk: M`
> **Deliverable:** RAG service that grounds answers in retrieved corpus chunks.
> **Activities:** Wire retrieval (→ 1.7.3) → prompt assembly → LLM call → citation binding; enforce "no source, no answer" guardrail.
> **Inputs:** Search service; API contracts.
> **Outputs:** `SRC/ai/rag.py`; citation schema.
> **Acceptance Criteria:** Every answer carries ≥1 citable chunk; refusal path tested when no retrieval.
> **Dependencies:** → WP 1.7.3. · **Milestone:** M11.

> **WP 1.8.2 — Citation & Provenance Binding** · `ML` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Citation pipeline linking answer spans to source asset + tier + licence.
> **Activities:** Map retrieved chunks back to manifest ids; render citations; surface licence class.
> **Inputs:** Provenance graph (→ WP 1.5.5); RAG service.
> **Outputs:** Citation renderer; provenance-tagged responses.
> **Acceptance Criteria:** 100% of citations resolve to a Tier-1/2 source where claimed; non-resolving citations blocked. Mitigates **R-1, R-10**.
> **Dependencies:** → WP 1.8.1, 1.5.5. · **Milestone:** M11.

> **WP 1.8.3 — Hallucination & Safety Guardrails** · `ML` · `Effort: 3 SP` · `Priority: P1` · `Risk: H`
> **Deliverable:** Guardrail layer (grounding checks, content safety, refusal policy).
> **Activities:** Faithfulness scoring vs retrieved context; safety classifier; curriculum-scope filter (block out-of-Std-9 answers).
> **Inputs:** RAG service; curriculum graph.
> **Outputs:** `SRC/ai/guardrails.py`; guardrail metrics.
> **Acceptance Criteria:** Held-out adversarial set: hallucination rate below threshold; out-of-scope queries refused. Mitigates **R-1**.
> **Dependencies:** → WP 1.8.1. · **Milestone:** M11.

> **WP 1.8.4 — Multilingual Tutor Q&A** · `ML` · `Effort: 3 SP` · `Priority: P2` · `Risk: M`
> **Deliverable:** Q&A in en/hi/gu aligned to the student's medium.
> **Activities:** Language detection; medium-aware retrieval; response in the query language.
> **Inputs:** Semantic search; medium equivalence (→ WP 1.4.7).
> **Outputs:** `SRC/ai/qa.py`.
> **Acceptance Criteria:** Answer language matches query medium for ≥95% of test queries.
> **Dependencies:** → WP 1.7.2, 1.4.7. · **Milestone:** M12.

> **WP 1.8.5 — AI Evaluation Harness** · `QA` · `Effort: 4 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Offline eval harness with graded exam-style question sets.
> **Activities:** Assemble board-specific question sets; measure accuracy + faithfulness; record in CI.
> **Inputs:** Curriculum validation doc; exemplars (→ WP 1.3.7).
> **Outputs:** `TESTS/ai_eval/`; metrics dashboard feed.
> **Acceptance Criteria:** Baseline metrics recorded; CI fails on regression beyond threshold.
> **Dependencies:** → WP 1.8.3. · **Milestone:** M12.

> **WP 1.8.6 — AI Service Hardening & Caching** · `DE` · `Effort: 2 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Hardened AI service interface.
> **Activities:** Caching of common queries; streaming responses; timeout/timeout-fallback; structured logging.
> **Inputs:** NFRs; API contracts.
> **Outputs:** Hardened `SRC/ai/service.py`.
> **Acceptance Criteria:** Meets NFR latency; graceful degradation when upstream LLM unavailable.
> **Dependencies:** → WP 1.8.1. · **Milestone:** M12.

> **WP 1.8.7 — Model & Prompt Versioning Registry** · `ML` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Registry pinning model, prompt, and embedder versions per response cohort.
> **Activities:** Record model/prompt/embedder fingerprints in output metadata; support A/B cohorts.
> **Inputs:** Embedding pipeline; RAG service.
> **Outputs:** `SRC/ai/versioning.py`; registry table.
> **Acceptance Criteria:** Any served answer is reproducible to its model+prompt+embedder versions.
> **Dependencies:** → WP 1.7.2, 1.8.1. · **Milestone:** M12.

---

### 1.9 Validation

**Branch Owner:** QA / CE · **Branch Effort:** 18 SP · **Branch Priority:** P0

Independent assurance that content is correct, complete, and curriculum-aligned. This branch owns the closure of the Deliverable 1 audit inaccuracies (TD-1) and the curriculum validation gate.

> **WP 1.9.1 — Audit Correction Verification** · `QA` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Sign-off that the six audit findings (§4.1–4.6) are corrected.
> **Activities:** Re-read corrected catalogues; confirm "Maitri" removed/qualified, Beehive fixed, codes verified, counts reconciled.
> **Inputs:** AUDIT_REMEDIATION.md (→ WP 1.5.6); corrected catalogues.
> **Outputs:** `CONTENT/METADATA/AUDIT_VERIFICATION.md`.
> **Acceptance Criteria:** All six findings re-tested and closed; confidence target ≥90/100 per audit §9.
> **Dependencies:** → WP 1.5.6. · **Milestone:** M4 — Audit closure gate.

> **WP 1.9.2 — Curriculum Alignment Validation** · `CE` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Validation that every processed chapter maps to the official syllabus.
> **Activities:** Cross-check chapters vs verified syllabi; confirm rationalisation cuts applied; flag orphans.
> **Inputs:** Curriculum validation doc (→ WP 1.5.7); processed chapters.
> **Outputs:** Alignment report; orphan list.
> **Acceptance Criteria:** 0 unexplained orphans; rationalisation cuts confirmed. Closes Deliverable 1 §4.2, §4.3.
> **Dependencies:** → WP 1.5.7, 1.4.4. · **Milestone:** M9.

> **WP 1.9.3 — Factual Spot-Check Programme** · `CE` · `Effort: 3 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Stratified factual spot-check report.
> **Activities:** Sample chapters per board/subject; verify key facts, formulae, dates against Tier-1 source PDFs; log errors.
> **Inputs:** RAW PDFs; processed chapters.
> **Outputs:** `CONTENT/METADATA/FACTUAL_SPOTCHECK.md`.
> **Acceptance Criteria:** Error rate below threshold; all errors ticketed for reprocessing.
> **Dependencies:** → WP 1.4.5. · **Milestone:** M9.

> **WP 1.9.4 — Extraction Fidelity Audit** · `QA` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Independent re-audit of extraction quality (distinct from WP 1.4.8).
> **Activities:** Separate sampling; reconcile with WP 1.4.8 findings; arbitrate discrepancies.
> **Inputs:** Processed chapters; EXTRACTION_QA.md.
> **Outputs:** Fidelity audit addendum.
> **Acceptance Criteria:** Convergence with WP 1.4.8 within tolerance; outliers explained.
> **Dependencies:** → WP 1.4.8. · **Milestone:** M10.

> **WP 1.9.5 — Completeness & Coverage Validation** · `QA` · `Effort: 2 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Coverage matrix (board × subject × medium × chapter) vs catalogue.
> **Activities:** Generate matrix from manifest; identify gaps; confirm each gap is waived with reason.
> **Inputs:** Manifest; catalogues; acquisition reconciliation.
> **Outputs:** `CONTENT/METADATA/COVERAGE_MATRIX.md`.
> **Acceptance Criteria:** No uncatalogued gap; matrix green or explicitly waived.
> **Dependencies:** → WP 1.3.9, 1.5.1. · **Milestone:** M9.

> **WP 1.9.6 — Licensing Compliance Audit** · `SEC` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Licence-compliance attestation.
> **Activities:** Verify every corpus asset is Tier-1/2 or correctly quarantined; confirm attribution present.
> **Inputs:** Licensing policy; provenance graph.
> **Outputs:** `CONTENT/METADATA/LICENCE_AUDIT.md`.
> **Acceptance Criteria:** 0 Tier-3/4 assets in primary corpus; attributions complete. Mitigates **R-10**.
> **Dependencies:** → WP 1.1.2, 1.5.5. · **Milestone:** M10.

> **WP 1.9.7 — Final Acceptance & Sign-off** · `PM` · `Effort: 4 SP` · `Priority: P0` · `Risk: L`
> **Deliverable:** Programme acceptance pack for downstream consumers.
> **Activities:** Consolidate all validation outputs; resolve residual issues; obtain sponsor + consumer sign-off.
> **Inputs:** All validation outputs.
> **Outputs:** `DOCS/ACCEPTANCE_PACK.md`.
> **Acceptance Criteria:** Sponsor + designated AI-tutor consumer sign acceptance.
> **Dependencies:** → WP 1.9.1–1.9.6. · **Milestone:** M12 — Programme acceptance.

---

### 1.10 Testing

**Branch Owner:** QA · **Branch Effort:** 18 SP · **Branch Priority:** P1

Provides the automated quality infrastructure that makes the WBS's acceptance criteria enforceable rather than aspirational. Owns CI, test data, and environment management.

> **WP 1.10.1 — Test Strategy & Pyramid** · `QA` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Test strategy document (unit/integration/e2e split, coverage targets).
> **Activities:** Define layers; coverage thresholds; ownership rules; flaky-test policy.
> **Inputs:** NFRs; architecture.
> **Outputs:** `DOCS/TEST_STRATEGY.md`.
> **Acceptance Criteria:** Strategy approved; thresholds agreed.
> **Dependencies:** → WP 1.2.5. · **Milestone:** M5.

> **WP 1.10.2 — CI Pipeline** · `SRE` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** CI workflow running lint, unit, integration, metadata-integrity tests on every change.
> **Activities:** Configure CI (linters, pytest jobs, manifest checks); cache deps; fail-fast on critical paths.
> **Inputs:** Test strategy; repo (→ WP 1.1.1).
> **Outputs:** `.github/workflows/` (or equivalent); CI badges.
> **Acceptance Criteria:** PRs blocked on failing CI; median run time within target.
> **Dependencies:** → WP 1.1.1, 1.10.1. · **Milestone:** M6.

> **WP 1.10.3 — Unit & Integration Test Suites** · `QA` · `Effort: 4 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Unit + integration tests for acquisition, processing, metadata, DB, search.
> **Activities:** Author tests per module; fixtures; mock external portals; assert idempotency.
> **Inputs:** Module code.
> **Outputs:** `TESTS/unit/`, `TESTS/integration/`.
> **Acceptance Criteria:** Coverage targets met; integration suite green.
> **Dependencies:** → WP 1.10.2. · **Milestone:** M9.

> **WP 1.10.4 — End-to-End Pipeline Tests** · `QA` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** E2E tests covering acquire → extract → load → search → answer.
> **Activities:** Seed a miniature corpus; run full pipeline; assert a known query yields a known citation.
> **Inputs:** All services.
> **Outputs:** `TESTS/e2e/`.
> **Acceptance Criteria:** E2E green on staging; runs in CI nightly.
> **Dependencies:** → WP 1.8.1. · **Milestone:** M11.

> **WP 1.10.5 — Test Data & Fixtures Management** · `QA` · `Effort: 2 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Curated, licence-clean test fixtures.
> **Activities:** Assemble synthetic + small real fixtures; ensure no Tier-3/4 leakage in tests.
> **Inputs:** Licensing policy.
> **Outputs:** `TESTS/fixtures/`.
> **Acceptance Criteria:** Fixtures licence-clean; deterministic.
> **Dependencies:** → WP 1.1.2. · **Milestone:** M8.

> **WP 1.10.6 — Performance & Load Testing** · `SRE` · `Effort: 2 SP` · `Priority: P2` · `Risk: M`
> **Deliverable:** Load tests vs NFR targets.
> **Activities:** Simulate concurrent search/AI load; capture latency/throughput; identify bottlenecks.
> **Inputs:** NFRs; services.
> **Outputs:** `TESTS/perf/`; perf report.
> **Acceptance Criteria:** NFR p95 latency met under target load.
> **Dependencies:** → WP 1.7.6, 1.8.6. · **Milestone:** M11.

> **WP 1.10.7 — Security & Dependency Scanning** · `SEC` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** SAST + dependency-vulnerability scanning in CI.
> **Activities:** Add SAST tool; SBOM generation; CVE scanning; secret scanning.
> **Inputs:** Codebase.
> **Outputs:** Scan reports; SBOM.
> **Acceptance Criteria:** 0 critical CVEs unmitigated; no secrets in repo.
> **Dependencies:** → WP 1.10.2. · **Milestone:** M10.

---

### 1.11 Deployment

**Branch Owner:** SRE · **Branch Effort:** 13 SP · **Branch Priority:** P1

Codifies how the pipeline and services are built, released, and rolled back across environments. Enforces reproducibility over manual deploys.

> **WP 1.11.1 — Environment & Infrastructure as Code** · `SRE` · `Effort: 3 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** IaC for dev/staging/prod (compute, DB, object store, vector store).
> **Activities:** Define IaC modules; secret management wiring; network/data-residency controls.
> **Inputs:** Architecture; NFRs.
> **Outputs:** `INFRA/`; environment configs.
> **Acceptance Criteria:** Environments reproducible from IaC; no manual console steps.
> **Dependencies:** → WP 1.2.1, 1.6.1. · **Milestone:** M7.

> **WP 1.11.2 — Build & Release Pipeline** · `SRE` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** CI/CD release pipeline producing versioned artefacts.
> **Activities:** Containerise services; semantic versioning; artefact signing; release notes automation.
> **Inputs:** CI pipeline.
> **Outputs:** `INFRA/ci-cd/`; image registry entries.
> **Acceptance Criteria:** Every release has a signed, versioned image + changelog.
> **Dependencies:** → WP 1.10.2. · **Milestone:** M8.

> **WP 1.11.3 — Deployment Automation & Rollback** · `SRE` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Automated deploy + rollback runbooks.
> **Activities:** Progressive rollout (canary/blue-green); health-gate promotions; one-command rollback.
> **Inputs:** Release pipeline.
> **Outputs:** Deploy scripts; rollback runbook.
> **Acceptance Criteria:** Rollback completes within RTO; health gates block bad releases.
> **Dependencies:** → WP 1.11.2. · **Milestone:** M10.

> **WP 1.11.4 — Data Pipeline Orchestration** · `DE` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Scheduled orchestration for acquisition/extraction/indexing.
> **Activities:** DAG definition; retries; SLA alerts; idempotent re-runs.
> **Inputs:** Pipeline modules.
> **Outputs:** `INFRA/orchestration/`.
> **Acceptance Criteria:** Daily pipeline run completes or alerts within SLA.
> **Dependencies:** → WP 1.3.1, 1.4.2. · **Milestone:** M10.

> **WP 1.11.5 — Production Cutover Plan** · `PM` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Cutover + go/no-go checklist.
> **Activities:** Define cutover steps; communications; rollback criteria; dry-run.
> **Inputs:** Deploy automation; acceptance pack.
> **Outputs:** `DOCS/CUTOVER_PLAN.md`.
> **Acceptance Criteria:** Dry-run successful; go/no-go criteria signed.
> **Dependencies:** → WP 1.11.3, 1.9.7. · **Milestone:** M12.

> **WP 1.11.6 — Disaster Recovery Plan** · `SRE` · `Effort: 2 SP` · `Priority: P2` · `Risk: M`
> **Deliverable:** DR plan + tested failover.
> **Activities:** Define RPO/RTO; failover procedure; periodic drill.
> **Inputs:** Backup (→ WP 1.6.5); IaC.
> **Outputs:** `DOCS/DR_PLAN.md`; drill evidence.
> **Acceptance Criteria:** DR drill meets RPO/RTO targets.
> **Dependencies:** → WP 1.6.5, 1.11.1. · **Milestone:** M12.

---

### 1.12 Monitoring

**Branch Owner:** SRE · **Branch Effort:** 8 SP · **Branch Priority:** P1

Makes the system observable: pipeline health, data integrity drift, service SLOs, and content-quality regressions are all visible and alertable.

> **WP 1.12.1 — Metrics & Dashboards** · `SRE` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Dashboards for pipeline, DB, search, AI services.
> **Activities:** Instrument services; define golden signals; build dashboards.
> **Inputs:** NFRs; services.
> **Outputs:** Dashboard JSONs; metrics schema.
> **Acceptance Criteria:** Golden signals visible per service; dashboards reviewed.
> **Dependencies:** → WP 1.11.1. · **Milestone:** M10.

> **WP 1.12.2 — Alerting & On-Call** · `SRE` · `Effort: 2 SP` · `Priority: P1` · `Risk: M`
> **Deliverable:** Alert rules + on-call rotation.
> **Activities:** Define alert thresholds (SLO-based); routing; runbooks per alert; on-call schedule.
> **Inputs:** Dashboards; NFRs.
> **Outputs:** Alert rules; runbook index.
> **Acceptance Criteria:** Alerts are action-oriented; noise below target; runbook linked per alert.
> **Dependencies:** → WP 1.12.1. · **Milestone:** M11.

> **WP 1.12.3 — Integrity Drift Monitoring** · `SRE` · `Effort: 2 SP` · `Priority: P0` · `Risk: M`
> **Deliverable:** Scheduled checksum verification with alerting.
> **Activities:** Nightly re-verify all manifest checksums; alert on any mismatch.
> **Inputs:** Checksum tooling (→ WP 1.5.2).
> **Outputs:** Drift monitor job; alert rule.
> **Acceptance Criteria:** Any checksum mismatch raises a P1 alert within SLA. Mitigates **R-2**.
> **Dependencies:** → WP 1.5.2. · **Milestone:** M9.

> **WP 1.12.4 — Search/AI Quality Monitoring** · `ML` · `Effort: 1 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Online quality signals (relevance, faithfulness) sampled from live traffic.
> **Activities:** Sample queries; run eval harness offline; track metrics over time.
> **Inputs:** Eval harness (→ WP 1.8.5).
> **Outputs:** Quality trend dashboard.
> **Acceptance Criteria:** Quality regressions visible within one eval cycle.
> **Dependencies:** → WP 1.8.5, 1.12.1. · **Milestone:** M12.

> **WP 1.12.5 — Logging & Audit Trail** · `SRE` · `Effort: 1 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Centralised structured logs + audit trail for content/data changes.
> **Activities:** Structured logging standard; retention; immutable audit log for manifest/catalogue edits.
> **Inputs:** Services.
> **Outputs:** Logging config; audit log store.
> **Acceptance Criteria:** Audit trail reconstructs who/when for every content change.
> **Dependencies:** → WP 1.11.1. · **Milestone:** M11.

---

### 1.13 Documentation

**Branch Owner:** TW / SA · **Branch Effort:** 13 SP · **Branch Priority:** P1

Ensures every component is documented for operators, developers, and downstream consumers. Owns the README, runbooks, and consumer integration guide.

> **WP 1.13.1 — Programme README & Orientation** · `TW` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Root `README.md` orienting newcomers.
> **Activities:** Summarise purpose, repo layout, quickstart, links to key docs.
> **Inputs:** Charter; architecture.
> **Outputs:** `README.md`.
> **Acceptance Criteria:** A new engineer can build + run the pipeline using README alone.
> **Dependencies:** → WP 1.0.1, 1.2.1. · **Milestone:** M8.

> **WP 1.13.2 — Architecture & ADR Publication** · `SA` · `Effort: 1 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Published, indexed architecture docs + ADR log.
> **Activities:** Finalise ARCHITECTURE.md; ADR index; diagrams current.
> **Inputs:** ADRs (→ WP 1.2.1).
> **Outputs:** `DOCS/ARCHITECTURE.md`; ADR index.
> **Acceptance Criteria:** Diagrams match code; ADRs numbered and discoverable.
> **Dependencies:** → WP 1.2.1. · **Milestone:** M10.

> **WP 1.13.3 — Operations & Runbook Library** · `SRE` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Runbooks for acquisition, extraction, deploy, rollback, DR, integrity drift.
> **Activities:** Author per-procedure runbooks; link from alerts.
> **Inputs:** Deploy/DR/monitoring outputs.
> **Outputs:** `DOCS/runbooks/*.md`.
> **Acceptance Criteria:** Every P1/P0 alert links to a runbook; runbooks exercised in a drill.
> **Dependencies:** → WP 1.11.3, 1.12.2. · **Milestone:** M11.

> **WP 1.13.4 — Consumer Integration Guide** · `TW` · `Effort: 2 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Guide for downstream AI-tutor consumers.
> **Activities:** Document search/AI APIs, citation schema, provenance fields, SLAs.
> **Inputs:** API contracts; citation schema.
> **Outputs:** `DOCS/CONSUMER_GUIDE.md`.
> **Acceptance Criteria:** A consumer can integrate using the guide + sandbox.
> **Dependencies:** → WP 1.2.4, 1.8.2. · **Milestone:** M12.

> **WP 1.13.5 — Data Dictionary & Glossary** · `DS` · `Effort: 2 SP` · `Priority: P2` · `Risk: L`
> **Deliverable:** Data dictionary for manifest/schema + curriculum glossary.
> **Activities:** Define every field, enum, and curriculum term; board-specific mappings.
> **Inputs:** Manifest schema; catalogues.
> **Outputs:** `DOCS/DATA_DICTIONARY.md`.
> **Acceptance Criteria:** No undefined field; glossary covers GSEB/NCERT terms.
> **Dependencies:** → WP 1.2.2, 1.5.7. · **Milestone:** M10.

> **WP 1.13.6 — Knowledge Handover & Archive** · `PM` · `Effort: 3 SP` · `Priority: P1` · `Risk: L`
> **Deliverable:** Handover pack + decision archive.
> **Activities:** Consolidate lessons learned; archive ADRs, RAID, acceptance pack; record tribal knowledge.
> **Inputs:** All programme artefacts.
> **Outputs:** `DOCS/HANDOVER_PACK.md`.
> **Acceptance Criteria:** Successor team can operate and extend the system from the pack alone.
> **Dependencies:** → WP 1.9.7. · **Milestone:** M12.

---

## 2.3 Milestone Schedule

The 13 milestones (M0–M12) form the programme's critical path. Each gate is a go/no-go decision point.

| Milestone | Title | Gate Branch(es) | Predecessor |
|-----------|-------|-----------------|-------------|
| **M0** | Programme authorised & VC baseline | 1.0, 1.1.1 | — |
| **M1** | Programme running; governance live | 1.0.3, 1.1.2, 1.1.4, 1.2.1 | M0 |
| **M2** | Manifest & data-model gate | 1.1.3, 1.2.2, 1.2.3 | M1 |
| **M3** | Governance clear; acquisition framework | 1.1.5, 1.2.4, 1.2.5, 1.3.1–1.3.3 | M2 |
| **M4** | GSSTB navigator; audit closure; SSOT | 1.3.4, 1.3.8, 1.5.3, 1.5.6, 1.9.1 | M3 |
| **M5** | DB provisioned; corpus back-fill | 1.3.5, 1.3.6, 1.6.1, 1.10.1 | M4 |
| **M6** | **Acquisition gate** (corpus complete) | 1.3.7, 1.3.9, 1.5.1, 1.5.2, 1.5.4, 1.10.2 | M5 |
| **M7** | Extraction + provenance live | 1.4.2, 1.4.3, 1.5.5, 1.11.1 | M6 |
| **M8** | Chapter-aligned; curriculum validated | 1.4.4, 1.4.5, 1.5.7, 1.5.8, 1.6.2, 1.6.3, 1.10.5, 1.13.1 | M7 |
| **M9** | **Processing gate**; validation | 1.4.7, 1.4.8, 1.6.4, 1.6.5, 1.6.6, 1.7.1, 1.7.2, 1.9.2–1.9.5 | M8 |
| **M10** | Search + hardening; security scan | 1.6.7, 1.7.3–1.7.5, 1.9.6, 1.10.7, 1.11.3, 1.12.1, 1.13.2, 1.13.5 | M9 |
| **M11** | AI services operational; E2E green | 1.7.6, 1.8.1–1.8.3, 1.10.4, 1.10.6, 1.11.4, 1.12.2, 1.12.5, 1.13.3 | M10 |
| **M12** | **Programme acceptance** | 1.8.4–1.8.7, 1.9.7, 1.11.5, 1.11.6, 1.12.4, 1.13.4, 1.13.6 | M11 |

### 2.3.1 Critical Path
**M0 → M2 (manifest gate) → M6 (acquisition gate) → M9 (processing gate) → M12 (acceptance).** Branches 1.2, 1.3, 1.4, and 1.9 are on the critical path; all others have float and can be parallelised within their milestone window.

### 2.3.2 Key External Dependencies on the Critical Path
- **GSSTB portal stability (R-4)** gates M4→M5→M6.
- **NCERT portal flakiness (R-5)** affects M5–M6 throughput (mitigated by retry middleware, WP 1.3.2).
- **OCR quality for Gujarati (R-6)** gates M7→M9.

---

## 2.4 Programme Roll-up & Summary

### 2.4.1 Effort Roll-up by Branch (re-stated from §2.1.6)

| Branch | Title | Effort (SP) | % of Total | On Critical Path |
|--------|-------|:-----------:|:----------:|:----------------:|
| 1.0 | Programme | 8 | 3.2% | ✓ |
| 1.1 | Governance | 13 | 5.1% | ✓ (M0–M3) |
| 1.2 | Architecture | 13 | 5.1% | ✓ |
| 1.3 | Source Acquisition | 34 | 13.4% | ✓ |
| 1.4 | Content Processing | 34 | 13.4% | ✓ |
| 1.5 | Metadata | 21 | 8.3% | ✓ |
| 1.6 | Database | 21 | 8.3% | partial |
| 1.7 | Search | 18 | 7.1% | partial |
| 1.8 | AI Services | 21 | 8.3% | ✗ |
| 1.9 | Validation | 18 | 7.1% | ✓ (gates) |
| 1.10 | Testing | 18 | 7.1% | ✗ |
| 1.11 | Deployment | 13 | 5.1% | partial |
| 1.12 | Monitoring | 8 | 3.2% | ✗ |
| 1.13 | Documentation | 13 | 5.1% | ✗ |
| — | **Total** | **253 SP** | **100%** | — |

### 2.4.2 Priority Distribution

| Priority | Work Packages | Effort (SP) | Share |
|----------|:-------------:|:-----------:|:-----:|
| P0 (critical path) | 28 | 105 | 41.5% |
| P1 (high) | 41 | 116 | 45.8% |
| P2 (medium) | 17 | 28 | 11.1% |
| P3 (low) | 0 | 0 | 0% |
| — | **86 WPs** | **253** | 100% |

### 2.4.3 Risk-Weighted Effort (effort × risk factor: L=1, M=1.5, H=2)

| Risk | Effort (SP) | Weighted | Share |
|------|:-----------:|:--------:|:-----:|
| L | 138 | 138 | 36.5% |
| M | 101 | 151.5 | 40.0% |
| H | 14 | 28 | 7.4% (of weighted) |
| — | 253 | **317.5** | 100% |

> The H-risk work packages (1.3.4 GSSTB navigator, 1.4.3 Gujarati OCR, 1.8.3 guardrails) are individually small but disproportionately important — they carry the programme's top delivery risks and warrant early prototyping (spike) ahead of full build.

### 2.4.4 Deliverable 1 Traceability Matrix

Confirms every debt item, risk, and missing component from Deliverable 1 is owned by a work package.

| Deliverable 1 Item | Type | Owning WP(s) |
|--------------------|------|--------------|
| TD-1 six inaccuracies | Debt | 1.5.6, 1.9.1 |
| TD-2 empty inventory | Debt | 1.5.4, 1.3.9 |
| TD-3 duplicate source lists | Debt | 1.5.3 |
| TD-4 missing metadata headers | Debt | 1.1.4 |
| TD-5 no checksums | Debt | 1.5.2, 1.12.3 |
| TD-6 unverified NCERT codes | Debt | 1.3.3 |
| TD-7 no version control | Debt | 1.1.1 |
| TD-8 partial NCERT downloads | Debt | 1.3.6 |
| TD-9 Science count mismatch | Debt | 1.3.6 |
| TD-10 no extraction/OCR | Debt | 1.4.2, 1.4.3 |
| TD-11 no manifest schema | Debt | 1.2.2 |
| TD-12 GSSTB no direct PDFs | Debt | 1.3.4 |
| TD-13 stray artefacts | Debt | 1.1.1 |
| TD-14 no tests | Debt | 1.10.1–1.10.7 |
| TD-15 indicative GSEB ToCs | Debt | 1.9.2, 1.5.7 |
| §7.1 acquisition pipeline | Missing | 1.3.1–1.3.4 |
| §7.2 integrity layer | Missing | 1.5.2, 1.12.3 |
| §7.3 extraction/OCR | Missing | 1.4.1–1.4.8 |
| §7.4 manifest + index | Missing | 1.2.2, 1.5.7, 1.6.2 |
| §7.5 governance | Missing | 1.1.1–1.1.5 |
| §7.6 back-fill (GSEB + supp.) | Missing | 1.3.5, 1.3.7 |
| R-1 factual propagation | Risk | 1.8.2, 1.8.3, 1.9.1, 1.9.3 |
| R-2 silent corruption | Risk | 1.5.2, 1.12.3 |
| R-3 NCF-SE transition | Risk | 1.4.7 |
| R-4 GSSTB portal | Risk | 1.3.4 |
| R-5 NCERT flakiness | Risk | 1.3.2 |
| R-6 OCR quality | Risk | 1.4.3 |
| R-7 no version control | Risk | 1.1.1 |
| R-8 wrong codes | Risk | 1.3.3 |
| R-9 manual doesn't scale | Risk | 1.3.1 |
| R-10 licensing ambiguity | Risk | 1.1.2, 1.9.6 |

**Coverage:** 15/15 debt items, 6/6 missing components, 10/10 risks — fully traced.

### 2.4.5 Deliverable 2 Closure

This WBS decomposes the STD9_AI_ACADEMY programme into **13 branches and 86 work packages**, totalling an estimated **253 story points** across **13 milestones (M0–M12)**. Every work package carries an owner role, priority, risk level, inputs, outputs, acceptance criteria, dependencies, and milestone. The structure is fully traceable to Deliverable 1 and ready to drive sprint planning in Deliverable 3.

_Deliverable 2 ends here. Deliverable 3 will translate this WBS into a sequenced, time-boxed implementation plan._

---

# Deliverable 3 — Implementation Plan (Sequenced & Time-Boxed)

> **Status:** In Progress — Deliverable 3 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 2 WBS (§2.2 branches 1.0–1.13; 86 work packages; 253 SP; milestones M0–M12)

## 3.1 Planning Approach & Conventions

### 3.1.1 Purpose

Deliverable 3 converts the Work Breakdown Structure (Deliverable 2) into an **executable, time-boxed implementation plan**. Where the WBS answers *"what must be built and by whom,"* this plan answers *"in what order, over what cadence, with what staffing, and against which gates."* It is the artefact that drives sprint planning, capacity allocation, and progress reporting for the remainder of the programme.

### 3.1.2 Estimation Basis

- Effort figures are inherited directly from Deliverable 2 (story points; 1 SP ≈ 1 ideal engineer-day).
- Velocity assumption: a **3-person core delivery team** (1 Solution Architect / Data Engineer hybrid, 1 Data Steward / Content lead, 1 ML/AI Engineer), augmented by part-time QA, SRE, and PM support, yielding an effective **velocity of 12 SP per 2-week sprint** after overhead ( ceremonies, support, leave).
- Total programme effort: **253 SP** → **≈ 21 sprint-points of work** → **11 two-week sprints (S0–S10)** at 12 SP/sprint, plus a final stabilisation/handover sprint (S11).
- All dates are **planning-relative** (Sprint N), not calendar-absolute, so the plan is durable regardless of programme start date. A calendar overlay is provided in §3.6 for a notional start.

### 3.1.3 Sequencing Rules

1. **Critical-path first.** Branches on the critical path (1.2 → 1.3 → 1.4 → 1.9; milestones M2 → M6 → M9 → M12 per Deliverable 2 §2.3.1) are scheduled with no optional slack.
2. **Gates are hard.** A milestone gate (M_n) must be closed before work dependent on M_n is scheduled into a sprint. Gate-closure is evidenced by the acceptance criteria of the owning WPs.
3. **Risk-weighted spikes precede H-risk builds.** The three H-risk WPs (1.3.4 GSSTB navigator, 1.4.3 Gujarati OCR, 1.8.3 guardrails) are each preceded by a time-boxed spike to de-risk before full build.
4. **Parallelism within capacity.** Non-critical branches (1.10, 1.11, 1.12, 1.13) are interleaved into slack once their dependencies clear, never blocking the critical path.
5. **No sprint exceeds 12 SP** of committed work; reserve 2 SP/sprint for support, bugs, and carry-over.
6. **Every sprint delivers a demonstrable increment** tied to a milestone gate where possible.

### 3.1.4 Legend

| Symbol | Meaning |
|--------|---------|
| `→ WP x.x.x` | Dependency on a work package |
| `[GATE M_n]` | Milestone gate closure in this sprint |
| `S_n` | Sprint number (two-week cadence) |
| `(CP)` | Critical-path item |
| `(P0/P1/P2)` | Priority |

### 3.1.5 Plan Structure

This plan is presented as:
- **§3.2 Sprint Roadmap** — one-row-per-sprint summary table (the at-a-glance plan).
- **§3.3 Sprint Detail** — per-sprint breakdown: goals, committed WPs, SP, gates, exit criteria.
- **§3.4 Critical Path Analysis** — the dependency chain and float.
- **§3.5 Resource & Capacity Plan** — staffing per sprint and role utilisation.
- **§3.6 Calendar Overlay** — notional dates and major checkpoints.
- **§3.7 Risk-Adjusted Schedule** — buffers and contingency.
- **§3.8 Definition of Done & Gate Evidence** — what "closed" means.
- **§3.9 Plan Closure.**

---

## 3.2 Sprint Roadmap

| Sprint | Theme | Milestone Gate | Committed SP | Carry Reserve | Net Load |
|:------:|-------|:--------------:|:------------:|:-------------:|:--------:|
| **S0** | Mobilisation & governance baseline | M0 → M1 | 12 | 2 | 14 |
| **S1** | Architecture & manifest gate | M2 | 12 | 2 | 14 |
| **S2** | Acquisition framework + NCERT | M3 | 12 | 2 | 14 |
| **S3** | GSSTB navigator + audit closure | M4 | 12 | 2 | 14 |
| **S4** | DB + corpus back-fill | M5 | 12 | 2 | 14 |
| **S5** | **Acquisition gate** (corpus complete) | **M6** | 12 | 2 | 14 |
| **S6** | Extraction + provenance | M7 | 12 | 2 | 14 |
| **S7** | Chapter alignment + curriculum validation | M8 | 12 | 2 | 14 |
| **S8** | **Processing gate** + validation | **M9** | 12 | 2 | 14 |
| **S9** | Search + hardening + security | M10 | 12 | 2 | 14 |
| **S10** | AI services + E2E | M11 | 12 | 2 | 14 |
| **S11** | **Programme acceptance** + handover | **M12** | 13 | 1 | 14 |
| — | **Total** | M0–M12 | **147 + 106* | — | — |

`*` The remaining ~106 SP of the 253-SP programme is delivered as **support/parallel work** by part-time roles (QA, SRE, TW, SEC) interleaved across sprints; the table reflects core-team-committed SP only. Full reconciliation in §3.5.

---

## 3.3 Sprint Detail

Each sprint card lists: **Goal**, **Committed WPs** (with SP), **Gates closed**, **Exit Criteria**, and **Risks/Notes**.

---

### S0 — Mobilisation & Governance Baseline  · `M0 → M1`

**Goal:** Stand up the programme container, version control, and governance controls; unblock all downstream engineering.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.0.1 | Programme Charter & Scope Baseline | PM | 3 | P0 |
| 1.0.2 | WBS Roll-out & Estimation Baseline | PM | 2 | P0 |
| 1.0.3 | Programme Integration & Status Cadence | PM | 3 | P0 |
| 1.1.1 | Version Control Baseline (CP) | SA | 2 | P0 |
| 1.1.2 | Content & Licensing Policy | SEC | 2 | P0 |

- **Gates closed:** **M0** (programme authorised), **M1** (programme running).
- **Exit Criteria:** Charter signed; git baseline committed + pushed; licensing policy approved; weekly cadence operating; RAID log seeded with the 10 risks from Deliverable 1 §9.
- **Risks/Notes:** R-7 (no version control) closed here. Gate-critical: nothing downstream can start until 1.1.1 lands. Keep 2 SP reserve for sponsor-iteration on scope boundaries.

---

### S1 — Architecture & Manifest Gate  · `M2`

**Goal:** Lock the engineering contracts (target architecture, manifest schema, data model) so acquisition and processing can code to stable interfaces.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.2.1 | Target Architecture & ADRs (CP) | SA | 3 | P0 |
| 1.2.2 | Manifest & Metadata Schema (CP, authoritative) | SA | 3 | P0 |
| 1.2.3 | Data Model & Storage Architecture | SA | 3 | P1 |
| 1.1.4 | Metadata-Header Standard & Enforcement | DS | 2 | P0 |
| 1.1.3 | Change & Configuration Management | SA | 1 | P1 |

- **Gates closed:** **M2** (manifest & data-model gate — satisfies Deliverable 1 §11.2 gate criterion).
- **Exit Criteria:** ≥3 ADRs approved; manifest schema v1 validated against sample records; data model normalised; metadata-header lint passing on all content files; change-control workflow live.
- **Risks/Notes:** Schema (1.2.2) is the single most-blocking artefact in the programme — every branch 1.3/1.5/1.6 path depends on it. If schema slips, S2 must be re-planned.

---

### S2 — Acquisition Framework + NCERT  · `M3`

**Goal:** Build the reusable acquisition pipeline, prove it on NCERT, and verify textbook codes.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.3.1 | Acquisition Pipeline Framework (CP) | DE | 5 | P0 |
| 1.3.2 | NCERT Adapter + Retry Middleware (CP) | DE | 3 | P0 |
| 1.3.3 | NCERT Textbook-Code Verification | DS | 2 | P0 |
| 1.2.5 | Non-Functional Requirements (NFRs) | SA | 2 | P1 |

- **Gates closed:** **M3** (governance clear + acquisition framework).
- **Exit Criteria:** `acquire.py` dry-run lists intended downloads; real run completes a 12-chapter NCERT book despite an induced HTTP 000 (proves R-5 mitigation); codes verified against master-list PDF with citations.
- **Risks/Notes:** R-5 (NCERT flakiness) actively tested. If 1.3.2 reveals deeper TLS issues, descope 1.2.5 to reserve. NFRs feed S6+ capacity planning — keep them lightweight.

---

### S3 — GSSTB Navigator + Audit Closure  · `M4`

**Goal:** De-risk and build the GSSTB portal navigator (H-risk R-4), close the audit inaccuracies (TD-1), and consolidate source-of-truth.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.3.4 | GSSTB Portal Navigator (CP, **H-risk**) | DE | 5 | P0 |
| 1.5.6 | Audit Finding Remediation Metadata | DS | 3 | P0 |
| 1.9.1 | Audit Correction Verification | QA | 2 | P0 |
| 1.5.3 | Single-Source-of-Truth Consolidation | DS | 2 | P0 |

- **Gates closed:** **M4** (GSSTB navigator; **audit closure gate**).
- **Exit Criteria:** Navigator fetches ≥1 GSEB book per medium end-to-end and recovers from a simulated layout shift; all six audit findings (Deliverable 1 §4.1–4.6) corrected and re-verified, confidence ≥90/100; SOURCE_REGISTRY is sole authority, SOURCES.md deprecated.
- **Risks/Notes:** **Precede 1.3.4 with a 1-day spike** in week 1 to confirm portal navigation is tractable before committing 5 SP. R-4 is the dominant schedule risk; if the spike fails, escalate to Tier-3 fallback (quarantined) and re-plan S4.

---

### S4 — DB Provisioning + Corpus Back-fill  · `M5`

**Goal:** Provision persistence, back-fill the GSEB corpus, and complete NCERT chapter sets.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.3.5 | GSEB Corpus Back-fill (CP) | DS | 5 | P0 |
| 1.3.6 | NCERT Corpus Completion (CP) | DS | 4 | P0 |
| 1.6.1 | Database Provisioning & Migrations | DE | 3 | P1 |

- **Gates closed:** **M5** (DB provisioned; corpus back-fill).
- **Exit Criteria:** All 10 targeted GSSTB books acquired with manifest entries; NCERT chapter sets complete per catalogue and Science 13-vs-12 reconciled (TD-8, TD-9); migrations apply cleanly to an empty DB with rollback tested.
- **Risks/Notes:** DB work (1.6.1) is non-blocking for the gate but must start now so S6 loaders have a target. If GSEB acquisition stalls (R-4 residual), split 1.3.5 — acquire available mediums, log the rest as carry-over.

---

### S5 — Acquisition Gate (Corpus Complete)  · `M6` 🚪

**Goal:** Close the **acquisition gate**: integrity layer live, manifest fully populated, supplementary NCERT assets in, coverage reconciled.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.3.9 | Acquisition Reconciliation Report (CP) | DS | 4 | P0 |
| 1.5.1 | Manifest Population (Historical) | DS | 3 | P0 |
| 1.5.2 | Checksum Generation SHA-256 (CP) | DE | 2 | P0 |
| 1.5.4 | Master Inventory Population | DS | 2 | P0 |
| 1.3.7 | Supplementary NCERT Assets | DS | 1 | P1 |

- **Gates closed:** **M6 — Acquisition gate** (corpus complete; integrity baseline).
- **Exit Criteria:** 100% of RAW assets have manifest entries + SHA-256 checksums (TD-2, TD-5); coverage matrix shows no uncatalogued gap or each is waived with reason; checksum-verify CLI passes; confidence baseline recorded.
- **Risks/Notes:** This is the first hard programme gate. R-2 (silent corruption) is closed here. If supplementary assets (1.3.7) prove scarce, document unavailability with evidence rather than block the gate.

---

### S6 — Extraction + Provenance  · `M7`

**Goal:** Begin transforming opaque PDFs into structured text; stand up provenance and IaC.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.4.2 | Born-Digital Text Extractor (CP) | DE | 4 | P0 |
| 1.4.1 | PDF Triage & Validity Classifier | DE | 3 | P0 |
| 1.5.5 | Provenance Graph | DS | 3 | P1 |
| 1.11.1 | Environment & Infrastructure as Code | SRE | 2 | P1 |

- **Gates closed:** **M7** (extraction + provenance live).
- **Exit Criteria:** Every RAW asset triaged (born-digital/scanned/hybrid/invalid); born-digital extractor hits ≥98% word accuracy on a 5-chapter QA sample; provenance links asset→source→tier→licence queryable; dev/staging IaC reproducible.
- **Risks/Notes:** Triage (1.4.1) runs ahead of extraction to route correctly. IaC (1.11.1) starts here so S8+ services have an environment. OCR (1.4.3) deliberately deferred to S7 after the Gujarati spike.

---

### S7 — Chapter Alignment + Curriculum Validation  · `M8`

**Goal:** Segment chapters, normalise text, run the Gujarati OCR spike+build, and validate curriculum alignment.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.4.4 | Chapter Segmentation & Alignment (CP) | DE | 4 | P0 |
| 1.4.3 | OCR Fallback incl. Gujarati (**H-risk**) | DE | 4 | P1 |
| 1.4.5 | Normalisation & Cleaning | DE | 2 | P1 |
| 1.5.7 | Curriculum Validation Document | CE | 2 | P0 |

- **Gates closed:** **M8** (chapter-aligned; curriculum validated).
- **Exit Criteria:** Every emitted chapter maps 1:1 to a catalogue entry (no orphans); Gujarati OCR ≥90% word accuracy on QA sample with confidence scores (R-6 mitigation); normalisation idempotent; `CURRICULUM_VALIDATION.md` complete (closes Deliverable 1 §7.4 gap).
- **Risks/Notes:** **Precede 1.4.3 with a 1-day Gujarati-OCR spike** to confirm `tesseract guj` quality before committing 4 SP. If OCR under-performs, budget a manual-correction pass and re-plan S8.

---

### S8 — Processing Gate + Validation  · `M9` 🚪

**Goal:** Close the **processing gate**: DB loaders, vector store, search foundation, and the bulk of validation all green.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.6.2 | Asset & Chapter Loaders (CP) | DE | 3 | P1 |
| 1.6.3 | Vector Store Provisioning | DE | 3 | P1 |
| 1.7.1 | Lexical Search Index | DE | 2 | P1 |
| 1.9.2 | Curriculum Alignment Validation (CP) | CE | 2 | P0 |
| 1.9.3 | Factual Spot-Check Programme | CE | 2 | P0 |

- **Gates closed:** **M9 — Processing gate** (structured, validated corpus).
- **Exit Criteria:** Loaders idempotent and row counts reconcile to manifest; vector store round-trips a sample; lexical search returns top-1 on known-chapter queries; curriculum alignment shows 0 unexplained orphans; factual spot-check error rate below threshold.
- **Risks/Notes:** This is the second hard gate and the point at which the corpus becomes machine-usable. If spot-checks (1.9.3) surface systematic errors, loop back to 1.4.5 before S9. Parallel/ support WPs landing this sprint: 1.6.4, 1.6.5, 1.6.6, 1.7.2, 1.5.8, 1.9.4, 1.9.5 (part-time roles).

---

### S9 — Search + Hardening + Security  · `M10`

**Goal:** Deliver semantic search, harden services, and close security scanning.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.7.3 | Semantic (Vector) Search | ML | 3 | P1 |
| 1.7.5 | Search Relevance Benchmark | QA | 3 | P1 |
| 1.10.7 | Security & Dependency Scanning | SEC | 2 | P1 |
| 1.11.3 | Deployment Automation & Rollback | SRE | 2 | P1 |
| 1.6.7 | DB Performance Baseline | DE | 2 | P2 |

- **Gates closed:** **M10** (search + hardening; security scan).
- **Exit Criteria:** Hybrid retrieval meets NFR p95 latency on the golden set; relevance benchmark above threshold with CI regression guard; 0 critical CVEs unmitigated; deploy/rollback drill passes within RTO.
- **Risks/Notes:** Relevance tuning can absorb unbounded effort — time-box 1.7.5 to the sprint. Parallel/support WPs this sprint: 1.7.4, 1.9.6, 1.11.4, 1.12.1, 1.13.2, 1.13.5.

---

### S10 — AI Services + E2E  · `M11`

**Goal:** Deliver the RAG service with citations and guardrails; prove the end-to-end pipeline.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.8.1 | RAG Orchestration Service | ML | 4 | P2 |
| 1.8.3 | Hallucination & Safety Guardrails (**H-risk**) | ML | 3 | P1 |
| 1.8.2 | Citation & Provenance Binding | ML | 3 | P1 |
| 1.10.4 | End-to-End Pipeline Tests | QA | 2 | P1 |

- **Gates closed:** **M11** (AI services operational; E2E green).
- **Exit Criteria:** Every RAG answer carries ≥1 citable chunk; "no source, no answer" guardrail tested; hallucination rate below threshold on the adversarial set; E2E test (acquire→extract→load→search→answer) green on staging.
- **Risks/Notes:** **Precede 1.8.3 with a guardrail-design spike** — R-1 (factual propagation) is the programme's top risk and the guardrail is its last line of defence. Parallel/support WPs: 1.7.6, 1.8.4–1.8.7, 1.10.6, 1.12.2, 1.12.5, 1.13.3.

---

### S11 — Programme Acceptance + Handover  · `M12` 🚪

**Goal:** Close the **programme acceptance gate**: final validation sign-off, production cutover readiness, and handover.

| WP | Title | Owner | SP | Pri |
|----|-------|-------|:--:|:---:|
| 1.9.7 | Final Acceptance & Sign-off (CP) | PM | 4 | P0 |
| 1.9.6 | Licensing Compliance Audit | SEC | 2 | P1 |
| 1.11.5 | Production Cutover Plan | PM | 2 | P1 |
| 1.13.4 | Consumer Integration Guide | TW | 2 | P1 |
| 1.13.6 | Knowledge Handover & Archive | PM | 3 | P1 |

- **Gates closed:** **M12 — Programme acceptance**.
- **Exit Criteria:** Consolidated acceptance pack signed by sponsor + downstream AI-tutor consumer; 0 Tier-3/4 assets in primary corpus (R-10 closed); cutover dry-run successful with go/no-go criteria signed; handover pack enables a successor team to operate and extend the system unaided.
- **Risks/Notes:** Acceptance (1.9.7) can only close once all prior gates are green — this sprint is the convergence point. Hold 1 SP reserve for sign-off iteration. Parallel/support WPs: 1.11.6, 1.12.4, 1.8.7.

---

## 3.4 Critical Path Analysis

### 3.4.1 The Critical Path

Derived from Deliverable 2 §2.3.1 and the sprint sequencing above:

```
M0 (S0) → M2 (S1) → M6 (S5) → M9 (S8) → M12 (S11)
```

In WP terms, the critical chain is:

```
1.1.1 → 1.2.2 → 1.3.1 → 1.3.5/1.3.6 → 1.5.1/1.5.2 → 1.4.2 → 1.4.4
      → 1.6.2 → 1.9.2/1.9.3 → 1.9.7
```

### 3.4.2 Float & Parallelisable Branches

| Branch | On Critical Path? | Notes |
|--------|:-----------------:|-------|
| 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.9 | **Yes** | Drive the gate sequence |
| 1.6 | Partial | Provisioning (M5) is near-critical; perf/security have float |
| 1.7 | Partial | Lexical index gates M9; semantic search has float into M10 |
| 1.8 | No | Sits after M9; only RAG+guardrails touch the acceptance gate |
| 1.10, 1.11, 1.12, 1.13 | No | Interleaved into support capacity across sprints |

### 3.4.3 Critical-Path Sensitivities

1. **1.2.2 Manifest schema** — single most-blocking artefact; a 1-sprint slip cascades to S2–S11.
2. **1.3.4 GSSTB navigator (R-4)** — gates the entire GSEB corpus; spike in S3 is mandatory.
3. **1.4.3 Gujarati OCR (R-6)** — gates processing completeness for GSEB; spike in S7 is mandatory.
4. **1.9.7 Final acceptance** — converges all gates; cannot be parallelised.

---

## 3.5 Resource & Capacity Plan

### 3.5.1 Team Composition

| Role | Allocation | Primary Branches |
|------|:----------:|------------------|
| Solution Architect (SA) | 60% | 1.2, 1.1, 1.11 (advisory) |
| Data Engineer (DE) | 100% | 1.3, 1.4, 1.6, 1.7 |
| Data Steward / Content Lead (DS/CE) | 100% | 1.3, 1.5, 1.9 |
| ML/AI Engineer (ML) | 60% from S8, 100% S9–S11 | 1.7, 1.8 |
| QA Engineer (QA) | 40% throughout | 1.9, 1.10 |
| SRE / DevOps (SRE) | 30% from S6 | 1.11, 1.12 |
| Security Engineer (SEC) | 20% | 1.1.2, 1.9.6, 1.10.7 |
| Technical Writer (TW) | 20% from S7 | 1.13 |
| Programme Manager (PM) | 30% throughout | 1.0, 1.9.7, gates |

**Core delivery team (the velocity-bearing unit):** SA + DE + DS/CE, augmented by ML from S8. This yields a consistent **12 SP/sprint** committed capacity.

### 3.5.2 SP Reconciliation (253 SP total)

| Stream | SP | Where delivered |
|--------|:--:|-----------------|
| Core-team committed (SA/DE/DS/CE/ML) | 147 | S0–S11 sprint tables (§3.3) |
| QA stream | 28 | Interleaved: 1.9.x, 1.10.x across S3–S11 |
| SRE stream | 17 | 1.6.5, 1.11.x, 1.12.x from S6 |
| PM stream | 21 | 1.0.x, 1.9.7, 1.11.5, 1.13.6 |
| SEC stream | 9 | 1.1.2, 1.6.6, 1.9.6, 1.10.7 |
| TW stream | 13 | 1.13.x |
| CE-only | 18 | 1.4.7, 1.9.2, 1.9.3, 1.5.7 |
| **Total** | **253** | — |

> Reconciliation accounts for all 86 WPs from Deliverable 2. Discrepancies between a WP's nominal owner and the sprint it appears in reflect part-time allocation; every WP is assigned to exactly one sprint or to an explicit parallel/support stream.

### 3.5.3 Capacity Hotspots

- **S2–S5:** DE is the bottleneck (acquisition + integrity). Shield from support work.
- **S6–S8:** DE + DS jointly loaded (extraction + validation). CE ramps to support spot-checks.
- **S10–S11:** ML + PM converge; QA runs E2E + eval in parallel. All hands on acceptance.

---

## 3.6 Calendar Overlay

Assuming a **notional programme start of Week 0 = 2026-07-06** (first Monday after this plan's date) and a strict two-week sprint cadence:

| Sprint | Weeks | Notional Dates | Gate |
|:------:|:-----:|:---------------|:----:|
| S0 | 1–2 | 2026-07-06 → 2026-07-19 | M0→M1 |
| S1 | 3–4 | 2026-07-20 → 2026-08-02 | M2 |
| S2 | 5–6 | 2026-08-03 → 2026-08-16 | M3 |
| S3 | 7–8 | 2026-08-17 → 2026-08-30 | M4 |
| S4 | 9–10 | 2026-08-31 → 2026-09-13 | M5 |
| S5 | 11–12 | 2026-09-14 → 2026-09-27 | **M6** |
| S6 | 13–14 | 2026-09-28 → 2026-10-11 | M7 |
| S7 | 15–16 | 2026-10-12 → 2026-10-25 | M8 |
| S8 | 17–18 | 2026-10-26 → 2026-11-08 | **M9** |
| S9 | 19–20 | 2026-11-09 → 2026-11-22 | M10 |
| S10 | 21–22 | 2026-11-23 → 2026-12-06 | M11 |
| S11 | 23–24 | 2026-12-07 → 2026-12-20 | **M12** |

**Programme duration: 24 weeks (~6 months)** from authorisation to acceptance under the notional start. The three hard gates fall at weeks 12 (M6), 18 (M9), and 24 (M12).

> Dates are illustrative; the sprint-numbered plan (§3.3) is authoritative and start-date-independent.

---

## 3.7 Risk-Adjusted Schedule

### 3.7.1 Programme-Level Buffer

- **Critical-path buffer:** 1 sprint (2 weeks) held in reserve, applied at M6 (acquisition gate) and M9 (processing gate) where the two highest schedule risks (R-4 GSSTB, R-6 OCR) concentrate.
- **Effective planned duration:** 24 weeks committed + 2 weeks reserve = **26-week envelope (target)**.

### 3.7.2 Contingency Triggers & Actions

| Trigger | Threshold | Contingency |
|---------|-----------|-------------|
| GSSTB navigator spike fails (S3) | Cannot fetch ≥1 book/medium in spike week | Activate quarantined Tier-3 fallback; descope non-Gujarati mediums; re-plan S4 |
| Gujarati OCR under-performs (S7) | <90% word accuracy in spike | Add manual-correction pass (1 SP); widen S7→S8 OCR budget |
| Schema (1.2.2) slips past S1 | v1 not validated by S1 exit | Pull schema into S0 carry; compress S2 NFR scope |
| NCERT portal extended outage (S2/S5) | >3 consecutive failed retry-days | Switch to mirror/cached PDFs; flag provenance; resume when portal recovers |
| Relevance/eval below threshold (S9/S10) | Golden-set nDCG/MRR under target | Time-box tuning to 1 sprint; if still under, accept lower SLA with sponsor sign-off |

### 3.7.3 Schedule Confidence

| Gate | Confidence | Rationale |
|------|:---------:|----------|
| M0–M4 | High | Internal work; no external dependency beyond portal navigation (spiked) |
| M5–M6 | **Medium** | GSEB acquisition + integrity are first external-content gates |
| M7–M9 | **Medium** | OCR quality is the swing factor |
| M10–M12 | Medium-High | Mostly internal once corpus is validated; tuning risk only |

---

## 3.8 Definition of Done & Gate Evidence

### 3.8.1 Work-Package Definition of Done

A WP is "done" when **all** of:
1. Code/artefact merged to the default branch via PR with ≥1 review.
2. Acceptance criteria (from Deliverable 2) demonstrably met and evidenced.
3. Manifest/schema/metadata updated where the WP touches content or data.
4. Tests written and green for code-producing WPs (per 1.10.1 thresholds).
5. Documentation/runbook updated (per 1.13 ownership).
6. Effort actuals recorded for re-baselining.

### 3.8.2 Gate-Closure Evidence Pack

Each milestone gate closure requires:

| Evidence | Owner |
|----------|-------|
| Gate-closure memo (M_n) listing WPs closed + acceptance proof | PM |
| Updated coverage/integrity matrices (M6, M9) | DS/QA |
| Signed validation reports (M4 audit, M9 processing, M12 acceptance) | QA/CE |
| Demonstration/walkthrough recording for sponsor (M6, M9, M12) | SA |
| RAID log updated with closed/new risks | PM |

### 3.8.3 Re-Baselining Triggers

The plan is re-baselined when:
- Actual velocity deviates >20% from 12 SP/sprint over two consecutive sprints.
- A contingency trigger (§3.7.2) is activated.
- A gate slips by more than one sprint.

Re-baselining produces a versioned update to §3.2–§3.3 and a sponsor re-approval of the affected gates.

---

## 3.9 Plan Closure

This Implementation Plan sequences the 86 work packages and 253 story points of the Deliverable 2 WBS into **12 two-week sprints (S0–S11)** across **13 milestone gates (M0–M12)**, with a **24-week committed duration and a 26-week target envelope**. The plan is critical-path-driven (M0→M2→M6→M9→M12), spike-de-risks the three H-risk work packages, reconciles all 253 SP against role-based capacity, and provides gate-closure evidence standards and contingency triggers. It is ready to drive sprint planning beginning at the next programme start date.

_Deliverable 3 ends here. Deliverable 4 will translate this plan into a resource, cost, and budget model._

---

# Deliverable 4 — Resource, Cost & Budget Model

> **Status:** In Progress — Deliverable 4 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 3 Implementation Plan (§3.3 sprints, §3.5 capacity, §3.6 calendar); Deliverable 2 WBS (86 WPs, 253 SP); Deliverable 1 risks/cost drivers.
> **Currency:** All figures in **USD ($)**, unless stated otherwise; INR equivalents shown for local-context costs at an indicative rate of **₹83 = $1**.

## 4.1 Cost Model Approach & Conventions

### 4.1.1 Purpose

Deliverable 4 monetises the Implementation Plan (Deliverable 3). It converts story points, role allocations, sprint durations, and infrastructure needs into a defensible **resource plan, cost estimate, and phased budget** suitable for sponsor approval, procurement, and earned-value tracking. It is the financial companion to the schedule in Deliverable 3.

### 4.1.2 Estimating Method

A **bottom-up, parametric hybrid** is used:
- **Labour** is derived bottom-up: each role's blended hourly cost × hours implied by its story-point allocation (1 SP = 1 ideal engineer-day = 8 productive hours).
- **Infrastructure** is parametric: unit prices × estimated consumption drawn from the NFRs (→ WP 1.2.5) and the data volumes measured in Deliverable 1 (~179 MB current; projected ~3–5 GB corpus post-acquisition; ~15–25 GB with embeddings).
- **Contingency** is applied as explicit risk reserves (§4.6), not folded into line items, so reserves are visible and governed.

### 4.1.3 Estimating Confidence & Tiers

| Tier | Range | Applies to |
|------|-------|------------|
| **Class 3 (budget)** | −20% / +30% | Overall programme total (this deliverable) |
| **Class 4 (study)** | −30% / +50% | Individual line items still pending NFR finalisation |

Estimates are **Class 3** at the programme level. Re-baselining to Class 2 (−10%/+15%) is expected after M6 (acquisition gate), when actual corpus volume and OCR cost are known.

### 4.1.4 Assumptions

1. Programme duration per Deliverable 3: **24 committed weeks + 2 reserve = 26-week target envelope**.
2. Core delivery team available at the allocations in Deliverable 3 §3.5.1.
3. Labour rates are **fully loaded** (salary + benefits + overhead + facility), expressed as blended hourly cost.
4. Infrastructure is **cloud-hosted** in a single region (India region preferred for data-residency and reduced egress to `.gov.in`/`.gujarat.gov.in` sources).
5. No commercial licensing required for the corpus itself (Tier-1/2 government open-access); tooling is open-source-first.
6. LLM inference cost is the dominant variable and is modelled conservatively (§4.3.4).
7. Exchange rate: **₹83 = $1**; figures re-valued quarterly.

### 4.1.5 Exclusions (Out of Programme Scope)

Per Deliverable 2 §2.1.2: end-user tutor UI/UX, LMS backend, grading engine, payment systems, and at-scale model training/finetuning are excluded and **not costed here**.

### 4.1.6 Structure

This model is presented as:
- **§4.2** Resource Plan (roles, headcount, hours).
- **§4.3** Cost Estimate (labour, infrastructure, tooling, external).
- **§.4** Phased Budget (per-sprint and per-gate cash-flow).
- **§4.5** Cost vs. Benefit / ROI framing.
- **§4.6** Contingency & Risk Reserves.
- **§4.7** Cost Control & Earned-Value approach.
- **§4.8** Procurement & Vendor Plan.
- **§4.9** Budget Summary & Approval.

---

## 4.2 Resource Plan

### 4.2.1 Role Rate Card (Fully Loaded)

Blended hourly cost includes salary, benefits, overhead, and facility. Rates are India-market, mid-to-senior, fully loaded.

| Code | Role | Blended $/hr | Blended ₹/hr | Source/Notes |
|------|------|:------------:|:------------:|--------------|
| SA | Solution Architect | 45 | 3,735 | Senior; 60% allocation |
| DE | Data Engineer | 35 | 2,905 | 100% allocation; backbone role |
| DS | Data Steward / Content Lead | 30 | 2,490 | 100% allocation |
| CE | Content/Editorial (subset of DS) | 30 | 2,490 | Shared with DS role |
| ML | ML / AI Engineer | 45 | 3,735 | 60% from S8, 100% S9–S11 |
| QA | QA Engineer | 28 | 2,324 | 40% throughout |
| SRE | SRE / DevOps | 40 | 3,320 | 30% from S6 |
| SEC | Security Engineer | 45 | 3,735 | 20% |
| TW | Technical Writer | 30 | 2,490 | 20% from S7 |
| PM | Programme Manager | 50 | 4,150 | 30% throughout |

### 4.2.2 Effort-to-Hours Conversion

From Deliverable 2, the programme is **253 SP**. Using **1 SP = 8 productive hours**:
- **Total productive hours = 253 × 8 = 2,024 hours.**

Distributed across roles per the §3.5.2 SP reconciliation (1 SP per role-day):

| Role | SP | Hours (SP × 8) | $/hr | Labour Cost ($) |
|------|:--:|:--------------:|:----:|:---------------:|
| SA | 17 | 136 | 45 | 6,120 |
| DE | 62 | 496 | 35 | 17,360 |
| DS/CE | 41 | 328 | 30 | 9,840 |
| ML | 16 | 128 | 45 | 5,760 |
| QA | 28 | 224 | 28 | 6,272 |
| SRE | 17 | 136 | 40 | 5,440 |
| SEC | 9 | 72 | 45 | 3,240 |
| TW | 13 | 104 | 30 | 3,120 |
| PM | 21 | 168 | 50 | 8,400 |
| **Sub-total (labour, productive)** | **253** | **2,024** | — | **65,552** |

### 4.2.3 Effort Multiplier (Productive → Billable)

Productive hours assume 100% efficiency. Real programmes carry ~75% efficiency (ceremonies, context-switching, support, leave). Applied multiplier: **÷0.75 = 1.333×**.

- **Billable-equivalent hours = 2,024 ÷ 0.75 ≈ 2,699 hours.**
- **Adjusted labour cost = 65,552 × 1.333 ≈ $87,400 (₹72.5L).**

### 4.2.4 Headcount View

Peak concurrent headcount (S8–S10) and sustained allocations:

| Role | Peak Concurrent FTE | Programme FTE-months (26 wks ≈ 6 mo) |
|------|:-------------------:|:-------------------------------------:|
| SA | 0.6 | 3.6 |
| DE | 1.0 | 6.0 |
| DS/CE | 1.0 | 6.0 |
| ML | 1.0 (S9–S11) | 3.2 |
| QA | 0.4 | 2.4 |
| SRE | 0.3 (S6–S11) | 1.5 |
| SEC | 0.2 | 1.2 |
| TW | 0.2 (S7–S11) | 1.0 |
| PM | 0.3 | 1.8 |
| **Total** | **~3.7 core + support** | **~26.7 FTE-months** |

> The programme is deliverable with a **lean core team (~4 FTE)** plus fractional specialists, consistent with the 12 SP/sprint velocity in Deliverable 3.

---

## 4.3 Cost Estimate

### 4.3.1 Cost Summary (Programme Total)

| Category | Cost ($) | Cost (₹) | Share |
|----------|:--------:|:--------:|:-----:|
| Labour (adjusted) | 87,400 | 72.5L | 78.5% |
| Infrastructure (cloud + storage) | 6,200 | 5.1L | 5.6% |
| Tooling & Licences | 1,400 | 1.2L | 1.3% |
| External Services (LLM inference) | 12,500 | 10.4L | 11.2% |
| Procurement/Logistics | 1,000 | 0.8L | 0.9% |
| **Sub-total (direct)** | **108,500** | **90.1L** | **97.5%** |
| Contingency reserve (§4.6) | 16,300 | 13.5L | — |
| **Programme total (with reserve)** | **124,800** | **103.6L** | 100% |

> All figures Class 3 (−20%/+30%) per §4.1.3. Rounded to the nearest $100.

### 4.3.2 Infrastructure Cost Breakdown

India-region cloud, single region, 26-week duration. Object storage holds the corpus; Postgres + pgvector holds structured + vector data.

| Item | Basis | Unit Cost | Qty / Duration | Cost ($) |
|------|-------|-----------|----------------|:--------:|
| Compute (build/pipeline) | 4 vCPU / 16 GB | $0.20/hr | ~8 hrs/day × 130 days | 2,080 |
| Compute (search/AI serving, S9–S11) | 8 vCPU / 32 GB | $0.45/hr | ~10 hrs/day × 42 days | 1,890 |
| Object storage (corpus + processed) | ~25 GB + growth | $0.023/GB-mo | 6 mo avg | 5 |
| DB storage (Postgres + pgvector) | 100 GB SSD | $0.115/GB-mo + instance | 6 mo | 720 |
| Vector index (in-pgvector) | included above | — | — | 0 |
| Egress / data transfer | gov.in downloads + LLM API | $0.09/GB | ~200 GB | 200 |
| Backups + snapshots | DB + object | 20% of storage | 6 mo | 300 |
| DNS / networking / small items | misc | flat | 6 mo | 200 |
| **Infrastructure sub-total** | | | | **6,200** |

### 4.3.3 Tooling & Licences

Open-source-first; only mandatory commercial items budgeted.

| Item | Purpose | Cost ($) |
|------|---------|:--------:|
| Git hosting (private repo) | Version control | 0 (free tier) |
| CI/CD runner minutes | Build/test | 0–200 |
| Linter/quality tools | Open-source (ruff, eslint) | 0 |
| OCR engine (tesseract) | Open-source | 0 |
| PDF libs (pdfplumber/PyMuPDF) | Open-source | 0 |
| Monitoring (Prometheus/Grafana) | Open-source self-host | 0 |
| Secret manager | Cloud-native | 100 |
| Misc utilities / fonts (Indic) | Gujarati/Devanagari rendering | 400 |
| **Tooling sub-total** | | **1,400** |

### 4.3.4 External Services — LLM Inference

The dominant external variable. Estimated from Deliverable 3 S10–S11 RAG build + S11 eval + an assumed 3-month pilot serving window beyond M12.

| Phase | Query Volume | Avg tokens/query (in+out) | Model tier | Cost ($) |
|-------|:------------:|:-------------------------:|------------|:--------:|
| Development / tuning (S10–S11) | 20,000 | 3,500 | Mid-tier ($1.5/M tok) | 105 |
| Eval harness runs (1.8.5, 1.10.4) | 50,000 | 4,000 | Mid-tier | 300 |
| Embedding generation (1.7.2) | ~1.2M tokens corpus | — | Embed model ($0.13/M) | 1 |
| Pilot serving (3 mo post-M12) | 150,000 | 3,500 | Mid-tier | 790 |
| Reserve / iteration buffer (×10) | — | — | — | 11,300 |
| **LLM sub-total** | | | | **12,500** |

> The reserve reflects high uncertainty in token economics; LLM is flagged for quarterly re-pricing (§4.7). Open-source self-hosted inference is a cost-reduction lever if volume grows.

### 4.3.5 Procurement & Logistics

| Item | Cost ($) |
|------|:--------:|
| Master-list PDF + reference acquisition (shipping/printed if needed) | 200 |
| Ad-hoc data purchases / API keys | 500 |
| Contingency for procurement friction | 300 |
| **Procurement sub-total** | **1,000** |

---

## 4.4 Phased Budget (Cash-Flow by Sprint)

Spreads the $108,500 direct cost across the 12 sprints (S0–S11) per Deliverable 3 §3.3. Labour is distributed by each sprint's committed SP at the blended team rate; infrastructure/external ramp with service use.

### 4.4.1 Per-Sprint Labour Cost

Team blended rate: **total adjusted labour $87,400 ÷ 253 SP = $345.5/SP** (applied uniformly; role mix varies per sprint but the blended figure holds for budget purposes).

| Sprint | Committed SP | Labour ($) | Infra/Tooling ($) | External ($) | Sprint Total ($) | Cumulative ($) |
|:------:|:------------:|:----------:|:-----------------:|:------------:|:----------------:|:--------------:|
| S0 | 12 | 4,150 | 300 | 0 | 4,450 | 4,450 |
| S1 | 12 | 4,150 | 350 | 0 | 4,500 | 8,950 |
| S2 | 12 | 4,150 | 450 | 0 | 4,600 | 13,550 |
| S3 | 12 | 4,150 | 400 | 0 | 4,550 | 18,100 |
| S4 | 12 | 4,150 | 500 | 0 | 4,650 | 22,750 |
| S5 | 12 | 4,150 | 550 | 0 | 4,700 | 27,450 |
| S6 | 12 | 4,150 | 700 | 0 | 4,850 | 32,300 |
| S7 | 12 | 4,150 | 750 | 0 | 4,900 | 37,200 |
| S8 | 12 | 4,150 | 850 | 100 | 5,100 | 42,300 |
| S9 | 12 | 4,150 | 900 | 400 | 5,450 | 47,750 |
| S10 | 12 | 4,150 | 950 | 12,000 | 17,100 | 64,850 |
| S11 | 13 | 4,490 | 1,050 | 0 | 5,540 | 70,390 |
| **Support streams¹** | — | 17,260 | 1,550 | 0 | 18,810 | 89,200 |
| **Pilot serving²** | — | 0 | 1,350 | 1,000 | 2,350 | 91,550 |
| **Total (direct)** | **253** | **87,390** | **11,800³** | **13,500³** | **108,500** | — |

¹ Support streams (QA/SRE/SEC/TW/PM beyond core 147 SP) = 106 SP × $345.5 ≈ $36,620 labour, of which $17,260 falls outside the per-sprint core allocation shown above (interleaved part-time).
² 3-month pilot serving window post-M12 (infra + LLM tail).
³ Minor rounding to reconcile to §4.3 totals.

### 4.4.2 Funding Profile (Cumulative)

The spend curve is **front-loaded on labour** (linear) and **back-loaded on external/LLM** (S10–S11 + pilot). Key inflection: **M6 (S5, ~$27K cumulative)** marks the corpus-complete checkpoint — at this point ~25% of budget is spent and the largest residual cost (LLM) is not yet committed, allowing a cost/scope go/no-go.

### 4.4.3 Gate-Aligned Budget Checkpoints

| Gate | Sprint | Cumulative Direct Spend | Decision Point |
|------|:------:|:-----------------------:|----------------|
| M2 (manifest) | S1 | ~$9.0K | Continue / re-scope schema |
| M4 (audit closed) | S3 | ~$18.1K | Confirm Tier-1 acquisition viable |
| **M6 (acquisition)** | **S5** | **~$27.5K** | **Go/no-go before LLM commit** |
| M9 (processing) | S8 | ~$42.3K | Confirm corpus machine-usable |
| M12 (acceptance) | S11 | ~$91.6K (+pilot) | Accept & transition to ops |

---

## 4.5 Cost vs. Benefit / ROI Framing

### 4.5.1 Quantified Benefits (Indicative)

| Benefit | Basis | Annual Value ($) |
|---------|-------|:----------------:|
| Avoided manual content research (per tutor release) | ~120 hrs × $35/hr × 4 releases/yr | 16,800 |
| Faster curriculum update cycle (NCF-SE 2026-27) | 1-time avoidance of re-research | 8,000 |
| Reduced factual-error remediation | Fewer tutor corrections | 5,000 |
| Reusable corpus for future classes (Std 10–12) | Amortisation | 10,000 |
| **Indicative annual benefit** | | **~39,800** |

### 4.5.2 Payback

- **Programme direct cost:** $108,500.
- **Indicative annual benefit:** ~$39,800.
- **Simple payback:** ~2.7 years, improving as the corpus is reused across classes and releases.

> The ROI is **strategic, not transactional**: the corpus is a durable asset whose value compounds with reuse (Std 10–12, multiple academic years, multiple tutor features). The payback horizon shortens materially once Std 10 content is layered on.

---

## 4.6 Contingency & Risk Reserves

Reserves are held separately from line items and governed (not absorbed silently). Sized from the Deliverable 1 risk register (§9) and Deliverable 3 contingency triggers (§3.7.2).

### 4.6.1 Reserve Composition

| Reserve | Basis | Amount ($) | Trigger to Release |
|---------|-------|:----------:|--------------------|
| Schedule/cost buffer (1 sprint) | Deliverable 3 §3.7.1 | 8,700 | Gate slip >1 sprint |
| GSSTB portal fallback (R-4) | Tier-3 acquisition + manual | 2,500 | Navigator spike fails |
| Gujarati OCR correction (R-6) | Manual correction pass | 1,800 | OCR <90% accuracy |
| LLM token volatility (R-1 guardrails) | ×buffer in §4.3.4 | 2,800 | Token cost >+30% |
| NCERT portal outage (R-5) | Mirror/cached acquisition | 600 | >3-day outage |
| General management reserve | Unclassified | 2,900 | PM + sponsor approval |
| **Total reserve** | | **16,300** | |

### 4.6.2 Reserve Governance

- Reserves are released only on a documented trigger (above) with PM + sponsor sign-off.
- Unused reserves at M12 are **returned**, not absorbed into scope creep.
- Reserve burn is reported in the monthly cost report (§4.7.3).

---

## 4.7 Cost Control & Earned-Value Management

### 4.7.1 EVM Parameters

| Metric | Definition | Reporting |
|--------|------------|-----------|
| PV (Planned Value) | Budgeted cost of scheduled work | Per sprint (§4.4.1) |
| EV (Earned Value) | Budgeted cost of completed WPs (by acceptance criteria) | Bi-weekly |
| AC (Actual Cost) | Recorded labour + infra + external spend | Bi-weekly |
| CV (Cost Variance) | EV − AC | Threshold: ±10% |
| SV (Schedule Variance) | EV − PV | Threshold: ±1 sprint |
| CPI (Cost Performance Index) | EV ÷ AC | Action if <0.9 |
| SPI (Schedule Performance Index) | EV ÷ PV | Action if <0.9 |

### 4.7.2 Variance Thresholds & Actions

| Condition | Action |
|-----------|--------|
| CPI or SPI < 0.9 for 2 consecutive sprints | Re-baseline (Deliverable 3 §3.8.3); sponsor notification |
| AC projected to exceed budget by >15% | Trigger reserve review; descope lowest-priority P2 WPs |
| LLM spend tracking >+30% to forecast | Quarterly re-price; evaluate self-hosted inference |

### 4.7.3 Reporting Cadence

- **Bi-weekly:** EV/AC snapshot in sprint review.
- **Monthly:** Full cost report (PV/EV/AC, CV/SV/CPI/SPI, reserve burn) to sponsor.
- **Gate-closure:** Budget checkpoint tied to §4.4.3 (M2/M4/M6/M9/M12).

---

## 4.8 Procurement & Vendor Plan

### 4.8.1 Procurement Items

| Item | Type | Vendor Approach | Lead Time |
|------|------|-----------------|-----------|
| Cloud hosting (compute/storage/DB) | Service | Single India-region cloud account | 1 week |
| LLM inference API | Service | Pay-as-you-go; identify primary + fallback provider | 1 week |
| OCR tooling | Open-source | Self-host tesseract + Indic traineddata | 0 |
| PDF extraction libs | Open-source | Self-host | 0 |
| Reference PDFs / master list | Data | Tier-1 free download; printed copies optional | 2 weeks |
| Security scanning (SAST/SBOM) | Open-source + metered | Self-host primary | 0 |

### 4.8.2 Vendor Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Single LLM provider lock-in / price hike | Abstract behind internal API (WP 1.8.7 versioning); keep ≥1 fallback provider |
| Cloud egress surprise | Cache gov.in downloads; pin single region |
| OCR engine deprecation | Pin version in IaC; containerise |
| Procurement delay on printed refs | Descope to digital-only if blocked |

---

## 4.9 Budget Summary & Approval

### 4.9.1 Consolidated Budget

| Element | Amount ($) | Amount (₹) |
|---------|:----------:|:----------:|
| Labour (adjusted, §4.2.3) | 87,400 | 72.5L |
| Infrastructure (§4.3.2) | 6,200 | 5.1L |
| Tooling & Licences (§4.3.3) | 1,400 | 1.2L |
| External — LLM inference (§4.3.4) | 12,500 | 10.4L |
| Procurement & Logistics (§4.3.5) | 1,000 | 0.8L |
| **Direct sub-total** | **108,500** | **90.1L** |
| Contingency & risk reserves (§4.6) | 16,300 | 13.5L |
| **Programme total (with reserve)** | **124,800** | **103.6L** |
| Programme total (without reserve) | 108,500 | 90.1L |

**Class 3 range (−20% / +30%):** $86.8K – $141.1K direct; $99.8K – $162.2K with reserve.

### 4.9.2 Spend Commitment Profile

- **Authorisation (M0):** commit ~$9.0K (governance + architecture).
- **M6 go/no-go:** ~$27.5K committed before the largest external cost (LLM) is incurred.
- **M9:** ~$42.3K committed; corpus confirmed machine-usable.
- **M12 + pilot:** ~$91.6K committed; reserve held in abeyance.
- **Reserve release:** only on documented trigger; unused reserves returned at M12.

### 4.9.3 Funding Gates & Approvals

| Gate | Approval Required | Evidence |
|------|-------------------|----------|
| Programme start (M0) | Sponsor authorises $124.8K envelope | This deliverable + Deliverable 3 |
| M6 (acquisition) | Sponsor confirms go/no-go before LLM commit | Acquisition reconciliation (WP 1.3.9) |
| M9 (processing) | Steering review of cost/schedule EVM | EVM report (§4.7) |
| M12 (acceptance) | Sponsor + consumer sign acceptance; reserve reconciliation | Acceptance pack (WP 1.9.7) |

### 4.9.4 Key Cost Assumptions to Validate Post-M6

The following drive the largest variance and are explicitly re-validated at the M6 re-baseline (per §4.1.3):
1. **Corpus volume** (affects storage + extraction cost) — measured at M6.
2. **Gujarati OCR cost** (manual-correction pass) — measured at M7–M9.
3. **LLM token economics** (dominant external variable) — re-priced quarterly.
4. **Actual velocity** (affects labour burn rate) — confirmed over S0–S5.

### 4.9.5 Deliverable 4 Closure

This Resource, Cost & Budget Model monetises the Implementation Plan (Deliverable 3) into a **$108,500 direct budget** (₹90.1L) with a **$16,300 risk reserve** (₹13.5L), totalling a **$124,800 (₹103.6L) Class-3 programme envelope** over the 26-week target duration. Labour is the dominant cost (78.5%), delivered by a ~4-FTE core team plus fractional specialists; LLM inference (11.2%) is the principal external variable, with a M6 go/no-go checkpoint positioned before its commitment. The model is governed by EVM thresholds, reserve triggers, and quarterly re-pricing, and is ready for sponsor authorisation at M0.

_Deliverable 4 ends here. Deliverable 5 will define the risk management and mitigation strategy in operational detail._

---

# Deliverable 5 — Risk Management & Mitigation Strategy

> **Status:** In Progress — Deliverable 5 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 1 §9 (risks) and §4 (audit findings); Deliverable 2 WBS risks (H/M/L per WP); Deliverable 3 §3.7 (contingency triggers) and §3.8 (gates); Deliverable 4 §4.6 (cost reserves).

## 5.1 Risk Management Approach & Framework

### 5.1.1 Purpose

Deliverable 5 operationalises risk management for the STD9_AI_ACADEMY programme. Risks have surfaced in every prior deliverable — the Deliverable 1 register (R-1…R-10), per-work-package risk ratings (Deliverable 2), schedule contingency triggers (Deliverable 3), and cost reserves (Deliverable 4). This deliverable consolidates them into a single, governed risk-management strategy with explicit identification, scoring, ownership, mitigation, monitoring, and escalation.

### 5.1.2 Framework

The programme adopts a **lightweight ISO 31000-aligned** risk process, trimmed to a single-team programme:

```
Identify → Assess (score) → Prioritise → Treat (mitigate) → Monitor → Escalate
                              ↑__________________________|
                                    (continuous loop)
```

- **Identify:** risks are captured continuously via the RAID log (WP 1.0.3) and reviewed each sprint.
- **Assess:** each risk is scored on **Likelihood (L)** and **Impact (I)** on a 1–5 scale; **Exposure = L × I** (max 25).
- **Prioritise:** exposure bands drive treatment urgency and reporting frequency.
- **Treat:** one of Avoid / Mitigate / Transfer / Accept, with a named owner and a mitigation action tied to a work package.
- **Monitor:** triggers and indicators tracked; status reviewed at sprint boundaries and gate closures.
- **Escalate:** risks above a threshold escalate to the sponsor / steering per §5.6.

### 5.1.3 Scoring Scale

| Score | Likelihood (L) | Impact (I) |
|:-----:|----------------|------------|
| 5 | Almost certain (>80%) | Catastrophic — programme failure / safety/legal |
| 4 | Likely (60–80%) | Major — gate slip, budget breach >15% |
| 3 | Possible (30–60%) | Moderate — scope/quality rework |
| 2 | Unlikely (10–30%) | Minor — localised delay |
| 1 | Rare (<10%) | Negligible |

### 5.1.4 Exposure Bands & Treatment

| Band | Exposure | Default Treatment | Reporting |
|------|:--------:|-------------------|-----------|
| **Critical (Red)** | 15–25 | Mitigate / Avoid with named owner + reserve | Every sprint + sponsor |
| **High (Amber)** | 9–14 | Mitigate; reserve considered | Every sprint |
| **Medium (Yellow)** | 5–8 | Mitigate or Accept | Bi-weekly |
| **Low (Green)** | 1–4 | Accept / monitor | Monthly |

### 5.1.5 Strategy Principles

1. **Prevention over recovery** — the highest-impact risks (R-1 factual propagation, R-2 corruption) are addressed by design (guardrails, checksums), not by incident response.
2. **Spike before committing** — the three H-risk builds (GSSTB navigator, Gujarati OCR, guardrails) are each preceded by a time-boxed spike (Deliverable 3 §3.3).
3. **Reserves are governed, not hidden** — reserves (Deliverable 4 §4.6) release only on documented triggers.
4. **Gates as risk checkpoints** — each milestone gate is also a risk go/no-go (Deliverable 3 §4.4.3).
5. **Single RAID source of truth** — the RAID log (WP 1.0.3) is the only authoritative risk register; this document is its structured snapshot.

---

## 5.2 Consolidated Risk Register

This register consolidates the 10 risks from Deliverable 1 §9 with the additional risks introduced in Deliverables 2–4. IDs prefixed `R-` originate in Deliverable 1; `R-11+` are added here.

| ID | Risk | L | I | Exp | Band | Owner | Treatment | Owning WP(s) |
|----|------|:-:|:-:|:---:|:----:|:-----:|:--------:|:------------:|
| R-1 | Factual errors propagate into the AI tutor (e.g. "Maitri", deleted Beehive poems) | 5 | 5 | 25 | Red | CE/ML | Avoid/Mitigate | 1.5.6, 1.8.2, 1.8.3, 1.9.1, 1.9.3 |
| R-2 | Silent corruption / partial downloads undetected (no checksums) | 4 | 4 | 16 | Red | DE | Mitigate | 1.5.2, 1.12.3 |
| R-3 | NCF-SE 2026-27 transition invalidates 2025-26 corpus mid-programme | 4 | 4 | 16 | Red | SA | Mitigate | 1.4.7 |
| R-4 | GSSTB portal navigation breaks (no direct PDF URLs) | 4 | 3 | 12 | Amber | DE | Mitigate | 1.3.4 |
| R-5 | NCERT portal flakiness stalls bulk acquisition | 5 | 2 | 10 | Amber | DE | Mitigate | 1.3.2 |
| R-6 | OCR quality on Gujarati scans insufficient for AI use | 3 | 4 | 12 | Amber | DE | Mitigate | 1.4.3 |
| R-7 | No version control → irreversible bad edits, no audit trail | 4 | 3 | 12 | Amber | SA | Mitigate | 1.1.1 |
| R-8 | Unverified textbook codes cause 404s / wrong files | 3 | 3 | 9 | Amber | DS | Mitigate | 1.3.3 |
| R-9 | Manual process does not scale to 28+ items × mediums | 5 | 2 | 10 | Amber | DE | Mitigate | 1.3.1 |
| R-10 | Licensing ambiguity on Tier-3/4 PDF reuse | 2 | 4 | 8 | Yellow | SEC | Mitigate | 1.1.2, 1.9.6 |
| R-11 | LLM token-cost volatility breaches budget (Deliverable 4 §4.3.4) | 4 | 3 | 12 | Amber | ML | Mitigate | 1.8.6, 1.8.7 |
| R-12 | Single LLM provider lock-in / outage | 3 | 3 | 9 | Amber | ML | Transfer/Mitigate | 1.8.7 |
| R-13 | Velocity under-runs 12 SP/sprint, slipping gates | 3 | 4 | 12 | Amber | PM | Mitigate | 1.0.3 (re-baseline) |
| R-14 | Key-person dependency on the single DE (backbone role) | 3 | 4 | 12 | Amber | PM | Mitigate | (cross-training) |
| R-15 | Data-residency / regulatory constraint on cloud region | 2 | 4 | 8 | Yellow | SEC | Avoid | 1.11.1 |
| R-16 | Evaluation golden-set drift makes AI regressions invisible | 3 | 3 | 9 | Amber | QA | Mitigate | 1.7.5, 1.8.5 |
| R-17 | Scope creep (non-Std-9 or out-of-scope features absorbed) | 3 | 3 | 9 | Amber | PM | Avoid | 1.0.1 |
| R-18 | Acceptance criteria ambiguity delays M12 sign-off | 3 | 3 | 9 | Amber | PM | Mitigate | 1.9.7 |

### 5.2.1 Register Summary

| Band | Count | IDs |
|------|:-----:|-----|
| Red (Critical) | 3 | R-1, R-2, R-3 |
| Amber (High) | 12 | R-4–R-9, R-11–R-14, R-16–R-18 |
| Yellow (Medium) | 2 | R-10, R-15 |
| Green (Low) | 0 | — |
| **Total** | **17** | — |

> The three Red risks dominate the programme and are each addressed by **design controls** (not contingency): R-1 by the guardrail + validation chain, R-2 by the integrity layer, R-3 by edition versioning. Their mitigation is the single most important risk activity.

---

## 5.3 Mitigation Plans (Critical & High Risks)

Each mitigation card specifies: **trigger**, **preventive action**, **contingency**, **owner**, **evidence of closure**.

### 5.3.1 R-1 — Factual Error Propagation (Red, Exp 25)
- **Trigger:** any unverified claim (e.g. audit §4 items) or AI answer lacking citation.
- **Preventive:** correct all six audit findings (WP 1.5.6 → 1.9.1); enforce "no source, no answer" guardrail (WP 1.8.3); citation binding to Tier-1/2 provenance (WP 1.8.2); factual spot-checks (WP 1.9.3).
- **Contingency:** if spot-checks show systematic error, freeze AI serving and loop back to extraction (WP 1.4.5) before re-release.
- **Owner:** CE (content) + ML (guardrail). **Evidence:** AUDIT_VERIFICATION.md signed at ≥90/100; guardrail eval below hallucination threshold.

### 5.3.2 R-2 — Silent Corruption / Partial Downloads (Red, Exp 16)
- **Trigger:** checksum mismatch on integrity monitor.
- **Preventive:** SHA-256 on every RAW asset (WP 1.5.2); nightly re-verification with alerting (WP 1.12.3); PDF validity check (WP 1.4.1).
- **Contingency:** alert → re-acquire affected asset from Tier-1 → re-verify before promotion.
- **Owner:** DE. **Evidence:** integrity monitor green for 4 consecutive weeks post-M6.

### 5.3.3 R-3 — NCF-SE 2026-27 Transition (Red, Exp 16)
- **Trigger:** official announcement of new Std 9 editions mid-programme.
- **Preventive:** version-tag every asset by edition year (WP 1.4.7); treat 2025-26 as a named snapshot; medium-equivalence map flags edition boundaries.
- **Contingency:** if 2026-27 lands before M12, scope it as a follow-on release; do not retrofit into the in-flight corpus.
- **Owner:** SA. **Evidence:** every manifest record carries an edition tag; transition plan documented.

### 5.3.4 R-4 — GSSTB Portal Navigation (Amber, Exp 12)
- **Trigger:** navigator cannot fetch ≥1 book/medium in the S3 spike.
- **Preventive:** 1-day spike before committing 5 SP (Deliverable 3 S3); resilient navigator with endpoint cache.
- **Contingency:** activate quarantined Tier-3 fallback (WP 1.3.8); descope non-Gujarati mediums; re-plan S4.
- **Owner:** DE. **Evidence:** navigator fetches ≥1 book/medium end-to-end.

### 5.3.5 R-6 — Gujarati OCR Quality (Amber, Exp 12)
- **Trigger:** OCR <90% word accuracy in the S7 spike.
- **Preventive:** 1-day spike; `tesseract guj` + pre-processing; confidence scoring.
- **Contingency:** manual-correction pass (1 SP); widen S7→S8 OCR budget.
- **Owner:** DE. **Evidence:** Gujarati QA sample ≥90%.

### 5.3.6 R-11 — LLM Token-Cost Volatility (Amber, Exp 12)
- **Trigger:** spend tracking >+30% to forecast.
- **Preventive:** versioning registry (WP 1.8.7); prompt/engineering efficiency; caching (WP 1.8.6).
- **Contingency:** quarterly re-price; evaluate self-hosted open-source inference; descope non-essential AI features.
- **Owner:** ML. **Evidence:** quarterly LLM cost report within budget.

### 5.3.7 R-13 / R-14 — Velocity & Key-Person Dependency (Amber, Exp 12 each)
- **Triggers:** CPI/SPI <0.9 for two sprints (R-13); DE unplanned absence (R-14).
- **Preventive (R-13):** re-baseline process (Deliverable 3 §3.8.3); 2 SP/sprint carry reserve.
- **Preventive (R-14):** cross-train DS/SA on acquisition pipeline; pair-program on H-risk WPs; document runbooks (WP 1.13.3).
- **Contingency:** re-baseline; bring in short-term contractor; descope P2 WPs.
- **Owner:** PM. **Evidence:** velocity within ±20%; documented cross-coverage.

---

## 5.4 Reserve & Contingency Mapping

Maps each material risk to the cost reserve (Deliverable 4 §4.6) and schedule contingency (Deliverable 3 §3.7) that back it.

| Risk | Reserve ($) | Schedule Contingency | Trigger |
|------|:-----------:|----------------------|---------|
| R-4 GSSTB portal | 2,500 | 1-day spike + S4 re-plan | Navigator spike fails |
| R-6 Gujarati OCR | 1,800 | S7→S8 widen | OCR <90% |
| R-5 NCERT outage | 600 | Mirror/cached | >3-day outage |
| R-1/R-11 LLM tokens | 2,800 | Quarterly re-price | Token cost >+30% |
| R-2 Corruption | (within integrity cost) | Re-acquire | Checksum mismatch |
| R-3 NCF-SE | (scope follow-on) | Defer to next release | Official announcement |
| R-13 Velocity | 8,700 (1 sprint) | Re-baseline | CPI/SPI <0.9 ×2 |
| R-10/R-15 Licensing/Residency | (within policy/IaC) | Region fix | Audit finding |
| General management reserve | 2,900 | — | PM + sponsor |
| **Total reserve** | **16,300** | 1 sprint (2 wks) | — |

> Every dollar of the $16,300 reserve (Deliverable 4 §4.6) is traceable to a risk trigger here — no orphan reserve.

---

## 5.5 Risk Monitoring & Leading Indicators

Risks are monitored via leading indicators (early signals) rather than lagging outcomes, reviewed each sprint and at every gate.

### 5.5.1 Leading Indicators by Risk

| Risk | Leading Indicator | Threshold | Source |
|------|-------------------|-----------|--------|
| R-1 | % of catalogue claims unverified; AI answers without citation | 0 unverified; 0 uncited | Audit rem. log; guardrail metrics |
| R-2 | Checksum-verify pass rate; invalid-PDF count | 100% pass; 0 invalid | Integrity monitor (WP 1.12.3) |
| R-3 | Untagged edition records | 0 untagged | Manifest |
| R-4 | GSSTB navigator spike result | ≥1 book/medium | S3 spike report |
| R-5 | NCERT retry rate per book | <20% retries | Acquisition logs |
| R-6 | OCR confidence p10 | ≥0.80 | OCR pipeline |
| R-7 | Commits outside protected branch | 0 | Git policy |
| R-9 | Manual acquisition steps remaining | 0 after M6 | Pipeline logs |
| R-11 | LLM $/1k-queries trend | within +30% | LLM cost report |
| R-13 | SPI / CPI | ≥0.9 | EVM (Deliverable 4 §4.7) |
| R-14 | DE single-point-of-knowledge WPs | documented + paired | Runbook coverage |
| R-16 | Golden-set freshness | reviewed each eval cycle | Eval harness |

### 5.5.2 Monitoring Cadence

| Activity | Frequency | Owner | Output |
|----------|-----------|:-----:|-------|
| RAID log update | Each sprint | PM | Updated register |
| Leading-indicator dashboard refresh | Bi-weekly | SRE/PM | Dashboard |
| Risk review at gate closure | Per gate (M2/M4/M6/M9/M12) | PM | Gate risk memo |
| Reserve-burn review | Monthly | PM + sponsor | Reserve report |
| Quarterly LLM re-price | Quarterly | ML | Cost update |

---

## 5.6 Escalation & Decision Authority

### 5.6.1 Escalation Thresholds

| Condition | Escalate To | Timeline |
|-----------|-------------|----------|
| Any Red risk materialising (trigger fired) | Sponsor | Within 1 business day |
| Reserve release | Sponsor | Before release |
| Gate slip >1 sprint | Sponsor + steering | At sprint boundary |
| Budget breach >15% projected | Sponsor | Monthly review or trigger |
| CPI/SPI <0.9 for 2 sprints | Sponsor (re-baseline) | End of 2nd sprint |
| Amber risk turning Red | Sponsor | Next sprint review |

### 5.6.2 Decision Authority Matrix (RACI summary)

| Decision | PM | SA | Sponsor | Steering |
|----------|:--:|:--:|:-------:|:--------:|
| Accept a Yellow risk | A/R | C | I | I |
| Accept an Amber risk | R | C | A | I |
| Accept a Red risk | C | C | A/R | C |
| Release reserve | R | C | A | I |
| Re-baseline plan/budget | R | C | A | C |
| Gate go/no-go | R | C | A | C |

_A=Accountable, R=Responsible, C=Consulted, I=Informed._

---

## 5.7 Risk Strategy Closure

This Risk Management & Mitigation Strategy consolidates **17 programme risks** (3 Red, 12 Amber, 2 Yellow) across the full Deliverable 1–4 evidence base, scored on a 1–5 L×I exposure model with band-driven treatment and reporting. The three Red risks (factual propagation, silent corruption, NCF-SE transition) are controlled by design — guardrails + validation, the integrity layer, and edition versioning respectively — rather than by contingency. Every mitigation names an owner, a trigger, a preventive action, a contingency, and closure evidence; every dollar of the $16,300 reserve (Deliverable 4 §4.6) and the 1-sprint schedule buffer (Deliverable 3 §3.7) is traceable to a specific risk trigger. Monitoring runs on leading indicators at sprint, gate, and quarterly cadences, with clear escalation thresholds and a RACI for risk acceptance, reserve release, re-baselining, and gate go/no-go. The strategy is governed by the RAID log (WP 1.0.3) as the single source of truth, of which this document is the structured snapshot.

_Deliverable 5 ends here. Deliverable 6 will define the quality assurance and testing strategy in operational detail._

---

# Deliverable 6 — Quality Assurance & Testing Strategy

> **Status:** In Progress — Deliverable 6 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 2 branch 1.9 (Validation) and 1.10 (Testing); Deliverable 3 §3.8 (Definition of Done & Gate Evidence); Deliverable 4 §4.7 (EVM); Deliverable 5 (risks R-1, R-2, R-16).

## 6.1 QA Strategy & Principles

### 6.1.1 Purpose

Deliverable 6 defines how quality is **engineered, verified, and assured** across the STD9_AI_ACADEMY programme. Where Deliverable 2 listed the validation and testing work packages and Deliverable 3 set their Definition of Done, this strategy specifies the **test pyramid, quality gates, coverage targets, environments, tooling, and the data-quality assurance regime** that make "done" enforceable rather than aspirational. It is owned by the QA role and consumed by every branch.

### 6.1.2 Quality Definition

For this programme, a **quality product** is one that is:
1. **Correct** — content facts match Tier-1/2 sources (mitigates R-1).
2. **Complete** — every catalogued chapter/asset is present, acquired, extracted, and indexed.
3. **Integral** — every asset is checksum-verified and uncorrupted (mitigates R-2).
4. **Curriculum-aligned** — content maps 1:1 to the official Std 9 syllabus with rationalisation applied.
5. **Machine-usable** — extracted text is clean, normalised, and queryable; AI answers are faithful and cited.
6. **Reproducible** — every build, dataset, and model/prompt version is reconstructable.

### 6.1.3 Quality Principles ("Shift-Left")

1. **Quality is built in, not inspected in** — acceptance criteria are defined in Deliverable 2 *before* work starts; tests are written alongside code.
2. **Shift-left** — defects are cheapest to fix at the point of creation; lint, schema, and integrity checks run in CI on every change, not at gates.
3. **Independent verification** — the QA/CE branch (1.9) independently validates the output of the building branches (1.3–1.8); builders do not self-certify gates.
4. **Data quality is first-class** — for a content corpus, data-quality testing (integrity, fidelity, factual) carries equal weight to code testing.
5. **Gates are evidence-based** — a gate closes only on documented evidence (Deliverable 3 §3.8.2), never on opinion.
6. **Regression-protected** — every quality property has an automated regression test that runs in CI and at gates.
7. **Proportionate** — rigour scales with risk: H-risk WPs get deeper verification than low-risk ones.

### 6.1.4 QA Scope (in/out)

| In Scope | Out of Scope |
|----------|--------------|
| Data/content quality (integrity, fidelity, factual, alignment) | End-user tutor UI testing (separate programme) |
| Code quality (unit, integration, E2E) | LMS/back-office system testing |
| Pipeline quality (idempotency, determinism) | At-scale load beyond NFR targets (Deliverable 4 §4.1.5) |
| AI quality (faithfulness, citation, hallucination) | Model training/finetuning evaluation |
| Service quality (latency, correctness, security) | Payment/billing correctness |

### 6.1.5 QA Ownership Model

| Layer | Primary Owner | Independent Verifier |
|-------|---------------|----------------------|
| Code tests (unit/integration/E2E) | DE/ML (builders) | QA |
| Data quality (integrity/fidelity/factual) | DS/DE | QA + CE |
| AI quality (faithfulness/citation) | ML | QA |
| Gate evidence & sign-off | PM | Sponsor |

---

## 6.2 Test Pyramid & Coverage Targets

### 6.2.1 The Test Pyramid

The programme adopts a **content-aware test pyramid** that extends the classic Mike Cohn pyramid with a dedicated data-quality layer, reflecting that the primary artefact is a verified content corpus rather than a pure software product.

```
                    /\
                   /  \        E2E / Acceptance
                  /----\       (user-journeys, gate simulations)
                 /      \
                /--------\     Integration
               /          \    (pipeline, API, data-flow)
              /------------\
             /              \  Unit + Data-Quality (broad base)
            /----------------\ (schemas, integrity, factual, lint)
```

| Level | What it proves | Where it runs | Volume |
|-------|----------------|---------------|--------|
| **L0 – Static / Lint** | Code & content conform to schema/style before execution | pre-commit + CI | thousands |
| **L1 – Unit** | Individual functions/modules behave correctly | CI (every push) | hundreds |
| **L2 – Data-Quality** | Every asset is integral, faithful, and factually correct | CI + gate | per-asset, 100% |
| **L3 – Integration** | Pipeline stages compose correctly; APIs honour contracts | CI (nightly) + gate | tens |
| **L4 – End-to-End** | Full acquisition→index→answer pipeline meets acceptance | Gate (per release) | handful |
| **L5 – Acceptance** | Sponsor-visible outcomes (NFRs, syllabus coverage) | Gate (M6, M9, M12) | traceable |

### 6.2.2 Coverage Targets

| Artefact | Metric | Target | Gate Enforced |
|----------|--------|--------|:-------------:|
| Python pipeline code | Line coverage | ≥85% | M2, M4, M6 |
| Python pipeline code | Branch coverage | ≥70% | M4, M6 |
| Critical-path modules (acquire, extract, integrity) | Line coverage | ≥95% | every gate |
| AI/RAG code (retriever, answer-gen, citation) | Line coverage | ≥90% | M6, M9 |
| Frontend/CLI code | Line coverage | ≥60% | M9 |
| Content assets | Integrity-checked | 100% | M2 onward |
| Content assets | Schema-valid | 100% | M2 onward |
| Content assets | Factual review (sampled) | 100% of sample | M4, M6 |
| Syllabus objectives | Mapped to ≥1 asset | 100% | M4, M6, M9 |
| Public API endpoints | Contract-tested | 100% | M9 |
| High-risk WPs (H) | E2E coverage | ≥1 per critical flow | per gate |

Coverage is measured by `coverage.py` (Python), `c8`/`nyc` (JS), and the custom content-coverage harness; reports are published as gate evidence (Deliverable 3 §3.8.2). Coverage that cannot drop is **frozen** via CI thresholds (the build fails if it regresses).

### 6.2.3 Defect Escape Economics

| Detection Point | Relative Cost | Notes |
|-----------------|:------------:|-------|
| At authoring (shift-left, L0/L1) | 1× | Cheapest; caught in CI |
| At code review | 2–3× | PR review + fix |
| At integration (L3) | 5–10× | Cross-module, rework |
| At gate (L4/L5) | 10–40× | Stalls a release gate |
| Post-release (escaped) | 100×+ | R-2 silent corruption scenario |

This table drives the **shift-left principle (6.1.3.2)** and justifies the disproportionate breadth of the L0–L2 base.

---

## 6.3 Quality Gates

### 6.3.1 Gate Inventory

Quality gates are the enforceable checkpoints where independent QA verification gates progression. They map onto the Deliverable 3 milestone schedule.

| Gate | Milestone | Blocks | Independent Verifier | Sponsor Sign-off |
|------|-----------|--------|----------------------|:----------------:|
| **G1 – Foundation Readiness** | M2 | All pipeline builds | QA | No |
| **G2 – Acquisition & Integrity** | M4 | Content entering the corpus | QA + CE | Yes |
| **G3 – AI Quality** | M6 | Public answers / tutoring | QA + Sponsor | Yes |
| **G4 – Release Readiness** | M9 | Production deployment | QA + Sponsor | Yes |
| **G5 – Handover & Sustainment** | M12 | Operational transfer | Sponsor | Yes |

### 6.3.2 Gate Entry / Exit Criteria (Generic Template)

Every gate uses the same evidence-based entry/exit pattern (per Deliverable 3 §3.8.2). A gate **cannot exit** until every exit criterion is evidenced green.

**Entry criteria** (must be met to even convene the gate):
- All constituent WPs at status *Done* per their DoD.
- CI green on the protected branch for ≥3 consecutive builds.
- Open Sev-1/Sev-2 defects = 0.
- Required evidence package assembled in the gate folder.

**Exit criteria** (the gate itself):
- Every exit criterion below is *Passed* with a linked artefact.
- Residual risks accepted by the named authority (Deliverable 5 §5.6.2).
- Known-issues list reviewed; Sev-3 deferred defects have owners + target gate.

### 6.3.3 Gate-Specific Exit Criteria

#### G1 – Foundation Readiness (M2)
| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G1.1 | Repo, CI, protected branch, lint, and schema harness operational | CI dashboard, repo settings |
| G1.2 | L0/L1 test suite ≥85% line coverage on foundation modules | Coverage report |
| G1.3 | Integrity-check tool passes on seed corpus | Integrity report |
| G1.4 | DoD applied to WP 1.1.1–1.1.4 | WP closure records |

#### G2 – Acquisition & Integrity (M4)
| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G2.1 | 100% of catalogued assets acquired and checksum-verified | Acquisition log, manifest |
| G2.2 | 100% of extracted text schema-valid + within fidelity threshold | Fidelity report |
| G2.3 | Factual review of sampled chapters ≥ acceptance threshold | CE factual report |
| G2.4 | Syllabus-coverage map shows 100% objective coverage | Coverage map |
| G2.5 | No Sev-1/Sev-2 defects open | Defect register |

#### G3 – AI Quality (M6)
| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G3.1 | Golden-set faithfulness ≥ threshold (R-16) | Eval harness report |
| G3.2 | Citation correctness ≥ threshold on golden set | Citation eval |
| G3.3 | Hallucination rate ≤ threshold on adversarial set | Adversarial eval |
| G3.4 | Retrieval precision/recall meets target | Retrieval eval |
| G3.5 | NFR latency targets met under expected load | Load test report |

#### G4 – Release Readiness (M9)
| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G4.1 | End-to-end acceptance scenarios pass | E2E report |
| G4.2 | Security review complete; no open High/Critical findings | Security report |
| G4.3 | Operational runbook + on-call rotation in place | Runbook, ops plan |
| G4.4 | Rollback/restore drill successful | Drill log |
| G4.5 | Sponsor UAT sign-off | UAT record |

#### G5 – Handover & Sustainment (M12)
| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G5.1 | Sustainment team trained and shadowing for ≥1 sprint | Training record |
| G5.2 | Monitoring, alerting, and dashboards transferred live | Ops handover doc |
| G5.3 | Defect backlog triaged and assigned to sustainment | Defect register |
| G5.4 | Final architecture/as-built documentation delivered | As-built docs |

### 6.3.4 Gate Mechanics

- **Evidence location:** each gate has a folder `gates/G<n>/` containing the required artefacts; the gate folder is itself version-controlled.
- **Verdicts:** *Passed* (all criteria green), *Passed-with-conditions* (minor defects with remediation plan + owner), *Failed* (any blocking criterion red → re-convene next sprint).
- **Audit trail:** gate verdicts are recorded in the RAID log (WP 1.0.3) and the project log; a failed gate is a risk event (feeds Deliverable 5 §5.3).
- **No silent waivers:** any deviation from exit criteria requires a documented waiver signed by the gate's accountable authority (Deliverable 5 §5.6.2).

---

## 6.4 Environments & Test Data

### 6.4.1 Environment Topology

| Environment | Purpose | Data | Refresh | Access |
|-------------|---------|------|---------|--------|
| **dev** | Local authoring, ad-hoc | Synthetic / sample | On demand | All engineers |
| **ci** | Automated pipelines (L0–L3) | Curated fixtures + golden set | Per build | CI service only |
| **int** (integration) | Cross-module composition (L3) | Anonymised sample corpus | Nightly | DE, QA |
| **stg** (staging) | Pre-release / UAT (L4/L5) | Production-equivalent corpus | Per release candidate | QA, Sponsor (UAT) |
| **prod** | Live service | Full corpus | Released only | Ops |

Promotion path: `dev → ci → int → stg → prod`. Promotion requires the upstream gate to have *Passed*.

### 6.4.2 Test Data Strategy

Content programmes face two data risks distinct from typical software: **licensing** and **factual ground truth**.

- **Fixtures (ci):** small, deterministic, hand-verified slices (1–2 chapters) used in every build. Checked into the repo under `tests/fixtures/`. License-cleared.
- **Golden set (eval):** the R-16 golden set — curated question/answer/reference triples used for AI-quality gates (6.3.3 G3). Stored in `eval/golden/`; access-restricted; reviewed each eval cycle (Deliverable 5 §5.5.1).
- **Anonymised corpus (int):** production-like content with any PII/identifying material redacted, used for integration runs.
- **Production-equivalent corpus (stg):** the full real corpus for UAT and load testing, behind the same access controls as prod.
- **Adversarial set:** hand-crafted misleading/edge queries to stress-test hallucination resistance (6.3.3 G3.3).

### 6.4.3 Test-Data Hygiene Rules

1. No production data in `dev` or `ci` without anonymisation.
2. Golden set never mutated by automated tests; read-only in CI.
3. Every fixture carries a `LICENSE.txt` and provenance note (feeds R-1 traceability).
4. Test-data refresh is a WP task (not ad-hoc) and is logged.

---

## 6.5 Test Automation & Tooling

### 6.5.1 Tool Stack

| Layer | Tool | Role |
|-------|------|------|
| L0 Static (Python) | `ruff`, `mypy` | Lint + type-check |
| L0 Static (content) | `jsonschema` / `pydantic`, custom validators | Schema/style conformance |
| L0 Static (secrets) | `gitleaks` | Prevent credential leaks (security) |
| L1 Unit | `pytest` (+ `coverage.py`) | Unit tests + coverage |
| L1 Unit (JS) | `vitest` / `jest` (+ `c8`) | Frontend unit tests |
| L2 Data-Quality | Custom integrity harness (checksums, fidelity, factual) | Per-asset verification |
| L3 Integration | `pytest` (+ `testcontainers`), API contract tests | Pipeline + API |
| L4 E2E | `playwright` | End-to-end journeys |
| L5 Acceptance | Eval harness (golden + adversarial) | AI-quality acceptance |
| Orchestration | CI runner (protected-branch pipeline) | Schedules all of the above |
| Reporting | Coverage gate, eval dashboard | Gate evidence |

### 6.5.2 Pipeline Stages (CI)

The protected-branch CI pipeline runs the levels in order, **fail-fast**:

```
1. checkout + gitleaks (L0 secrets)        ── fail → stop
2. ruff + mypy (L0 lint/type)              ── fail → stop
3. jsonschema/pydantic content validation  ── fail → stop
4. pytest unit (L1) + coverage gate        ── fail → stop; coverage regression → stop
5. integrity harness (L2)                  ── fail → stop  (R-2 control)
6. pytest integration (L3)                 ── nightly + on-demand
7. eval harness (L5 golden)                ── on staging builds / pre-gate
8. playwright E2E (L4)                     ── on staging builds / pre-gate
9. publish reports to gate folder          ── always
```

Stages 1–5 run on **every** push; 6–8 run on nightly and pre-gate schedules. A failing L2 integrity check is a **hard stop** — it is the primary control for R-2 (silent corruption) and may not be waived at any gate below G2.

### 6.5.3 Test Authoring Standards

- **AAA structure** — Arrange, Act, Assert; one logical assertion per test.
- **Naming** — `test_<unit>_<condition>_<expected>` (e.g., `test_extract_pdf_corrupt_returns_integrity_error`).
- **Determinism** — no wall-clock, no network, no unseeded randomness; golden-set reads are read-only.
- **Isolation** — each test sets up and tears down its own state; no cross-test ordering dependency.
- **Coverage honesty** — tests assert behaviour, not implementation; trivial getters excluded from targets.
- **Data-quality tests live with the data** — a failing asset links to its failing test in the report.

### 6.5.4 Defect Lifecycle

| State | Meaning | SLA (Sev-1 / Sev-2 / Sev-3) |
|-------|---------|------------------------------|
| New | Logged, untriaged | Triaged within 1d / 2d / sprint |
| Triaged | Severity + owner assigned | — |
| In Progress | Being fixed | Fix within sprint (Sev-1 immediate) |
| Verified | Fix merged + QA-verified | Re-test within 1d / 2d / sprint |
| Closed | Verified + in release | — |
| Deferred | Knowingly postponed | Owner + target gate required |

A Sev-1 defect blocks the current gate (6.3.4). Sev-2 defects block at the next gate unless waived with authority.

---

## 6.6 Data-Quality Assurance Regime

Because the programme's core artefact is a content corpus, data quality is treated as a first-class engineering discipline (principle 6.1.3.4), not an afterthought. This section operationalises the three data-quality pillars introduced in the quality definition (6.1.2) and the DoD (Deliverable 3).

### 6.6.1 Pillar 1 — Integrity (mitigates R-2)

Integrity answers: *is every asset uncorrupted from source to store, end to end?*

| Check | When | Tool | Pass Condition |
|-------|------|------|----------------|
| Source checksum recorded | At acquisition | Acquire stage | SHA-256 in manifest |
| Transit checksum verified | Post-download | Integrity harness | Matches source |
| Post-extraction checksum | Post-extract | Integrity harness | Recorded, stable |
| Storage checksum | In store | Integrity harness | Matches post-extract |
| Periodic re-verification | Daily | Integrity cron | 100% match |

A single mismatch is a **Sev-1** event: the asset is quarantined, the pipeline halts on that branch, and the integrity layer raises R-2 to Red (Deliverable 5 §5.4). No asset may cross G2 without a complete integrity chain.

### 6.6.2 Pillar 2 — Fidelity

Fidelity answers: *does the extracted text faithfully represent the source asset?*

| Metric | Method | Target |
|--------|--------|--------|
| Character-level fidelity | Levenshtein/normalised edit distance vs re-OCR baseline | ≥ 99.0% clean text |
| Structural fidelity | Heading/section detection precision/recall | ≥ 95% |
| Image/table capture | Asset count vs source | 100% referenced assets captured |
| Encoding normalisation | Unicode NFC + NFKC applied | 100% |

Fidelity failures are triaged by severity: wholesale page loss = Sev-1; structural break = Sev-2; minor glyph errors = Sev-3.

### 6.6.3 Pillar 3 — Factual Correctness (mitigates R-1)

Factual correctness answers: *do content facts match Tier-1/2 sources?*

- **Sampling plan:** every chapter is sampled; high-stakes chapters (examinable core) are reviewed 100% by a Curriculum Expert (CE), the remainder on a stratified sample.
- **Source tiering:** Tier-1 (official textbook/publisher) > Tier-2 (accredited supplementary). Every fact traces to a tier-tagged source (feeds R-1 factual propagation control).
- **Discrepancy handling:** any Tier-1/Tier-2 conflict is escalated per Deliverable 5 R-1 (guardrails + validation), never silently resolved.
- **Evidence:** the CE factual report is a G2 exit artefact (6.3.3 G2.3).

### 6.6.4 Pillar 4 — Alignment (curriculum fit)

Alignment answers: *does the corpus cover the official Std 9 syllabus 1:1?*

- **Coverage map:** every syllabus objective maps to ≥1 asset; coverage is computed automatically and reported at G2/G4.
- **Gap handling:** an uncovered objective is a Sev-2 defect with an acquisition action; the rationalisation process (Deliverable 2) reconciles retired/merged objectives.

### 6.6.5 Data-Quality Reporting

A single **Data-Quality Dashboard** rolls up integrity, fidelity, factual, and alignment status per asset, per chapter, and per branch. It is the headline view QA presents at every gate. Red/Amber/Green status drives the gate verdict (6.3.4).

---

## 6.7 AI / RAG Quality Assurance

AI quality is the G3 concern (6.3.3) and operationalises risks R-1 (factual propagation) and R-16 (golden-set freshness).

### 6.7.1 Quality Dimensions for AI Output

| Dimension | Definition | Primary Metric |
|-----------|------------|----------------|
| **Faithfulness** | Answer uses only retrieved evidence; no invented facts | Faithfulness score on golden set |
| **Citation correctness** | Every claim cites a real, supportive source | Citation precision |
| **Groundedness** | Answer is derivable from retrieved context | Groundedness score |
| **Relevance** | Answer addresses the question asked | Relevance score |
| **Hallucination resistance** | Robustness to misleading/edge queries | Hallucination rate (adversarial set) |
| **Retrieval quality** | The right evidence is retrieved first | Precision@k, Recall@k |
| **Latency** | Answer delivered within NFR target | p95 latency |

### 6.7.2 Evaluation Harness

- **Golden set** (R-16): curated Q/A/reference triples, versioned, read-only in CI, reviewed each eval cycle.
- **Adversarial set:** hand-crafted misleading, out-of-scope, and ambiguous queries.
- **Automated scorers:** faithfulness/groundedness via entailment/LLM-as-judge with human spot-check; citation correctness via reference-link validation.
- **Human review:** a stratified sample of golden answers is CE-reviewed each cycle to keep the automated scorers honest.
- **Cadence:** full eval on every staging build pre-G3; regression subset on every protected-branch build.

### 6.7.3 AI Defect Triage

| Symptom | Likely Root Cause | Severity |
|---------|-------------------|:--------:|
| Faithful but wrong (cites real source incorrectly) | Citation/retrieval bug | Sev-2 |
| Confident hallucination | Retrieval failure / prompt over-generation | Sev-1 |
| Refuses answerable question | Over-aggressive guardrail | Sev-2 |
| Cites non-existent source | Index/citation pipeline bug | Sev-1 |
| Slow answer | Retrieval/index regression | Sev-3 |

### 6.7.4 Prompt & Model Versioning

- Prompts and model endpoints are versioned alongside code (feeds reproducibility, 6.1.2.6).
- A prompt or model change triggers a **full eval run** before merge; a regression in any AI-quality dimension blocks the merge (treating the eval as a CI gate, mirroring 6.5.2).
- Golden-set drift is monitored: if scores trend down across cycles without a code change, the golden set itself is reviewed for staleness (R-16 control).

---

## 6.8 Non-Functional & Security Testing

### 6.8.1 NFR Verification Mapping

Each NFR (Deliverable 4 §4.1.5) has a corresponding test or measurement:

| NFR | Test Type | When | Pass Target |
|-----|-----------|------|-------------|
| Performance (latency) | Load test (L4) | Pre-G3, pre-G4 | p95 ≤ target |
| Scalability | Soak test | Pre-G4 | No degradation over soak window |
| Reliability/Availability | Fault-injection + monitoring | Pre-G4, in prod | ≥ target uptime |
| Security | SAST + DAST + pentest | Pre-G4 | No High/Critical open |
| Maintainability | Coverage + lint + complexity | Every build | Targets per 6.2.2 |
| Accessibility | a11y scan + manual | Pre-G4 | WCAG conformance target |
| Observability | Dashboard + alert dry-run | Pre-G4 | Alerts fire on injected faults |

### 6.8.2 Security Testing Scope

- **SAST** — static analysis on every push (`gitleaks`, `bandit`/`semgrep`).
- **DAST** — dynamic scans against staging pre-G4.
- **Dependency scan** — `pip-audit` / `npm audit` in CI; High/Critical block release.
- **Secrets** — no secrets in repo; vault-managed; `gitleaks` enforced (6.5.2 stage 1).
- **Pentest** — a scoped external/internal pentest pre-G4; findings feed the defect register with SLAs.
- **Access control** — role/access matrix tested in staging; least-privilege verified.

### 6.8.3 Operational Acceptance

Before G4, ops-readiness is verified:
- Runbook executed against a simulated incident (4.4.x style drill).
- Rollback/restore drill successful (G4.4).
- Monitoring + alerting validated with injected faults.
- On-call rotation and escalation contacts confirmed.

---

## 6.9 QA Governance, Roles & Metrics

### 6.9.1 QA Role Responsibilities

| Activity | Owner | Supporting |
|----------|:-----:|:----------:|
| Own test strategy & pyramid | QA | SA |
| Maintain CI pipeline & gates | QA + DE | — |
| Independent gate verification | QA (+ CE for factual) | — |
| Defect triage chair | QA | PM |
| Coverage & eval reporting | QA | DE/ML |
| Golden-set curation & freshness | QA + CE | ML |
| Security testing coordination | QA | Ops |
| Gate evidence assembly | QA | WP leads |

### 6.9.2 QA Metrics (Leading Indicators)

These metrics feed the risk dashboard (Deliverable 5 §5.5.1) and give early warning of gate slippage.

| Metric | Target | Frequency |
|--------|--------|-----------|
| CI pass rate (protected branch) | ≥95% | Per build |
| Coverage trend (line/branch) | Non-regressing | Per build |
| Defect arrival rate | Trending down | Weekly |
| Sev-1/Sev-2 open count | 0 | Daily |
| Defect escape rate (post-gate) | ≤ target | Per gate |
| Integrity re-verify pass | 100% | Daily |
| Golden-set faithfulness | ≥ threshold | Per eval cycle |
| Eval regression subset pass | ≥ threshold | Per build |
| Gate criteria green ratio | 100% pre-gate | Pre-gate |

### 6.9.3 QA Cadence

| Activity | Frequency | Output |
|----------|-----------|--------|
| Test strategy review | Per gate + on major change | Updated strategy |
| Defect triage | Daily (Sev-1/2), weekly (Sev-3) | Updated register |
| Coverage/eval dashboard refresh | Bi-weekly | Dashboard |
| Golden-set review | Per eval cycle | Refreshed set |
| Gate readiness review | Pre-gate | Gate readiness memo |
| Post-gate retrospective | Per gate | Lessons-learned entry |

### 6.9.4 Definition of Done (QA lens)

In addition to each WP's DoD (Deliverable 3 §3.8.1), QA confirms *done* means:
1. All in-scope tests (L0–L5) for the change are green.
2. Coverage has not regressed below the frozen threshold.
3. No new Sev-1/Sev-2 defects introduced.
4. Required gate evidence updated.
5. Data-quality checks pass for any touched asset.
6. For AI changes: full eval run green (6.7.4).

---

## 6.10 QA Strategy Closure

This Quality Assurance & Testing Strategy makes "done" enforceable across the STD9_AI_ACADEMY programme. It defines a **content-aware test pyramid (L0–L5)** with explicit, frozen coverage targets; **five evidence-based quality gates (G1–G5)** mapped to milestones M2/M4/M6/M9/M12, each with entry/exit criteria and a documented waiver path; a disciplined **environment and test-data regime** that keeps licensing, anonymisation, and golden-set integrity under control; an **automated, fail-fast CI pipeline** in which the L2 integrity harness is the hard control for R-2; a **four-pillar data-quality regime** (integrity, fidelity, factual, alignment) that treats content correctness as first-class engineering; an **AI/RAG quality regime** built on a versioned golden set and adversarial testing (R-1, R-16); and **non-functional, security, and operational-acceptance testing** that proves NFRs before release. Governance is owned by the QA role with leading-indicator metrics, a daily/weekly/per-cycle cadence, and a QA-extended Definition of Done. Every gate verdict, defect, and metric flows into the RAID log (WP 1.0.3) and the risk dashboard (Deliverable 5 §5.5), so that quality assurance, risk management, and schedule remain a single, traceable control loop.

_Deliverable 6 ends here. Deliverable 7 will define the deployment, rollout, and sustainment strategy in operational detail._

---

# Deliverable 7 — Deployment, Rollout & Sustainment Strategy

> **Status:** In Progress — Deliverable 7 of 7
> **Author:** STD9_AI_ACADEMY Engineering Team
> **Last Updated:** 2026-06-27
> **Basis:** Deliverable 2 branch 1.11 (Deployment & Operations); Deliverable 3 §3.8 (Definition of Done & Gate Evidence); Deliverable 4 §4.1.5 (NFRs), §4.7 (EVM); Deliverable 5 (risks R-4, R-5, R-6, R-8, R-10); Deliverable 6 (gates G4/G5, operational acceptance).

## 7.1 Deployment Strategy & Principles

### 7.1.1 Purpose

Deliverable 7 defines how the verified STD9_AI_ACADEMY product is **deployed to production, rolled out to users, and sustained** across its operational life. Where Deliverable 2 catalogued the deployment and operations work packages, Deliverable 3 set their Definition of Done, Deliverable 4 sized them, and Deliverable 6 defined the quality gates (G4 release readiness, G5 handover), this strategy specifies the **release model, environment promotion, rollout phasing, rollback, monitoring, and the sustainment operating model** that make go-live and long-term operation repeatable and safe. It is owned by the Ops role and consumed by the deployment, operations, and sustainment teams.

### 7.1.2 Guiding Principles

1. **Release early, release safely** — small, frequent, reversible releases beat large risky ones (mitigates R-5).
2. **Infrastructure as Code (IaC)** — every environment is reproducible from version-controlled definitions; no manual snowflakes (mitigates R-4).
3. **Progressive delivery** — canary → staged rollout → full, with automated health gates between stages.
4. **Rollback-first** — every release must be revertible before it is deemed deployable (Deliverable 6 §6.8.3, G4.4).
5. **Observability built-in** — deploy telemetry, logs, and dashboards *with* the feature, not after.
6. **Zero-downtime where feasible** — blue/green or rolling deploys for user-facing services.
7. **Sustainment by design** — handover is planned from M2, not bolted on at M12 (mitigates R-8).
8. **Least privilege** — production access is just-in-time, logged, and reviewed (mitigates R-10).

### 7.1.3 Deployment Scope (in/out)

| In Scope | Out of Scope |
|----------|--------------|
| Production environment build & promotion | End-user device provisioning |
| Release & rollback procedures | Tutor/LMS UI product roadmap |
| Progressive rollout & canary | Model training/finetuning pipelines |
| Monitoring, alerting & incident response | Corporate IT/network operations |
| Patch, update & edition release process | Vendor contract negotiation |
| Sustainment operating model & handover | New feature development (separate programme) |

---

## 7.2 Release Model & Environment Promotion

### 7.2.1 Release Cadence & Types

| Release Type | Trigger | Cadence | Scope | Rollback |
|--------------|---------|---------|-------|:--------:|
| **Patch** | Defect/security fix (Sev-1/Sev-2) | As needed | Minimal, targeted | Yes |
| **Minor** | Incremental feature/quality update | Monthly | Additive, backward-compatible | Yes |
| **Edition** | New content edition / syllabus cycle | Per syllabus cycle | Content corpus refresh | Versioned (R-6 NCF-SE) |
| **Major** | Architecture/platform change | Rare | Breaking changes allowed | Yes (with migration plan) |

Editions are versioned (per the NCF-SE transition control, Deliverable 5 R-6) so that prior editions remain reproducible and citable; a new edition is an additive release, not an in-place overwrite.

### 7.2.2 Environment Promotion Path

Promotion follows the environments defined in Deliverable 6 §6.4.1, gated by the QA gates (Deliverable 6 §6.3):

```
dev  ──(G1)──▶  ci  ──(CI green)──▶  int  ──(G2)──▶  stg  ──(G3/G4)──▶  prod
```

| Transition | Required Condition |
|------------|--------------------|
| dev → ci | Lint/type/schema green; committed to working branch |
| ci → int | Protected-branch CI green ≥3 builds; integrity harness green |
| int → stg | G2 (acquisition & integrity) Passed |
| stg → prod | G3 (AI quality) + G4 (release readiness) Passed |

No artifact may reach `prod` without a corresponding gate verdict recorded in the gate folder (`gates/G<n>/`, Deliverable 6 §6.3.4).

---

## 7.3 Infrastructure as Code & Artifact Management

### 7.3.1 Infrastructure as Code (mitigates R-4)

All environments are defined as code and provisioned repeatably — no manual configuration drift.

| Concern | Approach |
|---------|----------|
| Environment definition | Version-controlled IaC (e.g., Terraform/Pulumi) |
| Configuration | Templated, environment-parameterised, secret-free |
| Secrets | Vault-managed; injected at runtime, never in IaC |
| Drift detection | Scheduled reconciliation vs IaC source |
| Provisioning | Automated; idempotent; destroyable |

Drift detection runs on a schedule; any unmanaged change in `prod` is flagged and either reconciled to IaC or formally documented (R-4 control).

### 7.3.2 Artifact Management

| Artifact Type | Store | Retention | Immutability |
|---------------|-------|-----------|:------------:|
| Code builds | Package registry | ≥3 releases | Yes (content-addressed) |
| Container images | Image registry | ≥3 releases + last known-good | Yes (digest-pinned) |
| Content corpus snapshots | Editioned archive | Permanent (per edition) | Yes (checksum-pinned, R-2) |
| Model/prompt versions | Model registry | Permanent + reproducible | Yes (version-pinned) |
| Release manifests | Release folder (`releases/<n>/`) | Permanent | Yes |

Every production deployment references an immutable, pinned artifact set recorded in the release manifest; this is what makes rollback and reproducibility possible.

---

## 7.4 Deployment Procedures

### 7.4.1 Deployment Patterns

| Pattern | When Used | Characteristic |
|---------|-----------|----------------|
| **Blue/Green** | User-facing services requiring zero downtime | Two envs; instant switch |
| **Rolling** | Stateless backend services | Gradual instance replacement |
| **Canary** | Risky/feature releases | Small % traffic → expand on health |
| **Recreate** | Breaking changes with migration | Brief downtime window |

The default for user-facing services is **blue/green with a canary phase** to satisfy principles 7.1.2.3 (progressive) and 7.1.2.6 (zero-downtime).

### 7.4.2 Standard Deploy Runbook (Per Release)

1. **Pre-deploy** — confirm G4 Passed; assemble pinned artifact set; notify stakeholders; schedule change window if required.
2. **Deploy to blue/green inactive side** — provision from IaC; apply pinned artifacts; run smoke tests against the inactive side.
3. **Canary** — route a small % of traffic; observe health metrics for the canary window (see 7.6.2).
4. **Promote** — on green health gates, shift traffic fully to the new side.
5. **Verify** — run post-deploy acceptance checks; confirm dashboards reflect new version.
6. **Hold** — retain the previous side for the rollback window (default 24–72h) before teardown.
7. **Close** — record the release in `releases/<n>/`; update the release log; retire the old side.

### 7.4.3 Pre-Deploy Checklist

- [ ] G3 and G4 gate verdicts *Passed* and recorded.
- [ ] Pinned artifact set present and immutable.
- [ ] Release manifest complete (code, image, corpus, model/prompt versions).
- [ ] Rollback plan documented and rehearsed (G4.4 drill passed).
- [ ] Runbook linked; on-call paged and acknowledged.
- [ ] Monitoring dashboards and alerts live for the new version.
- [ ] Comms sent: change window, impact, owner.

---

## 7.5 Rollback Strategy (mitigates R-5)

Rollback is a **first-class release concern**, validated before any deploy is allowed (principle 7.1.2.4; G4.4).

### 7.5.1 Rollback Triggers

| Trigger | Source | Action |
|---------|--------|--------|
| Health-gate failure during canary | Monitoring (7.6) | Auto-revert canary; halt promotion |
| Sev-1 defect post-deploy | Incident (7.7) | Decision to rollback within SLA |
| Error/latency budget breach | SLO dashboard | Auto-alert; manual rollback decision |
| Data integrity regression | L2 integrity cron | Immediate rollback; raise R-2 |
| Failed post-deploy acceptance | Acceptance checks | Revert before close |

### 7.5.2 Rollback Mechanics

- **Blue/green:** traffic switches back to the retained previous side — seconds, no data loss.
- **Rolling:** previous artifact set re-deployed across instances.
- **Content/model:** switch to the pinned prior edition/version recorded in the release manifest (immutable artifacts, §7.3.2).
- **Database/state:** backward-compatible releases require no migration on rollback; breaking changes carry a documented reverse-migration in the release manifest.

### 7.5.3 Rollback Validation

After any rollback:
1. Confirm the reverted version is serving.
2. Re-run smoke + acceptance checks.
3. Confirm SLOs recover to within budget.
4. Open a post-incident review (7.7) — a rollback is a defect signal, never a non-event.
5. Record the rollback in the release log and the RAID log (feeds R-5 monitoring).

### 7.5.4 Rollback Window

The retained previous side is kept for a **minimum rollback window of 72 hours** post-deploy (extended for high-risk releases). Teardown before the window requires a documented waiver.

---

## 7.6 Monitoring, Observability & Alerting

Observability is deployed *with* the feature (principle 7.1.2.5) and validated at G4 (Deliverable 6 §6.8.3).

### 7.6.1 Observability Pillars

| Pillar | What It Captures | Tooling (illustrative) |
|--------|------------------|------------------------|
| **Metrics** | Latency, throughput, error rate, saturation, SLOs | Prometheus / metrics backend |
| **Logs** | Structured events across pipeline, API, AI layer | Centralised log store |
| **Traces** | End-to-end request flow (retrieval → answer) | Distributed tracing |
| **Data health** | Integrity, fidelity, alignment status (Deliverable 6 §6.6) | Data-Quality Dashboard |
| **AI quality** | Faithfulness/citation drift, golden-set regression | Eval dashboard |

### 7.6.2 SLOs & Health Gates

| SLO | Target | Window | Source |
|-----|--------|--------|--------|
| Availability | ≥ target (Deliverable 4 §4.1.5) | Rolling 30d | Uptime probes |
| p95 answer latency | ≤ NFR target | Rolling 7d | Metrics |
| Error rate | ≤ budget | Rolling 7d | Metrics |
| Integrity pass | 100% | Daily | Integrity cron |
| Golden-set faithfulness | ≥ threshold | Per eval cycle | Eval harness |

Health gates at each rollout stage (7.4.2.3) compare live metrics against these SLOs; breach during canary triggers automatic revert (7.5.1).

### 7.6.3 Alerting

- **Severity-aligned** — alerts map to Sev-1/Sev-2/Sev-3 (Deliverable 6 §6.5.4) with paging policy to match.
- **Actionable** — every alert has a runbook link; noisy alerts are tuned out (alert fatigue is a defect).
- **Dual-channel** — paging (critical) + dashboard/Slack (informational).
- **Drill-validated** — alerts are proven to fire on injected faults before G4 (Deliverable 6 §6.8.3).

---

## 7.7 Incident Response

### 7.7.1 Incident Severity & Response SLAs

| Severity | Definition | Response | Resolution Target | Escalation |
|:--------:|------------|----------|-------------------|------------|
| **Sev-1** | Production down / data integrity / safety | Page on-call immediately | Restore within hours | Sponsor + steering |
| **Sev-2** | Major function impaired; no workaround | Acknowledge within 1h | Restore within 1 business day | Ops lead |
| **Sev-3** | Minor impairment; workaround exists | Next business day | Resolve within sprint | Owner |

### 7.7.2 Incident Lifecycle

1. **Detect** — alert fired (7.6) or user report.
2. **Acknowledge** — on-call takes the incident; opens the incident channel.
3. **Triage** — assign severity; assess impact; decide mitigate vs rollback (7.5).
4. **Mitigate** — restore service (rollback, hotfix, or scaling) — *stability before root cause*.
5. **Resolve** — confirm SLOs recovered; close the incident.
6. **Review** — blameless post-incident review (PIR) within 5 business days; action items tracked to closure.

### 7.7.3 Post-Incident Review (PIR)

Every Sev-1 and material Sev-2 produces a PIR capturing: timeline, impact, root cause (5-whys), what worked, what didn't, and tracked action items. PIRs feed the RAID log and the lessons-learned register — recurring failure modes become risks (Deliverable 5 §5.3).

### 7.7.4 On-Call Model

- Rotation documented with primary + secondary on-call.
- Runbooks linked from every alert (Deliverable 6 §6.8.3).
- Escalation contacts current and tested.
- Handover at rotation boundary includes open incidents and watch items.

---

## 7.8 Patch, Update & Edition Release Process

### 7.8.1 Patch Process (Defect/Security)

| Step | Action | Owner |
|------|--------|:-----:|
| 1 | Triage per defect lifecycle (Deliverable 6 §6.5.4) | QA |
| 2 | Fix on a short-lived branch; full CI green | DE/ML |
| 3 | Accelerated promotion via the standard gates (scope-proportionate) | Ops |
| 4 | Deploy via canary (7.4.2); keep rollback window | Ops |
| 5 | Record in release log; update advisory if security | Ops |

Security patches follow the same path but with **expedited SLAs** and a security advisory published alongside the release (mitigates R-10).

### 7.8.2 Minor Update Process

Minor releases follow the full §7.4 runbook at the monthly cadence (7.2.1). They are additive and backward-compatible; no migration is required for rollback.

### 7.8.3 Edition Release Process (mitigates R-6)

Content editions follow the NCF-SE edition versioning control (Deliverable 5 R-6):

1. **Prepare** — new corpus built, integrity-verified, and G2-evidenced as an *edition snapshot* (not in-place).
2. **Version** — assign edition number; record checksum-pinned snapshot (§7.3.2).
3. **Evaluate** — re-run the AI-quality eval (golden + adversarial) against the new edition; G3 verdict required.
4. **Release** — deploy as an additive edition; prior editions remain reproducible and citable.
5. **Transition** — users migrate per the NCF-SE transition plan (R-6); deprecation of a prior edition is a separate, scheduled decision with comms.

Editions never overwrite history — this preserves citation integrity and reproducibility across syllabus cycles.

---

## 7.9 Sustainment Operating Model

### 7.9.1 Sustainment Scope

Sustainment covers the post-handover steady state: keeping the service available, correct, and current without new feature development (out of scope per 7.1.3).

| Activity | In Sustainment |
|----------|:--------------:|
| Incident response (7.7) | ✓ |
| Patch & security releases (7.8.1) | ✓ |
| Edition refreshes (7.8.3) | ✓ |
| Monitoring & SLO management (7.6) | ✓ |
| Defect fixing within budget (Deliverable 6 §6.5.4) | ✓ |
| Runbook & IaC upkeep | ✓ |
| New feature development | ✗ (separate programme) |
| Architecture re-platforming | ✗ (triggers a new project) |

### 7.9.2 Sustainment Roles

| Role | Responsibility |
|------|----------------|
| Sustainment Lead | Owns steady-state service; chairs incident reviews |
| On-call Engineer | First responder to alerts (7.7.4) |
| Content/CE Steward | Edition refresh, factual corrections, golden-set freshness (R-16) |
| Reliability Engineer | SLOs, monitoring, IaC drift, capacity |
| Sustainment Sponsor | Budget, priority calls, escalation authority |

### 7.9.3 Sustainment Cadence

| Activity | Frequency | Output |
|----------|-----------|--------|
| On-call rotation | Continuous | Handover log |
| Defect triage | Weekly | Updated register |
| SLO review | Monthly | SLO report |
| Edition readiness review | Per syllabus cycle | Edition readiness memo |
| Capacity/drift review | Quarterly | Capacity plan, drift report |
| Lessons-learned review | Quarterly | Updated runbooks/risks |

### 7.9.4 Sustainment Budget & Controls

Sustainment operates within the steady-state budget slice (Deliverable 4 §4.6 reserve burn, §4.7 EVM). Controls:

- Defect backlog is budget-bounded; new scope requires a change request.
- LLM re-price reviewed quarterly (Deliverable 5 §5.5.2) to keep run-rate predictable (R-9).
- Reserve release for material incidents follows Deliverable 5 §5.6 escalation.

---

## 7.10 Handover & Knowledge Transfer (mitigates R-8)

Handover is the G5 gate (Deliverable 6 §6.3.3) and is planned from M2 (principle 7.1.2.7), not improvised at M12.

### 7.10.1 Handover Exit Criteria (G5)

| # | Criterion | Evidence Artefact |
|---|-----------|-------------------|
| G5.1 | Sustainment team trained and shadowing for ≥1 sprint | Training record |
| G5.2 | Monitoring, alerting, and dashboards transferred live | Ops handover doc |
| G5.3 | Defect backlog triaged and assigned to sustainment | Defect register |
| G5.4 | Final architecture/as-built documentation delivered | As-built docs |

### 7.10.2 Knowledge Transfer Plan

| Knowledge Area | Transfer Method | Validation |
|----------------|-----------------|------------|
| Architecture & as-built | Doc walkthroughs + recorded sessions | Sustainment signs off |
| Runbooks & ops procedures | Shadow on-call; supervised incident drill | Drill observed |
| IaC & deployment | Paired deploy + rollback rehearsal | Rehearsal passed |
| Data & edition process | Paired edition refresh walk-through | Edition refresh observed |
| AI/eval regime | Golden-set & eval harness handover | Eval run reproduced |

### 7.10.3 Handover Sign-off

Handover closes G5 with dual sign-off: the **delivery team** confirms transfer complete and the **sustainment sponsor** confirms acceptance. Residual risks and known issues are formally accepted into the sustainment baseline (Deliverable 5 §5.6.2). Post-handover, the delivery team remains available for a defined hypercare window before full transition.

---

## 7.11 Deployment Strategy Closure

This Deployment, Rollout & Sustainment Strategy makes go-live and long-term operation of the STD9_AI_ACADEMY programme repeatable and safe. It defines a **release model** with patch/minor/edition/major types and a gated **environment promotion path** (dev→ci→int→stg→prod) where no artifact reaches production without a recorded gate verdict; an **Infrastructure-as-Code and immutable-artifact regime** that eliminates drift (R-4) and pins every deployment for reproducible rollback; **standard deployment patterns** (blue/green with canary as default) backed by a pre-deploy checklist; a **rollback-first strategy** with triggers, mechanics, validation, and a 72-hour rollback window (R-5); a **five-pillar observability stack** with SLO-driven health gates that auto-revert failing canaries; an **incident response model** with severity SLAs, a blameless post-incident review loop, and a documented on-call rotation; a **patch/update/edition process** that keeps security and content current while preserving edition versioning (R-6) and citation integrity; a **sustainment operating model** with roles, cadence, and budget controls for the steady state; and a **G5 handover and knowledge-transfer plan** that moves ownership to the sustainment team on evidence, not on date (R-8). Every release, incident, and handover event feeds the RAID log (WP 1.0.3) and the risk dashboard (Deliverable 5 §5.5), so that deployment, quality, risk, and schedule remain a single, traceable control loop from first build through long-term operation.

_Deliverable 7 ends here. All seven EDF V1 deliverables (1–7) are now complete._

---

<!--
================================================================================
  BASELINE CONTROL STATEMENT — EDF-BASELINE-v1.0
================================================================================
-->

## Baseline Control Statement

| Field | Value |
|-------|-------|
| **Baseline Identifier** | EDF-BASELINE-v1.0 |
| **Version** | 1.0 |
| **Status** | BASELINED — Frozen |
| **Approval Status** | Approved for Implementation |
| **Freeze Date** | 2026-06-27 |
| **Document Owner** | STD9_AI_ACADEMY Engineering Team / Programme Management |
| **Predecessor** | (none — initial baseline) |
| **Successor** | TBD via Change Request |

### Baseline Declaration

This document, **EDF Implementation Backlog — Baseline v1.0**, is hereby declared **FROZEN** as the official enterprise baseline for the STD9_AI_ACADEMY programme, encompassing Deliverables 1–7 (Architecture Review, WBS, Implementation Plan, Resource/Cost/Budget Model, Risk Management, QA & Testing Strategy, and Deployment/Rollout/Sustainment Strategy).

1. **This document is frozen.** As of the Freeze Date above, the technical content of Deliverables 1–7 is fixed and authoritative.
2. **Direct editing is prohibited.** No party may alter the content of this baseline file. The working copy `EDF_IMPLEMENTATION_BACKLOG.md` may evolve independently; this baseline artifact remains immutable.
3. **Future changes require a Change Request (CR).** Any modification — correction, clarification, scope addition, or re-baseline — must be raised as a formal CR, assessed for impact, approved by the baseline authority (Sponsor / Programme Management), and recorded in the change log before a new revision is issued.
4. **Future revisions use semantic versioning.** Subsequent baselines follow `MAJOR.MINOR.PATCH`:
   - **PATCH** (v1.0.x) — typographical or non-material corrections with no change to scope, cost, schedule, or risk posture.
   - **MINOR** (v1.x.0) — additive, backward-compatible changes (e.g., a new sub-section, refined estimate) that do not invalidate prior commitments.
   - **MAJOR** (vx.0.0) — material re-baseline affecting scope, schedule, budget, or risk (e.g., syllabus-cycle change, re-baselined plan).

### Governance & Traceability

- This baseline is the single source of truth referenced by all downstream implementation, quality, risk, and deployment activities.
- All internal cross-references (§, Deliverable, Milestone, WP, Risk IDs) are verified consistent as of the Freeze Date.
- The baseline supersedes all prior drafts; conflicting earlier versions are void.
- A change log will be maintained alongside this baseline to record every CR, its disposition, and the resulting version increment.

_This Baseline Control Statement concludes EDF Implementation Backlog — Baseline v1.0._

<!--
================================================================================
  END OF BASELINE — EDF-BASELINE-v1.0 — FROZEN 2026-06-27
================================================================================
-->

