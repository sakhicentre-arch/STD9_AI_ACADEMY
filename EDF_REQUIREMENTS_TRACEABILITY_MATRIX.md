# EDF Requirements Traceability Matrix (RTM)

> **Project:** STD9_AI_ACADEMY — Std 9 Educational Content Corpus (GSEB + NCERT)
> **Document Owner:** STD9_AI_ACADEMY Engineering Team / Programme Management
> **Version:** 1.0
> **Status:** TRACEABILITY BASELINE
> **Created:** 2026-06-27
> **Basis:** EDF_IMPLEMENTATION_BACKLOG_BASELINE_v1.md (Deliverables 1–7)
> **Companion documents (currently ABSENT — see §7 Gap Analysis):** EDF_MASTER_ARCHITECTURE.md, EDF_SOURCE_REGISTRY.md, EDF_DATA_MODEL.md, EDF_SOURCE_ADAPTER_SPEC.md

---

## Section 1 — RTM Overview

### 1.1 Purpose

This Requirements Traceability Matrix (RTM) is the master mapping that links every business and engineering requirement of the STD9_AI_ACADEMY programme — from research and architecture, through the frozen Baseline v1.0 — to the future specifications, implementation components, tests, and deployment artefacts that will satisfy them. Its purpose is to make **coverage and gaps visible at all times**, so that no requirement is silently dropped and every implemented component, test, and release can be traced back to a documented need.

The RTM is a **living governance document**: requirement rows are stable once baselined, but their architecture/implementation/test mapping columns are updated as specifications are authored (EDF-L1) and code is written (EDF-L2). It does not itself define requirements — it indexes requirements already established in the Baseline.

### 1.2 Scope

In scope:
- All functional and non-functional requirements implied by the Baseline v1.0 — specifically the architecture strengths/weaknesses, missing components (Baseline §7), technical debt (Baseline §6 TD-1…TD-15), the 86 work packages of the WBS (Baseline §2.2), the NFRs (Baseline §4.1.5), and the 17 risks (Baseline §5.2, R-1…R-17).
- Mapping each requirement to architecture, data model, source registry, adapter spec (future documents), implementation modules/services, and test tiers (Baseline §6.2 test pyramid L0–L5).

Out of scope:
- End-user tutor-UI product requirements (separate programme).
- Vendor contract or procurement requirements.
- Inventing requirements not grounded in the Baseline.

### 1.3 Traceability Philosophy

1. **Single source of truth.** The Baseline v1.0 is authoritative; this RTM indexes it. Where a future specification document is referenced but does not yet exist, the mapping cell is marked **[PLANNED DOC]** — a traceability gap, not an error.
2. **Requirement IDs are immutable.** Once a requirement receives an ID (EDF-REQ-nnnn), the ID is never reused or renumbered. Obsolete requirements are marked `Status: Withdrawn`, never deleted.
3. **Bidirectional trace.** Every requirement traces forward (→ implementation → test → deployment) and backward (← source). A component with no backward trace is unauthorised scope; a requirement with no forward trace is an uncovered gap.
4. **Phased rollout.** Each requirement is tagged to a phase — **L1** (specification), **L2** (implementation), **L3** (deployment/sustainment) — matching the EDF execution phases.
5. **Test tiers map to the Baseline pyramid (§6.2).** L0 static / L1 unit / L2 data-quality / L3 integration / L4 E2E / L5 acceptance.
6. **Proportionate rigour.** P0/Critical requirements carry the deepest trace (all four test tiers + deployment evidence); P2/Low requirements may trace to a single unit test.

### 1.4 How to Use This Matrix

- **Requirement owners** consult §2 to confirm their requirement's ID, priority, and phase.
- **Architects** consult §3 to author the planned specification documents and resolve `[PLANNED DOC]` cells.
- **Engineers** consult §4 to know which component satisfies which requirement.
- **QA** consults §5 to design tests that close each requirement's verification trace.
- **PM/Ops** consult §6 (coverage dashboard) and §7 (gap analysis) at each gate to confirm no requirement is uncovered.

### 1.5 ID Conventions

| Prefix | Meaning |
|--------|---------|
| `EDF-REQ-nnnn` | Requirement (this matrix, §2) |
| Baseline `§n.n` | Section of EDF_IMPLEMENTATION_BACKLOG_BASELINE_v1.md |
| Baseline `WP 1.n.n` | Work package (Baseline §2.2) |
| Baseline `TD-n` | Technical-debt item (Baseline §6) |
| Baseline `R-n` | Risk (Baseline §5.2) |
| Baseline `G1…G5` | Quality gate (Baseline §6.3) |
| `[PLANNED DOC]` | Referenced specification not yet authored (see §7) |
| `[PLANNED MODULE]` | Implementation component not yet built (see §7) |

---

## Section 2 — Requirement Register

Every requirement is grounded in a specific Baseline element (work package, technical-debt item, NFR, risk, or missing-component). IDs are assigned sequentially within categories. **Priority:** P0 (critical/blocking) · P1 (high) · P2 (medium/low). **Phase:** L1 (specification) · L2 (implementation) · L3 (deployment/sustainment).

### 2.1 Governance & Programme Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0001 | Governance / Version Control | Workspace placed under git with baseline commit, remote mirror, and binary/LFS policy. | Baseline WP 1.1.1; TD-7 | P0 | L1 |
| EDF-REQ-0002 | Governance / Licensing | Per-tier licensing & redistribution policy; quarantine rule for `_REF_3P`; attribution requirements documented. | Baseline WP 1.1.2; R-10 | P0 | L1 |
| EDF-REQ-0003 | Governance / Change Mgmt | Change-request workflow, configuration-item register, protected-branch rules. | Baseline WP 1.1.3 | P1 | L1 |
| EDF-REQ-0004 | Governance / Metadata | Mandatory metadata-header standard on all content files, with pre-commit lint enforcement. | Baseline WP 1.1.4; TD-4 | P0 | L1 |
| EDF-REQ-0005 | Governance / Audit | Governance readiness report and sponsor sign-off before downstream gates. | Baseline WP 1.1.5 | P1 | L2 |
| EDF-REQ-0006 | Programme / Charter | Approved programme charter with frozen, version-controlled scope boundaries. | Baseline WP 1.0.1 | P0 | L1 |
| EDF-REQ-0007 | Programme / WBS Baseline | WBS baselined, owner-acknowledged, committed to version control. | Baseline WP 1.0.2 | P0 | L1 |
| EDF-REQ-0008 | Programme / Integration | Inter-branch integration plan, weekly status cadence, RAID log live. | Baseline WP 1.0.3 | P0 | L2 |

### 2.2 Acquisition Pipeline Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0009 | Acquisition / Orchestrator | Acquisition orchestrator reads the source registry and downloads Tier-1 PDFs into `RAW/`. | Baseline WP 1.3.1; §7.1 | P0 | L2 |
| EDF-REQ-0010 | Acquisition / NCERT Resilience | Retry/rate-limit middleware for known-flaky `ncert.nic.in` (HTTP 000/TLS drops). | Baseline §8.1; WP 1.3.2 | P0 | L2 |
| EDF-REQ-0011 | Acquisition / GSSTB Navigator | Portal-navigation acquisition for GSEB (no direct PDF URLs), per medium/subject. | Baseline §8.1; TD-12; WP 1.3.3 | P1 | L2 |
| EDF-REQ-0012 | Acquisition / Idempotency | Re-runnable acquisition that resumes without duplicating or corrupting existing assets. | Baseline §6.1.3 (pipeline quality) | P0 | L2 |
| EDF-REQ-0013 | Acquisition / Manifest Emission | Each acquired file produces a manifest entry at write time. | Baseline WP 1.3.4; §7.1 | P0 | L2 |
| EDF-REQ-0014 | Acquisition / Tier Quarantine | Tier-3/4 third-party PDFs quarantined to `_REF_3P`, never treated as primary. | Baseline §4.8; R-10 | P0 | L2 |

### 2.3 Integrity Layer Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0015 | Integrity / Checksum | SHA-256 checksum computed and persisted for every RAW asset. | Baseline WP 1.3.5; TD-5; §7.2 | P0 | L2 |
| EDF-REQ-0016 | Integrity / Verification | Re-verification routine to detect drift/corruption on demand and on schedule (daily). | Baseline §6.6.1; R-2 | P0 | L2 |
| EDF-REQ-0017 | Integrity / PDF Validity | Each file validated as a real PDF (not an HTML error page) before acceptance. | Baseline §7.2; WP 1.3.6 | P0 | L2 |
| EDF-REQ-0018 | Integrity / Chain-of-Custody | Source → transit → post-extract → storage checksum chain recorded per asset; no asset crosses G2 without it. | Baseline §6.6.1; G2 | P0 | L2 |
| EDF-REQ-0019 | Integrity / Quarantine on Failure | Mismatch is a Sev-1 event: asset quarantined, pipeline halts, R-2 raised to Red. | Baseline §6.6.1; §5.4 | P0 | L2 |

### 2.4 Extraction & Normalisation Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0020 | Extraction / Text | PDF text extractor producing clean markdown/text for born-digital PDFs. | Baseline WP 1.4.1; §7.3; TD-10 | P0 | L2 |
| EDF-REQ-0021 | Extraction / OCR | OCR fallback for scanned GSEB Gujarati-medium editions. | Baseline WP 1.4.2; §7.3 | P1 | L2 |
| EDF-REQ-0022 | Extraction / Segmentation | Chapter segmentation aligned to the catalogue; per-chapter structured units. | Baseline WP 1.4.3; §7.3 | P1 | L2 |
| EDF-REQ-0023 | Extraction / Fidelity | Character-level fidelity ≥99.0%, structural fidelity ≥95%, 100% referenced assets captured, Unicode NFC/NFKC normalisation. | Baseline §6.6.2 | P0 | L2 |
| EDF-REQ-0024 | Extraction / Output Store | Deterministic `CONTENT/PROCESSED/**` naming for extracted/normalised text. | Baseline §7.3 | P1 | L2 |

### 2.5 Structured Knowledge Representation Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0025 | Data / Manifest Schema | Manifest schema (JSON/YAML): id, source, tier, subject, board, medium, chapter, edition, checksum, download date, status. | Baseline WP 1.5.1; §7.4; TD-11 | P0 | L1 |
| EDF-REQ-0026 | Data / Chapter Index | Machine-readable (board, subject, chapter) → asset(s) mapping. | Baseline WP 1.5.2; §7.4 | P0 | L2 |
| EDF-REQ-0027 | Data / Catalogue SSOT | Single-source-of-truth catalogue; retire `SOURCES.md` duplication of `SOURCE_REGISTRY.md`. | Baseline WP 1.5.3; TD-3 | P1 | L2 |
| EDF-REQ-0028 | Data / Master Inventory | Populated master inventory back-filled from DOWNLOAD_LOG. | Baseline WP 1.5.4; TD-2 | P1 | L2 |
| EDF-REQ-0029 | Data / Data Model | Formal data model for corpus entities (board, subject, chapter, asset, edition, source). | [PLANNED DOC] EDF_DATA_MODEL.md | P0 | L1 |

### 2.6 Curriculum Validation & Factual Correctness Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0030 | Curriculum / Factual Corrections | Six uncorrected audit inaccuracies (Maitri claim, Beehive list, "11 prose", NCERT codes, GSEB chapter lists, ~-estimates) fixed in live Markdown. | Baseline TD-1; WP 1.5.5 | P0 | L2 |
| EDF-REQ-0031 | Curriculum / Validation Doc | `CURRICULUM_VALIDATION.md` authored (currently referenced but absent). | Baseline §7.4 | P0 | L1 |
| EDF-REQ-0032 | Curriculum / Coverage Map | Every syllabus objective maps to ≥1 asset; 100% coverage reported at G2/G4. | Baseline §6.6.4; G2 | P0 | L2 |
| EDF-REQ-0033 | Curriculum / Tier Conflict Resolution | Tier-1/Tier-2 factual conflicts escalated via guardrails + validation, never silently resolved. | Baseline §6.6.3; R-1 | P0 | L2 |
| EDF-REQ-0034 | Curriculum / NCF-SE Edition | NCF-SE 2026-27 transition handled via edition versioning; prior editions reproducible. | Baseline §7.5; R-6 | P1 | L3 |

### 2.7 AI / Retrieval-Augmented Generation Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0035 | AI / Embeddings & Vector Store | Extracted text embedded and indexed in a vector store for retrieval. | Baseline §5 (missing structured rep); WP 1.7.x | P0 | L2 |
| EDF-REQ-0036 | AI / Retrieval | Retrieval returning the right evidence first (Precision@k, Recall@k targets). | Baseline §6.7.1; G3 | P0 | L2 |
| EDF-REQ-0037 | AI / Faithfulness | Answers use only retrieved evidence; no invented facts (faithfulness ≥ threshold on golden set). | Baseline §6.7.1; R-1 | P0 | L2 |
| EDF-REQ-0038 | AI / Citation Correctness | Every claim cites a real, supportive source (citation precision ≥ threshold). | Baseline §6.7.1; R-1 | P0 | L2 |
| EDF-REQ-0039 | AI / Hallucination Resistance | Robustness to misleading/out-of-scope queries (hallucination rate ≤ threshold on adversarial set). | Baseline §6.7.1; G3 | P0 | L2 |
| EDF-REQ-0040 | AI / Guardrails | Prevent over-generation; balance against not refusing answerable questions. | Baseline §6.7.3; R-1 | P0 | L2 |
| EDF-REQ-0041 | AI / Prompt & Model Versioning | Prompts and model endpoints versioned alongside code; change triggers full eval. | Baseline §6.7.4; reproducibility | P1 | L2 |
| EDF-REQ-0042 | AI / Golden Set | Curated Q/A/reference golden set, versioned, read-only in CI, reviewed per eval cycle. | Baseline §6.7.2; R-16 | P0 | L2 |
| EDF-REQ-0043 | AI / Eval Harness | Automated scorers (faithfulness, groundedness, citation) + adversarial set + human spot-check. | Baseline §6.7.2; G3 | P0 | L2 |

### 2.8 Service & API Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0044 | Service / Answer API | Service exposing retrieval-augmented answers to the (out-of-programme) tutor UI. | Baseline WP 1.8.x; §6.4 (in/out scope) | P0 | L2 |
| EDF-REQ-0045 | Service / Contract | Versioned API contract; 100% of public endpoints contract-tested at G4. | Baseline §6.2.2; G4 | P1 | L2 |
| EDF-REQ-0046 | Service / Adapter Spec | Source-adapter specification normalising heterogeneous sources into a uniform ingest interface. | [PLANNED DOC] EDF_SOURCE_ADAPTER_SPEC.md | P0 | L1 |
| EDF-REQ-0047 | Service / Architecture | Master architecture document defining component boundaries and interactions. | [PLANNED DOC] EDF_MASTER_ARCHITECTURE.md | P0 | L1 |
| EDF-REQ-0048 | Service / Source Registry | Authoritative source registry (Tier-1…4) feeding acquisition. | [PLANNED DOC] EDF_SOURCE_REGISTRY.md | P0 | L1 |

### 2.9 Non-Functional Requirements (NFRs)

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0049 | NFR / Performance | p95 answer latency ≤ NFR target under expected load. | Baseline §4.1.5; §6.8.1; G3 | P0 | L2 |
| EDF-REQ-0050 | NFR / Scalability | No degradation over soak window at expected scale. | Baseline §6.8.1 | P1 | L2 |
| EDF-REQ-0051 | NFR / Reliability | Availability ≥ target; fault-injection + monitoring validated. | Baseline §4.1.5; §6.8.1 | P0 | L3 |
| EDF-REQ-0052 | NFR / Security | SAST + DAST + dependency scan + pentest; no High/Critical open at G4. | Baseline §6.8.2; R-10 | P0 | L3 |
| EDF-REQ-0053 | NFR / Maintainability | Coverage (§6.2.2), lint, complexity non-regressing in CI. | Baseline §6.8.1 | P1 | L2 |
| EDF-REQ-0054 | NFR / Accessibility | WCAG conformance via a11y scan + manual check. | Baseline §6.8.1 | P2 | L2 |
| EDF-REQ-0055 | NFR / Observability | Metrics, logs, traces, dashboards deployed with features; alerts fire on injected faults. | Baseline §6.6; §7.6 | P0 | L3 |

### 2.10 Quality Assurance Infrastructure Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0056 | QA / Test Pyramid | Content-aware test pyramid L0–L5 operational with frozen coverage targets. | Baseline §6.2; WP 1.9.x | P0 | L2 |
| EDF-REQ-0057 | QA / CI Pipeline | Fail-fast CI: lint → schema → unit+coverage → integrity (hard stop) → integration → eval → E2E. | Baseline §6.5.2 | P0 | L2 |
| EDF-REQ-0058 | QA / Quality Gates | Gates G1–G5 with entry/exit criteria, evidence packs, waiver authority. | Baseline §6.3; WP 1.9.2 | P0 | L2 |
| EDF-REQ-0059 | QA / Test Environments | dev/ci/int/stg/prod environments with defined promotion path. | Baseline §6.4.1; §7.2.2 | P0 | L2 |
| EDF-REQ-0060 | QA / Test Data | Fixtures, golden set, anonymised corpus, adversarial set with hygiene rules. | Baseline §6.4.2 | P1 | L2 |

### 2.11 Deployment & Sustainment Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0061 | Deploy / IaC | All environments defined as version-controlled IaC; drift detection. | Baseline §7.3.1; R-4 | P0 | L3 |
| EDF-REQ-0062 | Deploy / Artifact Mgmt | Immutable, pinned artifacts (builds, images, corpus snapshots, model versions, manifests). | Baseline §7.3.2 | P0 | L3 |
| EDF-REQ-0063 | Deploy / Patterns | Blue/green with canary as default; rolling/recreate where appropriate. | Baseline §7.4.1 | P0 | L3 |
| EDF-REQ-0064 | Deploy / Rollback | Rollback-first: triggers, mechanics, validation, ≥72h rollback window. | Baseline §7.5; R-5 | P0 | L3 |
| EDF-REQ-0065 | Deploy / Edition Release | Edition releases additive & versioned; prior editions reproducible/citable. | Baseline §7.8.3; R-6 | P1 | L3 |
| EDF-REQ-0066 | Ops / Incident Response | Severity SLAs, blameless PIR, on-call rotation, runbooks. | Baseline §7.7 | P0 | L3 |
| EDF-REQ-0067 | Ops / Sustainment Model | Sustainment roles, cadence, budget-bounded defect fixing. | Baseline §7.9 | P1 | L3 |
| EDF-REQ-0068 | Ops / Handover | G5 handover: training, shadowing, as-built docs, dual sign-off. | Baseline §7.10; R-8; G5 | P0 | L3 |

### 2.12 Risk-Derived Control & Remaining Debt Requirements

| Requirement ID | Category | Description | Source Document | Priority | Phase |
|----------------|----------|-------------|-----------------|:--------:|:-----:|
| EDF-REQ-0069 | Risk Control / Manual Acquisition | Zero manual acquisition steps remaining after M6 (automation complete). | Baseline R-9 | P0 | L2 |
| EDF-REQ-0070 | Risk Control / LLM Cost | LLM $/1k-queries trended quarterly; within +30% tolerance. | Baseline R-11; §5.5.2 | P1 | L3 |
| EDF-REQ-0071 | Risk Control / SPI-CPI | Schedule/Cost performance index ≥0.9; re-baseline trigger if breached 2 sprints. | Baseline R-13; §4.7 | P1 | L3 |
| EDF-REQ-0072 | Debt / NCERT Back-fill | Complete partial NCERT downloads (Maths/English/Social/Hindi/Sanskrit/Urdu, exemplars, lab manual, model papers). | Baseline TD-8; §7.6 | P0 | L2 |
| EDF-REQ-0073 | Debt / GSEB Corpus | Acquire all 10 GSSTB books across mediums (GSEB RAW currently empty). | Baseline §7.6; TD-15 | P0 | L2 |
| EDF-REQ-0074 | Debt / Science Reconciliation | Reconcile Science chapter-count mismatch (13 vs 12) against rationalised list. | Baseline TD-9 | P1 | L2 |
| EDF-REQ-0075 | Debt / NCERT Code Verification | Verify NCERT textbook codes against master list PDF. | Baseline TD-6 | P2 | L2 |
| EDF-REQ-0076 | Debt / Stray Artifacts | Remove stray `nul` and `DEBUG/` artefacts from corpus area. | Baseline TD-13 | P2 | L1 |
| EDF-REQ-0077 | Debt / Validation Gates | Automated manifest/integrity/completeness assertions as tests. | Baseline TD-14; §6.5 | P1 | L2 |

### 2.13 Register Summary

| Metric | Value |
|--------|------:|
| Total requirements | **77** |
| By Priority — P0 (critical) | 51 |
| By Priority — P1 (high) | 19 |
| By Priority — P2 (medium/low) | 7 |
| By Phase — L1 (specification) | 15 |
| By Phase — L2 (implementation) | 40 |
| By Phase — L3 (deployment/sustainment) | 22 |
| Categories | 12 |

---

## Section 3 — Requirement → Architecture / Data / Source / Adapter Mapping

This section maps each requirement to its architecture home, the data-model entity it touches, the source-registry tier it depends on, and the adapter concern it implies. Cells marked **[PLANNED DOC]** reference specifications that must be authored in EDF-L1; until authored, the mapping is directional only.

### 3.1 Architecture Mapping

| Requirement ID | Architecture Section / Component | Data Model Entity | Source Registry Tier | Adapter Concern |
|----------------|----------------------------------|-------------------|:--------------------:|-----------------|
| EDF-REQ-0001 | Governance / VCS layer (Baseline §1.1) | (meta — repo) | — | — |
| EDF-REQ-0002 | Governance / Licensing (Baseline §1.1.2) | Licence, Tier | Tier-1…4 | Per-tier quarantine adapter |
| EDF-REQ-0003 | Governance / Change Mgmt (Baseline §1.1.3) | ConfigurationItem | — | — |
| EDF-REQ-0004 | Governance / Metadata (Baseline §1.1.4) | MetadataHeader | — | — |
| EDF-REQ-0005 | Governance / Audit | AuditFinding | — | — |
| EDF-REQ-0006 | Programme / Charter | ScopeBoundary | — | — |
| EDF-REQ-0007 | Programme / WBS | WorkPackage | — | — |
| EDF-REQ-0008 | Programme / Integration | Dependency, Risk | — | — |
| EDF-REQ-0009 | Acquisition / Orchestrator (Baseline §7.1) | Asset, ManifestEntry | Tier-1 (GSSTB, NCERT) | [PLANNED DOC] Adapter |
| EDF-REQ-0010 | Acquisition / Resilience middleware | ManifestEntry | Tier-1 (NCERT) | NCERT retry adapter |
| EDF-REQ-0011 | Acquisition / GSSTB navigator | Asset | Tier-1 (GSSTB) | Portal-navigation adapter |
| EDF-REQ-0012 | Acquisition / Idempotency | Asset, ManifestEntry | Tier-1…2 | — |
| EDF-REQ-0013 | Acquisition / Manifest emission | ManifestEntry | Tier-1…2 | — |
| EDF-REQ-0014 | Acquisition / Quarantine | Asset (ref-flag) | Tier-3/4 | `_REF_3P` quarantine adapter |
| EDF-REQ-0015 | Integrity / Checksum (Baseline §7.2) | Asset.checksum | — | — |
| EDF-REQ-0016 | Integrity / Verification | Asset.checksum | — | — |
| EDF-REQ-0017 | Integrity / PDF validity | Asset.format | — | — |
| EDF-REQ-0018 | Integrity / Chain-of-custody | Asset, ManifestEntry | — | — |
| EDF-REQ-0019 | Integrity / Quarantine | Asset.status | — | — |
| EDF-REQ-0020 | Extraction / Text (Baseline §7.3) | ExtractedText | — | PDF-text adapter |
| EDF-REQ-0021 | Extraction / OCR | ExtractedText | Tier-1 (GSEB Gujarati) | OCR adapter |
| EDF-REQ-0022 | Extraction / Segmentation | Chapter | — | Catalogue-alignment adapter |
| EDF-REQ-0023 | Extraction / Fidelity | ExtractedText (metrics) | — | — |
| EDF-REQ-0024 | Extraction / Output store | ExtractedText (path) | — | — |
| EDF-REQ-0025 | Data / Manifest schema (Baseline §7.4) | ManifestEntry | — | — |
| EDF-REQ-0026 | Data / Chapter index | Chapter, Asset | — | — |
| EDF-REQ-0027 | Data / Catalogue SSOT | Catalogue, Source | Tier-1…4 | — |
| EDF-REQ-0028 | Data / Master inventory | Asset | — | — |
| EDF-REQ-0029 | Data / Data model | (all entities) | — | [PLANNED DOC] EDF_DATA_MODEL.md |
| EDF-REQ-0030 | Curriculum / Corrections | Catalogue, AuditFinding | — | — |
| EDF-REQ-0031 | Curriculum / Validation doc | CurriculumObjective | — | — |
| EDF-REQ-0032 | Curriculum / Coverage map | CurriculumObjective, Asset | — | — |
| EDF-REQ-0033 | Curriculum / Conflict resolution | Source (tier), AuditFinding | Tier-1/2 | — |
| EDF-REQ-0034 | Curriculum / NCF-SE edition | Edition | — | — |

### 3.2 AI / Service / NFR Architecture Mapping

| Requirement ID | Architecture Section / Component | Data Model Entity | Source Registry Tier | Adapter Concern |
|----------------|----------------------------------|-------------------|:--------------------:|-----------------|
| EDF-REQ-0035 | AI / Embeddings & vector store (Baseline §7.4) | Embedding, Asset | — | — |
| EDF-REQ-0036 | AI / Retrieval | Embedding, Citation | — | — |
| EDF-REQ-0037 | AI / Faithfulness | Citation, Answer | — | — |
| EDF-REQ-0038 | AI / Citation correctness | Citation | Tier-1/2 | — |
| EDF-REQ-0039 | AI / Hallucination resistance | Answer, AdversarialQuery | — | — |
| EDF-REQ-0040 | AI / Guardrails | Answer | — | — |
| EDF-REQ-0041 | AI / Prompt & model versioning | ModelVersion, Prompt | — | — |
| EDF-REQ-0042 | AI / Golden set | GoldenItem | — | — |
| EDF-REQ-0043 | AI / Eval harness | EvalResult | — | — |
| EDF-REQ-0044 | Service / Answer API (Baseline §1.8) | Answer, Citation | — | — |
| EDF-REQ-0045 | Service / Contract | Endpoint | — | — |
| EDF-REQ-0046 | Service / Adapter spec | Source, Adapter | Tier-1…4 | [PLANNED DOC] EDF_SOURCE_ADAPTER_SPEC.md |
| EDF-REQ-0047 | Service / Master architecture | (all components) | — | [PLANNED DOC] EDF_MASTER_ARCHITECTURE.md |
| EDF-REQ-0048 | Service / Source registry | Source | Tier-1…4 | [PLANNED DOC] EDF_SOURCE_REGISTRY.md |
| EDF-REQ-0049 | NFR / Performance | SLO | — | — |
| EDF-REQ-0050 | NFR / Scalability | SLO | — | — |
| EDF-REQ-0051 | NFR / Reliability | SLO | — | — |
| EDF-REQ-0052 | NFR / Security | Finding | — | — |
| EDF-REQ-0053 | NFR / Maintainability | (meta — CI) | — | — |
| EDF-REQ-0054 | NFR / Accessibility | (meta — UI contract) | — | — |
| EDF-REQ-0055 | NFR / Observability | Metric, Log, Trace | — | — |
| EDF-REQ-0056 | QA / Test pyramid | TestResult | — | — |
| EDF-REQ-0057 | QA / CI pipeline | Build, TestResult | — | — |
| EDF-REQ-0058 | QA / Quality gates | GateVerdict | — | — |
| EDF-REQ-0059 | QA / Environments | Environment | — | — |
| EDF-REQ-0060 | QA / Test data | Fixture, GoldenItem | — | — |
| EDF-REQ-0061 | Deploy / IaC | Environment, IaC | — | — |
| EDF-REQ-0062 | Deploy / Artifacts | Artifact, Release | — | — |
| EDF-REQ-0063 | Deploy / Patterns | Environment | — | — |
| EDF-REQ-0064 | Deploy / Rollback | Release | — | — |
| EDF-REQ-0065 | Deploy / Edition release | Edition, Release | — | — |
| EDF-REQ-0066 | Ops / Incident response | Incident, Alert | — | — |
| EDF-REQ-0067 | Ops / Sustainment | Incident, Defect | — | — |
| EDF-REQ-0068 | Ops / Handover | HandoverRecord | — | — |
| EDF-REQ-0069 | Risk / Manual acquisition | Asset, ManifestEntry | Tier-1…2 | — |
| EDF-REQ-0070 | Risk / LLM cost | CostMetric | — | — |
| EDF-REQ-0071 | Risk / SPI-CPI | EVM (Baseline §4.7) | — | — |
| EDF-REQ-0072 | Debt / NCERT back-fill | Asset | Tier-1 (NCERT) | NCERT adapter |
| EDF-REQ-0073 | Debt / GSEB corpus | Asset | Tier-1 (GSSTB) | GSSTB navigator adapter |
| EDF-REQ-0074 | Debt / Science reconciliation | Chapter, Asset | — | — |
| EDF-REQ-0075 | Debt / NCERT codes | Asset.code | — | — |
| EDF-REQ-0076 | Debt / Stray artifacts | (meta — repo) | — | — |
| EDF-REQ-0077 | Debt / Validation gates | TestResult | — | — |

### 3.3 Specification Documents Required (Forward Trace)

The architecture mapping resolves to these specification documents. Those marked **ABSENT** are §7 gap items.

| Required Spec | Status | Satisfies |
|---------------|:------:|-----------|
| EDF_MASTER_ARCHITECTURE.md | **ABSENT** | EDF-REQ-0047 |
| EDF_SOURCE_REGISTRY.md | **ABSENT** | EDF-REQ-0048 |
| EDF_DATA_MODEL.md | **ABSENT** | EDF-REQ-0029 |
| EDF_SOURCE_ADAPTER_SPEC.md | **ABSENT** | EDF-REQ-0046 |

---

## Section 4 — Requirement → Implementation Mapping

Maps each requirement to its future implementation component. **Module** = code unit; **Service** = deployable service; **DB** = datastore/entity; **API** = interface; **UI** = user-facing surface (mostly out-of-programme); **AI** = AI/ML component. `[PLANNED MODULE]` = not yet built (§7 gap).

### 4.1 Governance / Acquisition / Integrity / Extraction / Data Implementation

| Requirement ID | Future Module / Service | DB / Store | API | UI | AI |
|----------------|-------------------------|------------|-----|:--:|:--:|
| EDF-REQ-0001 | VCS / gitops module | repo (meta) | — | — | — |
| EDF-REQ-0002 | Licensing-policy service | licence store | /licences | admin | — |
| EDF-REQ-0003 | Change-mgmt service | CI register | /changes | admin | — |
| EDF-REQ-0004 | Metadata-lint module (pre-commit) | content store | — | — | — |
| EDF-REQ-0005 | Governance-audit service | audit store | /governance | admin | — |
| EDF-REQ-0006 | Programme-charter doc tooling | doc store | — | — | — |
| EDF-REQ-0007 | WBS-baseline module | doc store | — | — | — |
| EDF-REQ-0008 | Integration / RAID service | RAID store | /raid | PM | — |
| EDF-REQ-0009 | [PLANNED MODULE] `acquire` orchestrator | RAW store, manifest DB | /acquire | — | — |
| EDF-REQ-0010 | [PLANNED MODULE] NCERT retry middleware | manifest DB | — | — | — |
| EDF-REQ-0011 | [PLANNED MODULE] GSSTB navigator | RAW store | — | — | — |
| EDF-REQ-0012 | [PLANNED MODULE] Idempotent acquire controller | manifest DB | — | — | — |
| EDF-REQ-0013 | [PLANNED MODULE] Manifest writer | manifest DB | — | — | — |
| EDF-REQ-0014 | [PLANNED MODULE] Quarantine router | RAW store (`_REF_3P`) | — | — | — |
| EDF-REQ-0015 | [PLANNED MODULE] Checksum service | Asset.checksum | /checksum | — | — |
| EDF-REQ-0016 | [PLANNED MODULE] Integrity verifier | Asset.checksum | /verify | — | — |
| EDF-REQ-0017 | [PLANNED MODULE] PDF-validity checker | Asset.format | — | — | — |
| EDF-REQ-0018 | [PLANNED MODULE] Chain-of-custody service | manifest DB | — | — | — |
| EDF-REQ-0019 | [PLANNED MODULE] Quarantine-on-fail controller | Asset.status | — | — | — |
| EDF-REQ-0020 | [PLANNED MODULE] PDF text extractor | PROCESSED store | — | — | — |
| EDF-REQ-0021 | [PLANNED MODULE] OCR fallback | PROCESSED store | — | — | — |
| EDF-REQ-0022 | [PLANNED MODULE] Chapter segmenter | Chapter store | — | — | — |
| EDF-REQ-0023 | [PLANNED MODULE] Fidelity scorer | PROCESSED store (metrics) | — | — | — |
| EDF-REQ-0024 | [PLANNED MODULE] Normalised output store | PROCESSED store | — | — | — |
| EDF-REQ-0025 | [PLANNED MODULE] Manifest schema (pydantic/jsonschema) | manifest DB | — | — | — |
| EDF-REQ-0026 | [PLANNED MODULE] Chapter-index service | Chapter index | /index | — | — |
| EDF-REQ-0027 | [PLANNED MODULE] Catalogue SSOT service | Catalogue store | — | — | — |
| EDF-REQ-0028 | [PLANNED MODULE] Master-inventory builder | Inventory store | /inventory | — | — |
| EDF-REQ-0029 | [PLANNED DOC] Data model | (defines entities) | — | — | — |
| EDF-REQ-0030 | [PLANNED MODULE] Factual-correction migration | Catalogue store | — | — | — |
| EDF-REQ-0031 | [PLANNED DOC] Curriculum validation | Curriculum store | — | — | — |
| EDF-REQ-0032 | [PLANNED MODULE] Coverage-map service | CurriculumObjective ↔ Asset | /coverage | — | — |
| EDF-REQ-0033 | [PLANNED MODULE] Tier-conflict resolver | AuditFinding | — | — | — |
| EDF-REQ-0034 | [PLANNED MODULE] Edition-versioning service | Edition | — | — | — |

### 4.2 AI / Service / NFR / QA / Ops Implementation

| Requirement ID | Future Module / Service | DB / Store | API | UI | AI |
|----------------|-------------------------|------------|-----|:--:|:--:|
| EDF-REQ-0035 | [PLANNED MODULE] Embedding/indexer service | Vector store | /index/embed | — | ✓ |
| EDF-REQ-0036 | [PLANNED MODULE] Retriever service | Vector store | /retrieve | — | ✓ |
| EDF-REQ-0037 | [PLANNED MODULE] Answer generator | Answer | /answer | — | ✓ |
| EDF-REQ-0038 | [PLANNED MODULE] Citation service | Citation | — | — | ✓ |
| EDF-REQ-0039 | [PLANNED MODULE] Adversarial-test runner | EvalResult | — | — | ✓ |
| EDF-REQ-0040 | [PLANNED MODULE] Guardrail module | Answer | — | — | ✓ |
| EDF-REQ-0041 | [PLANNED MODULE] Prompt/model registry | ModelVersion, Prompt | — | — | ✓ |
| EDF-REQ-0042 | [PLANNED MODULE] Golden-set store | GoldenItem | — | — | ✓ |
| EDF-REQ-0043 | [PLANNED MODULE] Eval harness | EvalResult | /eval | — | ✓ |
| EDF-REQ-0044 | [PLANNED MODULE] Answer API (tutor-facing) | Answer, Citation | /v1/answer | (out-of-programme) | ✓ |
| EDF-REQ-0045 | [PLANNED MODULE] Contract-test suite | Endpoint | — | — | — |
| EDF-REQ-0046 | [PLANNED DOC] Adapter spec | Adapter | — | — | — |
| EDF-REQ-0047 | [PLANNED DOC] Master architecture | (defines modules) | — | — | — |
| EDF-REQ-0048 | [PLANNED DOC] Source registry | Source | — | — | — |
| EDF-REQ-0049 | [PLANNED MODULE] Load-test harness | SLO store | — | — | — |
| EDF-REQ-0050 | [PLANNED MODULE] Soak-test harness | SLO store | — | — | — |
| EDF-REQ-0051 | [PLANNED MODULE] Fault-injection suite | SLO store | — | — | — |
| EDF-REQ-0052 | [PLANNED MODULE] Security-test suite (SAST/DAST/pentest) | Finding | — | — | — |
| EDF-REQ-0053 | [PLANNED MODULE] Coverage/lint/complexity gates | CI store | — | — | — |
| EDF-REQ-0054 | [PLANNED MODULE] a11y scanner | Finding | — | — | — |
| EDF-REQ-0055 | [PLANNED MODULE] Telemetry/tracing/logging stack | Metrics/Logs/Traces | /metrics | ops | — |
| EDF-REQ-0056 | [PLANNED MODULE] Test-pyramid harness | TestResult | — | — | — |
| EDF-REQ-0057 | [PLANNED MODULE] CI pipeline orchestrator | Build, TestResult | — | — | — |
| EDF-REQ-0058 | [PLANNED MODULE] Gate-evidence service | GateVerdict | /gates | — | — |
| EDF-REQ-0059 | [PLANNED MODULE] Environment-provisioning (IaC) | Environment | — | — | — |
| EDF-REQ-0060 | [PLANNED MODULE] Test-data management | Fixture, GoldenItem | — | — | — |
| EDF-REQ-0061 | [PLANNED MODULE] IaC definitions + drift detector | Environment, IaC | — | — | — |
| EDF-REQ-0062 | [PLANNED MODULE] Artifact registry + release manifest | Artifact, Release | — | — | — |
| EDF-REQ-0063 | [PLANNED MODULE] Blue/green + canary controller | Environment | — | — | — |
| EDF-REQ-0064 | [PLANNED MODULE] Rollback controller | Release | — | — | — |
| EDF-REQ-0065 | [PLANNED MODULE] Edition-release process | Edition, Release | — | — | — |
| EDF-REQ-0066 | [PLANNED MODULE] Incident-response toolkit | Incident, Alert | — | on-call | — |
| EDF-REQ-0067 | [PLANNED MODULE] Sustainment dashboard | Incident, Defect | — | ops | — |
| EDF-REQ-0068 | [PLANNED MODULE] Handover-evidence service | HandoverRecord | — | — | — |
| EDF-REQ-0069 | [PLANNED MODULE] (satisfied by acquire orchestrator automation) | — | — | — | — |
| EDF-REQ-0070 | [PLANNED MODULE] LLM-cost monitor | CostMetric | — | ops | — |
| EDF-REQ-0071 | [PLANNED MODULE] EVM/SPI-CPI dashboard | EVM | — | PM | — |
| EDF-REQ-0072 | [PLANNED MODULE] NCERT back-fill (via acquire) | Asset | — | — | — |
| EDF-REQ-0073 | [PLANNED MODULE] GSEB back-fill (via navigator) | Asset | — | — | — |
| EDF-REQ-0074 | [PLANNED MODULE] Science-count reconciliation | Chapter | — | — | — |
| EDF-REQ-0075 | [PLANNED MODULE] NCERT-code verifier | Asset.code | — | — | — |
| EDF-REQ-0076 | [PLANNED MODULE] Repo cleanup script | (meta) | — | — | — |
| EDF-REQ-0077 | [PLANNED MODULE] Validation-gate assertions | TestResult | — | — | — |

---
