# Proposal: 1000 ICP-Qualified Companies in One Month
### Sample Submission — Business Analytics Internship, DeepThought

---

## Goal

Build a verified list of 1000 companies that match DeepThought's Federer ICP — Indian specialty manufacturers, Rs.50Cr–Rs.500Cr, promoter-driven, differentiated product, technical decision-maker, active growth signals — within 30 calendar days.

## Key Constraints

- **Quality over volume.** 1000 companies that are genuinely qualified, not 5000 names scraped from a directory. Every company must have evidence-backed scores on all 6 criteria.
- **~30% yield.** From the Part A exercise, roughly 3 in 10 companies investigated will pass. To get 1000 passes, the sourcing universe needs to be ~3500–4000 companies.
- **Tools available:** Claude, Gemini, GitHub Copilot, Antigravity, scraping tools, database subscriptions, API credits.

---

## The Funnel

```
Universe (3500-4000 companies)
    ↓ Hard pre-filters (auto-disqualify)
Screened pool (2000-2500)
    ↓ Automated ICP scoring (6 criteria, AI-assisted)
First-pass qualified (1200-1400)
    ↓ Human QA on borderline + low-confidence scores
Final verified list (1000)
```

---

## Sourcing the Universe (Week 1)

The first week is entirely about building the raw universe of 3500-4000 companies. No scoring yet — just names, websites, cities, and rough segment tags.

### Source 1: DSIR-Recognized R&D Units List
- **What:** Department of Scientific and Industrial Research maintains a public list of companies with recognized in-house R&D units. ~3000+ companies nationally.
- **Why it works for this ICP:** DSIR recognition directly signals C3 (differentiation — R&D investment) and C4 (technical decision-maker — someone had to set up and run the R&D unit). It's a pre-filter for technical seriousness.
- **How to extract:** DSIR list is available as a downloadable PDF/Excel from dsir.gov.in. Parse it, tag by city and industry, filter to manufacturing companies in target segments.
- **Expected yield:** ~800-1000 companies after filtering to target cities and segments.
- **Limitation:** Skews toward older, established companies. Misses newer startups that haven't applied for DSIR yet.

### Source 2: Expo Exhibitor Lists
- **What:** Industry-specific trade expos publish exhibitor directories. Target expos: CPHI India (pharma/chem), BioAsia (biotech, Hyderabad), Aero India (defence), ELECRAMA (electrical), PackEx (packaging machinery), IMTEX (machine tools), Agri Intex (agri-inputs).
- **Why it works:** Exhibitors self-select for growth intent — paying Rs.2-10L for a booth signals C6 (active growth). Expo segments map directly to our industry baskets.
- **How to extract:** Most expos publish exhibitor directories online (some require registration). Scrape exhibitor name + website + segment. For past expos, check archived exhibitor lists on expo websites or in the Wayback Machine.
- **Expected yield:** ~600-800 companies across 6-8 expos after deduplication.
- **Limitation:** Biased toward companies that can afford booths. Misses bootstrapped smaller MSMEs.

### Source 3: BSE SME / NSE Emerge Listed Companies
- **What:** BSE SME platform and NSE Emerge list small-cap companies. Filter by manufacturing sectors.
- **Why it works:** Listed companies have public financials (revenue band immediately available), annual reports (leadership bios, facility details), and regulatory filings (ownership structure visible). This makes scoring faster and more reliable.
- **How to extract:** BSE/NSE provide sector-wise company lists. Filter to: chemicals, pharma (non-generic), engineering, electronics, biotech, medical devices, agri-inputs. Download company master data.
- **Expected yield:** ~400-500 companies in target segments and revenue band.
- **Limitation:** Only captures listed companies. Unlisted private MSMEs — which are the majority of the ICP — won't appear here.

### Source 4: USFDA / EU-GMP / WHO-GMP Approved Facility Lists
- **What:** USFDA publishes a list of approved manufacturing facilities globally. EU-GMP and WHO-GMP prequalification lists are also public.
- **Why it works:** Regulatory approval directly evidences C1 (manufacturer — you can't get USFDA approval without a facility), C3 (differentiation — commodity manufacturers don't pursue international regulatory approval), and C5 (export tailwind).
- **How to extract:** USFDA facility list is searchable at fda.gov. Filter to India, then to target segments. Cross-reference with EU-GMP and WHO lists.
- **Expected yield:** ~300-400 companies after filtering to MSME segment (exclude Cipla, Sun, Dr. Reddy's tier).
- **Limitation:** Heavy pharma/chem bias. Doesn't cover defence, agri, medtech well.

### Source 5: Industry Association Member Directories
- **What:** Associations like IDMA (pharma), BDMA (bulk drugs), CPhI exhibitor network, NASSCOM (IT, but has IoT/medtech sub-groups), ACMA (auto components), ELCINA (electronics), Seed Association of India.
- **Why it works:** Active association membership signals an operating company in the segment. Directories often include company size, product range, and contact info.
- **How to extract:** Some directories are public. Others require registration or a small fee. Scrape or manually extract.
- **Expected yield:** ~500-600 companies across 5-6 associations.
- **Limitation:** Overlaps heavily with DSIR and expo lists. Deduplication is critical.

### Source 6: MCA (Ministry of Corporate Affairs) Filings
- **What:** MCA has public data on all registered Indian companies — including paid-up capital, industry classification (NIC code), director details, and registered address.
- **Why it works:** NIC codes let you filter to specific manufacturing sub-segments. Director details give you the decision-maker's name. Paid-up capital gives a rough size proxy.
- **How to extract:** Use Antigravity or similar tools to query MCA data by NIC code + city + capital range. Alternatively, use third-party MCA data providers (Tofler, Zauba Corp).
- **Expected yield:** ~1000-1500 companies, but many will be dormant, tiny, or non-manufacturing despite NIC code.
- **Limitation:** Very noisy. NIC codes are self-reported and often wrong. Requires heavy filtering. No website data in MCA.

### Source 7: LinkedIn Sales Navigator
- **What:** Search for founders/MDs of manufacturing companies in target cities with technical backgrounds.
- **Why it works:** Inverts the search — instead of finding companies and checking if the DM is technical, find technical DMs and check if their company is a manufacturer. Strong for C4.
- **How to extract:** Sales Navigator filters: Industry (manufacturing sub-sectors), company headcount (50-500), geography (target cities), seniority (owner, CXO, founder). Export to CSV.
- **Expected yield:** ~400-600 profiles, mapping to ~300-400 unique companies.
- **Limitation:** LinkedIn data is self-reported. Company headcount and industry are often wrong for Indian MSMEs.

### Week 1 Output

After deduplication across all 7 sources: **~3500-4000 unique companies** with at minimum company name, city, and rough segment tag. Approximately 60% will have a website URL. The remaining 40% need website discovery (Google search by company name + city).

### Week 1 Tasks
| Day | Task |
|-----|------|
| 1-2 | Download and parse DSIR list, BSE/NSE SME lists, USFDA facility list. These are structured data — fastest to process. |
| 2-3 | Scrape exhibitor directories from 6-8 target expos. Build scraper scripts (Python + BeautifulSoup/Playwright). |
| 3-4 | Extract industry association directories. Query MCA data via Antigravity for target NIC codes + cities. |
| 4-5 | LinkedIn Sales Navigator extraction for target cities and segments. |
| 5-6 | Deduplicate master list. Resolve company names (fuzzy matching — "ABC Pvt Ltd" vs "ABC Private Limited"). |
| 6-7 | Website discovery for companies without URLs. Google search automation: "{company name} {city} site:.com OR site:.in". |

---

## Automated ICP Scoring (Week 2-3)

### The Scraper

For each company with a website, scrape:
- Homepage
- /about, /about-us
- /leadership, /team, /management
- /products, /services
- /news, /media, /press
- /careers, /jobs
- /contact

Concatenate to ~8K tokens max. Use Playwright (handles JavaScript-rendered sites) with a 10-second timeout per page. Respect robots.txt.

**Tech stack:** Python + Playwright for scraping, Claude Haiku for first-pass scoring, Claude Sonnet for borderline re-scoring.

### The Scoring Pipeline

```
For each company:
  1. Scrape website (5-8 pages, ~8K tokens)
  2. Send to Claude Haiku with ICP scoring prompt
  3. Receive JSON: 6 criterion scores + verdict + evidence + confidence flags
  4. If verdict = "pass" and total 40-48 (borderline): re-score with Sonnet
  5. If any criterion has confidence = "low": flag for human QA
  6. Store result in master spreadsheet
```

**Cost estimate:**
- Haiku first pass: ~Rs.0.40/company × 3500 = Rs.1,400
- Sonnet re-score on ~20% borderline: ~Rs.3.50/company × 700 = Rs.2,450
- Scraping compute: negligible on a local machine
- **Total AI cost: ~Rs.4,000** for the full pipeline

**Speed estimate:**
- Scraping: ~30 seconds/company (with politeness delays) = ~30 hours for 3500 companies. Run 4 parallel scrapers = ~8 hours.
- Haiku scoring: ~3 seconds/company = ~3 hours for 3500 companies.
- Sonnet re-scoring: ~5 seconds/company = ~1 hour for 700 companies.
- **Total compute time: ~12 hours** spread across 2-3 days.

### Hard Pre-Filter (Before AI Scoring)

Before sending to the LLM, auto-reject:
- No website found (after Google search attempt)
- Website is a single parked page (check: page count < 2, total text < 500 chars)
- Company name contains "Trading", "Imports", "Distributors" (simple string match)
- Revenue > Rs.500Cr (if known from BSE/NSE data)

This eliminates ~500-800 companies before the AI scoring step, saving cost and time.

### Week 2-3 Tasks
| Day | Task |
|-----|------|
| 8-9 | Build and test scraper on 50 companies. Debug edge cases (JavaScript-heavy sites, redirect chains, rate limiting). |
| 10 | Build scoring pipeline: Haiku prompt, JSON parser, result storage. Test on 15 calibration companies. Tune prompt if <12/15 correct. |
| 11-14 | Run scraper on full universe (3500 companies, 4 parallel workers). |
| 14-17 | Run Haiku scoring on all scraped companies. |
| 17-18 | Run Sonnet re-scoring on borderline cases (40-48 total score). |
| 19 | Compile first-pass results. Expected: ~1200-1400 passes, ~300-400 borderline/low-confidence flagged for QA. |

---

## Human QA (Week 3-4)

AI scoring will produce false positives. The main failure modes:
- **C3 inflation:** LLM reads "ISO 9001" and scores differentiation as moderate, when ISO 9001 is a baseline certification, not a differentiator.
- **C4 false positives:** LLM infers "technical" from any engineering degree, when a B.Tech from a tier-3 college running a commodity business isn't the same as a PhD from IISc running a specialty biotech.
- **C6 false positives:** LLM reads a press page with articles from 2019 and scores growth as moderate, when no activity in 5 years is a red flag.
- **C1 false negatives:** Company website emphasizes "solutions" and "services" language but actually manufactures — LLM takes website language too literally.

### QA Process

1. **Auto-QA (programmatic):**
   - Flag any company where all 6 scores are "high confidence" but total is exactly 40-42. These are likely inflated borderlines.
   - Flag any company where C3 evidence mentions only ISO 9001 / ISO 14001 (baseline, not differentiating).
   - Flag any company where C6 evidence references news older than 2023.

2. **Human QA (manual review):**
   - Review all ~300-400 flagged companies. Estimated: 3-4 minutes per company = ~20 hours.
   - For each: open website, verify 2-3 key claims, adjust scores if needed. Accept, reject, or reclassify.
   - Spot-check 50 random "strong pass" companies (should be fine, but verify).

3. **Final list assembly:**
   - Take all strong_pass (expected ~600-700)
   - Take QA-verified pass (expected ~400-500)
   - Drop all remaining borderline/unverified
   - Target: **1000 verified companies**

### Week 3-4 Tasks
| Day | Task |
|-----|------|
| 19-20 | Run auto-QA flags. Separate flagged vs. clean. |
| 20-24 | Human QA on ~400 flagged companies (2 hours/day × 4 days). |
| 24-25 | Spot-check 50 strong_pass companies. |
| 25-27 | Final assembly: merge clean strong_pass + QA-verified pass. Deduplicate. Verify count ≥ 1000. |
| 27-28 | Add personalization hooks for top 200 (priority outreach tier). |
| 28-29 | Format final deliverable: master CSV with all fields, summary dashboard, methodology doc. |
| 30 | Buffer day for overruns. |

---

## Weekly Summary

| Week | Focus | Output |
|------|-------|--------|
| 1 | Sourcing | 3500-4000 company universe with names, cities, segment tags, websites |
| 2 | Scraping + scoring | All companies scraped and scored by AI. First-pass results: ~1200-1400 passes. |
| 3 | Re-scoring + QA start | Borderline re-scored with Sonnet. Human QA begins on flagged companies. |
| 4 | QA completion + assembly | 1000 verified companies in final CSV. Top 200 with personalization hooks. |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Yield lower than 30% | Expand universe: add 2-3 more expo lists, tap state-level industrial directories (TSIIC, MIDC, GIDC), use Google Maps scraping for industrial areas in target cities. |
| Scraper blocked by websites | Rotate user agents, add delays, use residential proxies for critical sites. Fall back to manual research for high-priority companies that block scraping. |
| AI scoring accuracy < 80% | Retune prompt on calibration set. Split into 2-step scoring: Haiku for C1/C2/C5 (factual, easier), Sonnet for C3/C4/C6 (judgment, harder). |
| QA bottleneck (too many flagged) | Tighten auto-QA rules to reduce human review load. Recruit a second reviewer if needed. |
| Deduplication errors | Use fuzzy matching (Levenshtein distance) + CIN number matching for listed companies. Manual review of top 50 suspected duplicates. |

---

## Tools and Budget

| Tool | Purpose | Cost |
|------|---------|------|
| Claude Haiku API | First-pass ICP scoring (3500 companies) | ~Rs.1,400 |
| Claude Sonnet API | Borderline re-scoring (700 companies) | ~Rs.2,450 |
| Antigravity | MCA data extraction, company discovery | Licence provided |
| Playwright + Python | Website scraping | Free (open source) |
| GitHub Copilot | Code assistance for scraper and pipeline | Licence provided |
| LinkedIn Sales Navigator | DM discovery, company enrichment | Licence provided |
| Google Sheets / PostgreSQL | Master data storage and QA tracking | Free |
| **Total AI + data cost** | | **~Rs.4,000** |

---

## Final Deliverable

1. **Master CSV** — 1000 companies, each with: name, website, city, segment, products, revenue band, decision-maker, C1-C6 scores with evidence, verdict, confidence flags
2. **Priority-200 list** — top 200 companies with personalization hooks ready for outbound
3. **Methodology document** — sources used, scraper architecture, scoring prompt, QA process, yield rates at each stage
4. **Code repository** — all scraping scripts, scoring pipeline, data processing notebooks, reproducible end-to-end
5. **Source breakdown** — which sources contributed how many final companies (to inform future sourcing investment)
