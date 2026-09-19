# tests/omnistudio/ -- OmniScript + FlexCard example suites

Two example suites ported 2026-09-18/19 from the agentic-crt-orchestrator repo's live OmniStudio
work, both against org **fsc7f** (Financial Services Cloud trial, `${client_idFSC}` /
`${usernameFSC}` / `${private_keyFSC}`). **health90 is not used here: it has zero OmniStudio hosts,
measured 4 separate ways** (`docs/recorder/evidence/industry-omni-families-2026-09-07.md`, sections
1a and 5, in the source repo) -- there is nothing OmniScript- or FlexCard-shaped on that org to
drive.

coverage-target: none. Both suites are **structural examples**, not proven-live-through-this-repo
suites -- every citation inside them points at the session that drove the underlying
`keywords_omni.py` callable directly (via `tools/interop/up.py --op kw` or a session script in the
source repo), never at a run of these exact `.robot` files. See the port report for the structural
(parse + import-closure) check that WAS run.

## `fsc7f-digital-lending-omniscript.robot`

**Target:** the OmniScript `DigitalLendingDF/ApplicantIntakeSecured` (OmniProcessId
`0jNhk0000001ltpEAA`, v2), launched at `/lightning/n/GarzAI_Omni_Launcher`.

**Step list** (one test case, `Drive Digital Lending Applicant Intake OmniScript`):

| # | Step | Keyword | Proof on THIS script/org |
|---|---|---|---|
| 1 | auth | `JwtAuthenticate` / `JwtLogin` | -- |
| 2 | navigate | `GoTo .../lightning/n/GarzAI_Omni_Launcher` | lands on Personal Information |
| 3 | Personal Information: Date Of Birth | `Omni Date FSC_DL_v1_Date_Of_Birth 1990-04-17` | VERIFIED-PASS, fsc7f, 2026-09-07 |
| 4 | advance | `Omni Next Step` | VERIFIED-PASS (progress-percent fallback oracle) |
| 5 | Loan Details: Start Date | `Omni Date FSC_DL_v1_Start_Date 2020-01-01` | VERIFIED-PASS (same-month regression case) |
| 6-7 | advance x2 (Loan Asset Information not driven) | `Omni Next Step` | progress-percent oracle only |
| 8 | advance (Address Information not driven) | `Omni Next Step` | progress-percent oracle only |
| 9 | Employment Information: add a row | `Omni Edit Block Add Row EmploymentBlock` | CAUGHT-BUG then VERIFIED-PASS same session (5->6) |
| 10 | Employment Information: Employment Start Date | `Omni Date FSC_DL_v1_Employment_Start_Date 2015-06-01` | VERIFIED-PASS |
| 11 | advance | `Omni Next Step` | progress-percent oracle |
| 12 | Income Information | `Omni Radio FSC_DL_v1_Additional_Income No` | VERIFIED-PASS |
| 13 | advance | `Omni Next Step` | progress-percent oracle |
| 14 | Expense Information | `Omni Radio FSC_DL_v1_Additional_Expense No` | VERIFIED-PASS |
| 15 | advance | `Omni Next Step` | progress-percent oracle |
| 16 | Automatic Payments | `Omni Checkbox FSC_DL_v1_Auto_Pay_Enrollment ${TRUE}` | VERIFIED-PASS |
| 17-18 | advance x2 (Additional Applicants not driven) | `Omni Next Step` | progress-percent oracle |
| 19 | Asset Declaration | `Omni Radio FSC_DL_v1_Add_Assets Yes` | VERIFIED-PASS |
| 20 | Asset Declaration | `Omni Checkbox FSC_DL_v1_Does_Lien_Exist ${FALSE}` | VERIFIED-PASS |
| 21 | Asset Declaration: PrimaryOwner lookup | `Omni Lookup PrimaryOwner GZREF` (commented out) | COULD-NOT-CHECK -- typing/keyup proven, server listbox returned 0 options after 1.5s (a data/timing gap in this script's Party-creation sequence, not a keyword defect) |

Progress read back 0% -> 64.28% across 9 real `Omni Next Step` calls in the cited session
(`docs/recorder/sessions/fsc7f/omni-date-calendar-fix-2026-09-07.json`,
`task_4_omni_next_step_oracle_fix`); this suite's step order matches that session's stated step
order (Personal Information -> Loan Details -> Loan Asset Information -> Address Information ->
Employment Information -> Income Information -> Expense Information -> Automatic Payments ->
Additional Applicants -> Asset Declaration). `Omni Multiselect` and `Omni Typeahead` are
deliberately NOT exercised against this script: a SOQL census of its own `OmniProcessElement` rows
found no Multi-select element in its metadata at all, and no Type Ahead Block element was reached
live this session (both cited inline in the suite).

## `fsc7f-digital-lending-flexcards.robot`

**Two test cases, two separate FlexCard surfaces:**

### `Drive Digital Lending Loan Calculator FlexCard`

**Target:** the Digital Lending Home-page loan-calculator FlexCard, `/lightning/app/06mhk000000z9rhAAA`
(settles to `/lightning/page/home`).

| Step | Keyword | Proof |
|---|---|---|
| Repayment Type (Select) | `Omni Select Repayment Type Amortization` | VERIFIED-PASS, fsc7f, 2026-09-06, held after 4 further calls |
| Loan Amount (Currency) | `Omni Type Loan Amount 250000 family=omni-currency` | VERIFIED-PASS (`$250,000.00` reformat is correct, not a bug) |
| LoanTermSelection (Radio) | `Omni Radio LoanTermSelection Years` | VERIFIED-PASS (only anchor reaching this group at all) |
| Interest Rate (Number) | `Omni Type Interest Rate 7.5 family=omni-number` | VERIFIED-PASS |
| Loan Term (Select) | commented out | **CAUGHT-BUG**: reads correctly immediately, empty on a later sweep after the radio group above changes -- a sibling-field reset, not a resolver defect |
| Start Date (Date) | commented out | **CAUGHT-BUG**: reads correctly immediately, ALL 7 date inputs on this card read empty after 4 more calls / re-renders -- a real limitation of this specific card's persistence, not of the keyword |

### `Drive Application Form Product FlexCard Outputs And Actions`

**Target:** `/lightning/app/06mhk000000z9rhAAA/r/ApplicationFormProduct/13Zhk0000001KxZEAU/view`
(5 FlexCards: applicant detail/profile, offer detail, seller item, loan documents; 12 flex-actions).

| Step | Keyword | Proof |
|---|---|---|
| `First Name` | `Omni Read Output` -> `'Jane'` | VERIFIED-PASS, fsc7f, 2026-09-07, 7/7 steps |
| `Phone` | `Omni Read Output` -> `'(867) 542-3435'` | VERIFIED-PASS |
| `Birth Date` | `Omni Read Output` -> `'7/1/1993'` | VERIFIED-PASS |
| `lastname` (norm-matched) | `Omni Read Output` -> `'Smith'` | VERIFIED-PASS |
| `First Name` == `Jane` | `Omni Verify Output Field` | VERIFIED-PASS |
| `First Name` == `Wrong` | `Omni Verify Output Field` | raises `SilentWrongValue` -- **the guard seen firing** |
| `Application Form` (a caption host) | `Omni Read Output` | raises `OmniElementNotFound` (does not return the caption's own text) |
| `NoSuchFieldW9` | `Omni Read Output` | raises `OmniElementNotFound` |
| `NoSuchActionW9` | `Omni Click Action` | raises `OmniElementNotFound`, lists the 6 real labels offered + names the 4 decoy hosts excluded |
| `partyprofilevalue` | `Omni Click Action` (commented out) | **COULD-NOT-CHECK**: host resolved, click fired (full pointer sequence, retried), neither URL nor visible-modal count moved within 8s |

## Activation / compile trap (skill `sf-omnistudio-runtime`, agentic-crt-orchestrator repo)

Neither example above exercises a fresh deploy -- both target scripts/cards that were already
active and compiled in their cited sessions. If you point either suite at a FRESHLY
deployed/activated OmniScript or FlexCard, two things the skill measured will bite:

- **Activating an OmniScript IS the Designer's compile step, not the `IsActive` flag.** A bare
  `sf data update record ... IsActive=true` does NOT recompile the `OmniProcessCompilation` rows the
  runtime actually reads -- the launcher keeps rendering "is not active" even with `IsActive=true`
  and SOQL-confirmed. The real activation is the Designer's `buildJson {scriptState: 'compile'}`
  Aura call, which `tools/qforce-lite/omni_activate.py --apply` drives for you (source repo). Any
  verdict read within ~60s of a compile is COULD-NOT-CHECK, not a fail -- the render lags the
  compile by up to ~75s.
- **A FlexCard's generated LWC module rebuilds 20-40s after any `OmniUiCard` write.** A capture
  taken immediately after a deploy reads the PREVIOUS generation; `Failed to get generated module
  ... get(String) is null` is a stale-cache/null-key symptom, not necessarily a broken card. Wait,
  then re-capture, before concluding a card is broken.

Query `OmniProcessCompilation.LastModifiedDate` against the `OmniProcess` edit timestamp as the
cheap offline oracle for "did this script actually recompile" before trusting either suite's
navigation step to land on a working page.

## Test-file porting note

The source inventory (`docs/audit/non-qforce-keywords-inventory-2026-09-18.md` section 2) suggested
porting `test_keywords_omni_date_fix.py`, `test_keywords_omni_output_action.py` and
`test_keywords_omni_flexcard.py` as offline pytest structural tests "if CRTPagePatterns runs
pytest; otherwise as documentation of what was proven where." This repo has no pytest
infrastructure (no `conftest.py`, no `pytest.ini`, no `requirements.txt`) and every other ported
Python file here (`garzai_recorder_override.py`) ships without a companion pytest suite -- so this
port follows the "documentation" branch: what those three test files proved is cited inline, by
exact evidence-file path, throughout `resources/garzai_omni.robot` and the two suites above, rather
than copying pytest files with no runner to execute them.
