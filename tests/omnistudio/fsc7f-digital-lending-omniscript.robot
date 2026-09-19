*** Settings ***
Documentation     EXAMPLE (2026-09-18/19): drive the OmniScript `DigitalLendingDF/ApplicantIntakeSecured`
...               (OmniProcessId `0jNhk0000001ltpEAA`, v2) end to end through its own Omni Type/Radio/
...               Checkbox/Date/Edit-Block-Add-Row/Next-Step keywords, org fsc7f.
...
...               WHY THIS PAGE, not a health90 page: health90 has ZERO OmniStudio hosts, measured 4
...               separate ways (docs/recorder/evidence/industry-omni-families-2026-09-07.md section 1a/5)
...               -- there is nothing OmniScript-shaped to drive there. fsc7f's `DigitalLendingDF/
...               ApplicantIntakeSecured` is the SAME script the keyword module's own most extensive live
...               session drove (docs/recorder/sessions/fsc7f/omni-date-calendar-fix-2026-09-07.json,
...               omni-elements-additional-2026-09-07.json) -- 9 consecutive Next clicks, Progress 0% ->
...               64.28%, with real SET+read-back proof at 6 of the 10 steps.
...
...               ACTIVATION / COMPILE TRAP (skill sf-omnistudio-runtime, tests/omnistudio/README.md):
...               activating an OmniScript IS the compile step, and the generated runtime module rebuilds
...               20-40s AFTER a metadata write -- the first capture/drive right after an activation reads
...               stale. This script was already active and compiled before the cited session ran; a fresh
...               org that just deployed/activated this script needs that wait BEFORE step 1 below, or
...               every keyword here will resolve against a not-yet-regenerated page.
...
...               SEED-DATA TRAP (same evidence file, task_2_seed_data): this exact script previously
...               failed to advance past Loan Details with "We couldn't find the product(s)..." because an
...               OmniProcessElement 'Set Values' element hard-coded a Product2 Id from a DIFFERENT org
...               (prefix 01tWs, not fsc7f's 01thk) -- a stale cross-org metadata reference, not a missing
...               seed record. Already repaired on fsc7f at the OmniProcessElement level (see the evidence
...               file for the exact REST PATCH); noted here because the SAME class of trap (a Set Values
...               element pinning another org's record Id) is the first thing to check if this suite's
...               product-fetch step ever raises that message again on a refreshed sandbox.
...
...               coverage-target: none -- structural example only (see the port report). No step below
...               has been driven live THROUGH this suite; every citation is to the session that drove the
...               underlying keyword directly. Read every inline `#` comment before assuming a step is
...               proven on THIS script -- several intentionally are not, and say so.
Resource          ../../resources/common.robot
Resource          ../../resources/garzai_omni.robot
Suite Setup       Setup Browser
Suite Teardown    End suite

*** Test Cases ***
Drive Digital Lending Applicant Intake OmniScript
    # FSC (fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    ${instance}=    GetInstanceUrl
    # URL-first: the launcher is a custom Lightning tab, not a record URL (the script has no record
    # context of its own until Personal Information is saved) -- cited launcher path, evidence file
    # docs/recorder/sessions/fsc7f/omni-date-calendar-fix-2026-09-07.json ("script"."launcher").
    GoTo    ${instance}/lightning/n/GarzAI_Omni_Launcher
    # Lands on the script's first step. VerifyText proves the launcher opened THIS script, not a
    # blank/error page -- the step label itself is the same "Personal Information" the evidence
    # file's step-order list starts with.
    VerifyText    Personal Information    timeout=30

    # --- Personal Information -------------------------------------------------------------------
    # Date Of Birth. PROOF: fsc7f, this exact script, 2026-09-07, VERIFIED-PASS -- asked 1990-04-17,
    # the widget committed 04-17-1990 (a format shift, not a value mismatch; Omni Date normalises
    # both sides before comparing). Step heading inferred from the field-key prefix and the
    # session's stated step order, not independently re-confirmed against a captured page for this
    # port -- the evidence file cites the ORG, SCRIPT and FIELD KEY, not a step-heading screenshot.
    Omni Date    FSC_DL_v1_Date_Of_Birth    1990-04-17
    Omni Next Step
    # Read-back proof for EVERY Next click below is the same shared oracle: this script's own step
    # chart never carries aria-current="step" (chart index stays -1 both before and after a genuine
    # advance -- a permanent false negative for the index-only oracle), so Omni Next Step falls back
    # to comparing the page's own "Progress: N%" text and labels the result oracle=progress-percent
    # rather than silently treating the fallback as the primary read. PROOF: fsc7f, this script,
    # 2026-09-07 -- 9 consecutive clicks, Progress 0 -> 7.14 -> 14.29 -> ... -> 64.29 (%),
    # VERIFIED-PASS every time.

    # --- Loan Details -----------------------------------------------------------------------------
    # Start Date. PROOF: fsc7f, this script, 2026-09-07, VERIFIED-PASS -- asked 2020-01-01, committed
    # 01-01-2020. This is the SAME-MONTH REGRESSION CASE the fix targeted: the target month equalled
    # the already-displayed month, so the month-nav loop never clicked anything and so never waited,
    # which used to expose a stale day grid still showing the prior year -- fixed by polling the
    # rendered day cells' own year instead of trusting the year <select>'s synchronous .value.
    Omni Date    FSC_DL_v1_Start_Date    2020-01-01
    Omni Next Step
    Omni Next Step    # Loan Asset Information -- no keyword proof cited for this step's own controls
    ...                 # in the sessions this suite draws from; advanced through, not driven.

    # --- Address Information ------------------------------------------------------------------------
    Omni Next Step    # no keyword proof cited for this step's own controls; advanced through only.

    # --- Employment Information --------------------------------------------------------------------
    # EmploymentBlock: add one repeatable row and prove the row count rose. PROOF: fsc7f, this
    # script, 2026-09-07 -- CAUGHT-BUG (the original oracle never saw the new sibling block) then
    # VERIFIED-PASS same session after the fix, block count 5 -> 6.
    Omni Edit Block Add Row    EmploymentBlock
    # Employment Start Date -- same citation and same step-heading caveat as Date Of Birth above.
    Omni Date    FSC_DL_v1_Employment_Start_Date    2015-06-01
    Omni Next Step

    # --- Income Information ------------------------------------------------------------------------
    # PROOF: fsc7f, this script, this step, 2026-09-07, VERIFIED-PASS -- asked No, read back No.
    Omni Radio    FSC_DL_v1_Additional_Income    No
    Omni Next Step

    # --- Expense Information -----------------------------------------------------------------------
    # PROOF: fsc7f, this script, this step, 2026-09-07, VERIFIED-PASS -- asked No, read back No.
    Omni Radio    FSC_DL_v1_Additional_Expense    No
    Omni Next Step

    # --- Automatic Payments -------------------------------------------------------------------------
    # PROOF: fsc7f, this script, this step, 2026-09-07, VERIFIED-PASS -- asked ${TRUE}, read back ${TRUE}.
    Omni Checkbox    FSC_DL_v1_Auto_Pay_Enrollment    ${TRUE}
    Omni Next Step
    Omni Next Step    # Additional Applicants -- no keyword proof cited for this step's own controls.

    # --- Asset Declaration --------------------------------------------------------------------------
    # PROOF: fsc7f, this script, this step, 2026-09-07, VERIFIED-PASS -- asked Yes, read back Yes;
    # revealed the Asset/PrimaryOwner/Does_Lien_Exist/AdditionalOwner sub-fields, matching metadata.
    Omni Radio    FSC_DL_v1_Add_Assets    Yes
    # PROOF: fsc7f, this script, this step, 2026-09-07, VERIFIED-PASS -- asked ${FALSE}, read back ${FALSE}.
    Omni Checkbox    FSC_DL_v1_Does_Lien_Exist    ${FALSE}
    # PrimaryOwner Lookup. PROOF: fsc7f, this script, this step, 2026-09-07, COULD-NOT-CHECK -- the
    # TYPE half drove correctly (input wrote and read back "GZREF", a keyup event fired) but the
    # server-backed listbox returned ZERO options after a 1.5s wait: a data/timing gap in this
    # script's own Party-creation sequence at this point in the flow, not a keyword defect (the
    # shared select-commit half IS proven live on fsc7f, via Omni Select on the loan-calculator
    # FlexCard suite -- see fsc7f-digital-lending-flexcards.robot). Left as a comment: calling it
    # live here would either hang on ${choose}=${NONE} (type-only) or raise CouldNotCheck on commit,
    # neither of which this example suite asserts against, per the tri-state rule (a COULD-NOT-CHECK
    # step is reported, never silently retried into a false pass).
    # Omni Lookup    PrimaryOwner    GZREF
    # Progress stopped at 64.28% (Asset Declaration) in the cited session -- steps beyond this one
    # (Soft Credit Pull Disclaimer, Offer Configurator, Disclosures and Consents, Upload Your
    # Documents, Application Summary) were never reached and are not exported here; no new element
    # TYPES are expected there per the script's own metadata census (Custom LWC / Date-Time-Local /
    # Formula -- none of which has a dedicated keyword yet).

    # Multiselect and Typeahead are DELIBERATELY not exercised against this script: a SOQL census of
    # its own OmniProcessElement rows found no Multi-select element anywhere in its metadata, and no
    # Type Ahead Block element was reached live this session (docs/recorder/sessions/fsc7f/
    # omni-elements-additional-2026-09-07.json, catalogue_note). Both keywords are separately proven
    # (dev1) -- see resources/garzai_omni.robot's own citations.
