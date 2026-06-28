# Audit Report — Phase 1 Quality Audit

> **Source:** STD9_AI_ACADEMY Phase 1 audit of existing CONTENT files
> **Publisher:** STD9_AI_ACADEMY (internal audit document)
> **Verification Date:** 2025-06-25
> **Verification Status:** Complete — files read, URLs live-checked, curriculum cross-checked
> **Confidence Score:** 74 / 100

---

## 1. Scope of Audit

**Files audited:** 5
1. `CONTENT/SYLLABUS/GSEB_STD9_SYLLABUS.md`
2. `CONTENT/SYLLABUS/SOURCES.md`
3. `CONTENT/NCERT/NCERT_BOOK_CATALOG.md`
4. `CONTENT/GSEB/GSEB_BOOK_CATALOG.md`
5. `CONTENT/INVENTORY.md`

**Verification methods used:**
- Full re-read of every file
- HTTP live-check of every unique URL (30 unique URLs)
- Cross-check of curriculum claims against Tier-1 sources (NCERT rationalised list, NCERT Grade 9 syllabus PDF, CBSE curriculum PDF)
- Download + integrity check of key PDFs

---

## 2. Quantitative Summary

| Metric | Count |
|--------|:-----:|
| Files audited | 5 |
| Unique URLs checked | 30 |
| URLs **Working (200)** | 30 |
| URLs **Redirect** | 0 |
| URLs **Broken** | 0 |
| URLs **Unavailable** | 0 |
| Total factual claims reviewed | ~85 |
| **Verified claims** | ~71 |
| **Unverified / inaccurate claims** | **6** (see §4) |
| Source citations present | Yes (all files cite sources) |
| Duplicate information blocks | 1 (SOURCES.md ↔ file source tables) |

**Overall Confidence Score: 74 / 100**

> Score rationale: Strong source coverage and all URLs healthy, but **6 factual inaccuracies** (most notably the unverified "Maitri" textbook-name claim and the over-stated Beehive chapter list) reduce confidence. The structural/sourcing quality is high; the *content accuracy* on two topics is not yet Tier-1-verified.

---

## 3. URL Verification Results (STEP 8)

All 30 unique URLs were live-checked via HTTP on 2025-06-25.

| Status | Count | Detail |
|--------|:-----:|--------|
| Working (200) | 30 | All reachable |
| Redirect (3xx) | 0 | — |
| Broken (4xx/5xx) | 0 | — |
| Unavailable | 0 | — |

**Known intermittent flakiness (NOT broken):**
- `ncert.nic.in` returns HTTP 000 on ~1 of 3 requests (connection drop / TLS). Always succeeds on retry. This is server-side instability, not a dead link. Affected: textbook.php, Grade 9 syllabus PDF.

**Full per-URL status table:** see `SOURCE_REGISTRY.md` (Verification column).

---

## 4. Unverified / Inaccurate Claims Found (critical)

### 4.1 ❌ "Maitri" textbook name — UNVERIFIED
- **Where:** `GSEB_STD9_SYLLABUS.md` (§1, §6), `GSEB_BOOK_CATALOG.md` (§5, §6)
- **Claim:** A *"Maitri"* textbook series is being introduced for GSEB/NCF Std 9 Maths & Science.
- **Finding:** No official source confirms "Maitri" as an NCERT or GSEB Std 9 textbook name. The search for it returned only unrelated entities (tuition classes, a journalist). NCERT's *reported* (third-party) new Class 9 names are **Ganita Manjari (Maths), Exploration (Science), Kaveri (English), Ganga (Hindi), Sharada (Sanskrit)** — and NCERT's own syllabus PDF states these are **under development** (not yet released).
- **Action:** Remove/qualify all "Maitri" references. Replace with a neutral, accurately-sourced statement about the NCF-SE transition (new editions under development, names not officially confirmed for GSEB adoption).

### 4.2 ❌ Beehive chapter list over-stated — INACCURATE
- **Where:** `NCERT_BOOK_CATALOG.md` §4.1
- **Claim:** Lists "The Snake Trying" (poem 9) and "The Duck and the Kangaroo" (poem 7) as current Beehive content.
- **Finding:** Per NCERT rationalisation (2022-23), **these two poems were DELETED**, along with prose chapters **"Packing"** and **"The Bond of Love"**. The catalog also lists "The Fun They Had" as prose 1 (correct) but should note rationalisation.
- **Action:** Correct the Beehive list to reflect rationalised (current 2025-26) content; mark deleted items explicitly.

### 4.3 ⚠️ Beehive prose count "11" — INACCURATE
- **Where:** `NCERT_BOOK_CATALOG.md` §4.1 header ("11 prose + 9 poems")
- **Finding:** After rationalisation, Beehive retains **fewer** prose chapters (Packing & The Bond of Love removed). The "11 prose" figure predates rationalisation.
- **Action:** Correct to the rationalised count (verify exact number against the official NCERT book).

### 4.4 ⚠️ NCERT textbook codes (iemh1, iesc1, iebe1, iemo1) — UNVERIFIED
- **Where:** `NCERT_BOOK_CATALOG.md` §1, §2, §4.1, §4.2
- **Claim:** Specific textbook codes assigned (e.g. `iemh1` for Maths).
- **Finding:** These codes were inferred from the NCERT URL pattern (`iesc102.pdf` for Science ch. is confirmed real), but the **main-book codes were not directly verified** against the NCERT master list (Tier-1 source #7).
- **Action:** Verify each code against `ncertbooks.ncert.gov.in/static/Textbooks.pdf`; mark as unverified until then.

### 4.5 ⚠️ GSEB chapter lists labeled "indicative" — correctly caveated but UNVERIFIED
- **Where:** `GSEB_STD9_SYLLABUS.md` §4, `GSEB_BOOK_CATALOG.md`
- **Finding:** GSEB chapter/unit lists are explicitly marked "indicative" — this is honest, but the lists were compiled from third-party sources, **not** extracted from the official GSSTB textbook PDFs.
- **Action:** Acceptable for Phase 1, but flag for verification during textbook acquisition (download the actual GSSTB PDFs and extract authoritative ToCs).

### 4.6 ⚠️ NCERT History/Sanskrit/Urdu chapter counts marked "~" or "varies" — UNVERIFIED
- **Where:** `NCERT_BOOK_CATALOG.md` §3 (History "~5"), §6, §7
- **Finding:** Counts shown with `~` are estimates, not verified against the official NCERT books.
- **Action:** Verify during acquisition.

---

## 5. Structural Issues

| Issue | Detail | Severity |
|-------|--------|:--------:|
| **Duplicate source lists** | `SOURCES.md` repeats the per-file source tables already inside the catalog files. | Low (redundancy) |
| **Root `INVENTORY.md` empty** | The root `INVENTORY.md` referenced in the prior task was never created; only `CONTENT/INVENTORY.md` exists (and is a near-empty template). | High |
| **No metadata headers** | Existing files do not carry the required Source/Publisher/Verification Date/Status/Confidence header block. | Medium |
| **No METADATA folder** | (Resolved in this phase — created.) | Resolved |

---

## 6. Coverage Gaps (Missing Resources)

### Missing Subjects / Textbooks
| Gap | Detail |
|-----|--------|
| **NCERT exemplar books** | Class 9 Maths & Science *Exemplar Problems* books not catalogued (important for the AI tutor). |
| **NCERT question banks / model papers** | Not collected. |
| **NCERT lab manuals** | Class 9 Science *Laboratory Manual* not catalogued. |
| **NCERT Class 9 Sanskrit full chapter list** | Only title given; chapters not enumerated. |
| **NCERT Class 9 Urdu chapters** | Titles only; no chapter enumeration. |
| **GSEB per-medium textbook PDFs** | Not downloaded; only catalogued at title level. No Gujarati-medium ToC extracted. |
| **GSEB Std 9 chapter-level lists** | Only "indicative" themes; no authoritative per-subject chapter lists. |
| **GSEB exemplar / model papers** | Not collected. |
| **Class 9 Gujarati (1st lang) chapter list** | Not enumerated. |
| **Class 9 Social Science (NCERT) — Civics/Geo/Eco exact rationalised chapters** | Only indicative lists; deletions not applied. |

### Missing Chapters (vs. latest curriculum) — see CURRICULUM_VALIDATION.md
- Beehive: deleted items still listed (must remove Packing, The Bond of Love, The Duck and the Kangaroo, The Snake Trying).
- Maths/Science chapter lists appear current but need confirmation against the downloaded CBSE/NCERT syllabus PDFs.

---

## 7. Outdated Sources

| Source | Issue |
|--------|-------|
| BYJU'S GSEB SST PDFs (#18, #19) | 2020/2021 scans — pre-rationalisation; edition unverified. |
| BYJU'S GSEB Class 9 Syllabus page (#17) | Page title references "Reduced Syllabus 2020-21". |
| These are fine as *reference* but must not be treated as the current 2025-26 edition. |

---

## 8. Recommendations

1. **Fix the 6 inaccurate/unverified claims now** (§4) — highest priority; they are factual errors in the corpus.
2. **Add the required metadata header** to every content file (Source / Publisher / Verification Date / Status / Confidence).
3. **Verify NCERT textbook codes** against the official master list PDF (Tier-1 #7).
4. **Begin acquisition with Tier-1 sources only** (NCERT portal chapter PDFs + GSSTB portal) — do not ingest third-party scans as primary content.
5. **Catalogue NCERT Exemplars, Lab Manual, and model papers** to complete Class 9 coverage.
6. **Resolve the root `INVENTORY.md`** — create it as the master inventory (currently missing).
7. **De-duplicate** `SOURCES.md` vs. in-file source tables (keep `SOURCE_REGISTRY.md` as the single source of truth, retire `SOURCES.md` duplication).

---

## 9. Audit Sign-off

- **Audited by:** STD9_AI_ACADEMY Phase 1 audit pass
- **Date:** 2025-06-25
- **Confidence Score:** **74 / 100**
- **Status:** Findings actionable; corrections scheduled before any content acquisition.
- **Next gate:** Re-run audit after §4 corrections to target ≥ 90/100.
