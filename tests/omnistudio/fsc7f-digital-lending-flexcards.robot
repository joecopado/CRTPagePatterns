*** Settings ***
Documentation     EXAMPLE (2026-09-18/19): drive two OmniStudio FlexCard surfaces in the fsc7f Digital
...               Lending app through the FlexCard-anchored Omni keywords (data-element-label /
...               aria-label / placeholder -- FlexCard elements carry NO data-omni-key at all, measured
...               0/1 on this exact card, docs/recorder/evidence/omni-fsc7f-2026-09-06.json).
...
...               TWO SEPARATE TEST CASES, two separate surfaces:
...               1. the Digital Lending Home-page loan-calculator FlexCard (Select/Currency/Number/
...                  Radio/Date SET keywords)
...               2. the ApplicationFormProduct record page's FlexCards (Read Output / Verify Output
...                  Field / Click Action -- a different DOM family, output fields and actions, not
...                  inputs)
...
...               WHY fsc7f, not health90: health90 has ZERO OmniStudio hosts, measured 4 separate ways
...               (docs/recorder/evidence/industry-omni-families-2026-09-07.md section 1a/5) -- there is
...               nothing FlexCard-shaped to drive there.
...
...               ACTIVATION / COMPILE TRAP (skill sf-omnistudio-runtime): a FlexCard's generated module
...               rebuilds 20-40s after a metadata write, and "Failed to get generated module ...
...               get(String) is null" is a stale-cache symptom, not a broken card -- re-open the page
...               (or wait) before assuming a card is broken. Neither card driven below was freshly
...               deployed in the cited sessions (both were already compiled), so this trap was not
...               itself exercised here; carried forward as a standing caution per the skill.
...
...               coverage-target: none -- structural example only (see the port report). No step below
...               has been driven live THROUGH this suite; every citation is to the session that drove
...               the underlying keyword directly, and two real CAUGHT-BUGs are preserved as comments
...               rather than asserted as passes.
Resource          ../../resources/common.robot
Resource          ../../resources/garzai_omni.robot
Suite Setup       Setup Browser
Suite Teardown    End suite

*** Test Cases ***
Drive Digital Lending Loan Calculator FlexCard
    # FSC (fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    ${instance}=    GetInstanceUrl
    # This app id resolves (settles) to /lightning/page/home once inside it -- docs/recorder/
    # evidence/omni-fsc7f-flexcard-2026-09-06.json's own "surface" line says so explicitly. Do NOT
    # assert on the app-id fragment surviving in the landed URL (it will not); the read-back below
    # is the card's own rendered content, which is the real proof the right page loaded.
    GoTo    ${instance}/lightning/app/06mhk000000z9rhAAA
    VerifyText    Repayment Type    timeout=30

    # Repayment Type (Select). PROOF: fsc7f, this card, 2026-09-06, VERIFIED-PASS -- asked
    # "Amortization", read back "Amortization" immediately AND after 4 further keyword calls on the
    # same card (proves the resolver keeps finding the same host across repeated calls, not just on
    # first touch). Resolved via anchor #3: aria-label="Repayment Type" on the leaf
    # input[role=combobox] (this card has no data-element-label on this particular control).
    Omni Select    Repayment Type    Amortization

    # Loan Amount (Currency). PROOF: fsc7f, this card, 2026-09-06, VERIFIED-PASS -- asked 250000,
    # committed "$250,000.00" (the runtime reformatting on blur is correct behaviour, not a bug --
    # Omni Type's family-aware read-back normalises both sides before comparing). Resolved via
    # data-element-label="loanamount".
    Omni Type    Loan Amount    250000    family=omni-currency

    # LoanTermSelection (Radio). PROOF: fsc7f, this card, 2026-09-06, VERIFIED-PASS -- asked "Years",
    # read back "Years". data-element-label="loantermselection" is the ONLY anchor that reaches this
    # group at all -- its own <fieldset> carries no aria-label and no legend text.
    Omni Radio    LoanTermSelection    Years

    # Interest Rate (Number). PROOF: fsc7f, this card, 2026-09-06, VERIFIED-PASS -- asked 7.5, read
    # back 7.5, value held. Resolved via data-element-label on the wrapper with a placeholder-anchored
    # leaf lookup inside.
    Omni Type    Interest Rate    7.5    family=omni-number

    # Loan Term (Select) -- KNOWN LIMITATION, NOT asserted as a passing SET here. CAUGHT-BUG, fsc7f,
    # this card, 2026-09-06: asked "30", read back "30" IMMEDIATELY after the call (the resolver and
    # the select-commit both worked), but on a LATER sweep -- after the LoanTermSelection radio group
    # above was changed to "Years" -- Loan Term read back EMPTY. This looks like the card's own
    # reactive logic resetting a dependent field when a sibling control changes (the qforce-lite
    # doctrine's "a picklist can overwrite a field you already typed" pattern, here triggered by a
    # SIBLING radio group instead of the same field). Not a resolver defect; recorded here as a
    # comment rather than a live call so this suite does not assert a value the evidence shows does
    # not survive the very next radio change:
    # Omni Select    Loan Term    30    # do this LAST if you need it, or re-set it after Omni Radio

    # Start Date (Date) -- KNOWN LIMITATION, NOT asserted here either. CAUGHT-BUG, fsc7f, this card,
    # 2026-09-06: Omni Date correctly found the leaf input (anchor #3, aria-label="Start Date
    # (yyyy-MM-dd)") and committed a value that read back correctly AT THE TIME of the call --
    # but on a later sweep (after 4 more keyword calls / re-renders on other fields), ALL 7
    # date-picker inputs on this card read back empty, confirmed by a direct eval. This FlexCard's
    # date-picker component appears to only persist a value chosen through its own calendar widget
    # long-term; Omni Date already drives that exact widget (see resources/garzai_omni.robot), so the
    # mechanism is correct -- the finding is that repeated re-renders on THIS card can still blank it,
    # a real, reproducible limitation of this specific card, not of the keyword:
    # Omni Date    Start Date (yyyy-MM-dd)    2026-10-01    # verify immediately if you rely on this

    # Negative case, PROVEN live on fsc7f, this card, 2026-09-06, PASS-GUARDED: a key that resolves
    # nowhere raises OmniElementNotFound cleanly rather than silently returning None.
    # Omni Type    Not A Real Element    x    # raises OmniElementNotFound as designed

    # No Save button exists on this card -- it only computes client-side (no DML in the cited
    # session; none performed here either).


Drive Application Form Product FlexCard Outputs And Actions
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    ${instance}=    GetInstanceUrl
    # URL-first, the exact app-scoped record URL from the evidence file (5 FlexCards: applicant
    # detail/profile, offer detail, seller item, loan documents; 12 flex-actions).
    GoTo    ${instance}/lightning/app/06mhk000000z9rhAAA/r/ApplicationFormProduct/13Zhk0000001KxZEAU/view
    VerifyText    First Name    timeout=30

    # --- Omni Read Output (the OUTPUT-field family: runtime_omnistudio_common-output-field, no
    #     data-omni-key / data-element-label at all -- the rendered LABEL is the only handle) -------
    # PROOF: fsc7f, this exact page, 2026-09-07, VERIFIED-PASS, 7/7 steps as designed
    # (docs/recorder/evidence/industry-omni-families-2026-09-07.md section 2a).
    ${first}=    Omni Read Output    First Name
    Should Be Equal    ${first}    Jane
    ${phone}=    Omni Read Output    Phone
    Should Be Equal    ${phone}    (867) 542-3435
    ${dob}=    Omni Read Output    Birth Date
    Should Be Equal    ${dob}    7/1/1993
    # norm-matched: the metadata-style key "lastname" resolves the same host as the rendered label
    # "Last Name" -- __norm() lowercases and strips non-alphanumerics on both sides before comparing.
    ${last}=    Omni Read Output    lastname
    Should Be Equal    ${last}    Smith

    # --- Omni Verify Output Field (the assert half) -----------------------------------------------
    Omni Verify Output Field    First Name    Jane
    # The guard SEEN FIRING, not merely claimed -- PROOF: fsc7f, same page/session, raised
    # `SilentWrongValue: typed 'Wrong' into First Name (omni-output) -- field holds 'Jane'.`
    ${wrong_ok}=    Run Keyword And Expect Error    SilentWrongValue: *
    ...    Omni Verify Output Field    First Name    Wrong
    Log    guard fired as proven: ${wrong_ok}    console=True

    # Caption-only host (no label/value pair, not a readable output) correctly raises rather than
    # returning its own rendered text -- PROOF: fsc7f, same page/session.
    Run Keyword And Expect Error    OmniElementNotFound: *    Omni Read Output    Application Form
    Run Keyword And Expect Error    OmniElementNotFound: *    Omni Read Output    NoSuchFieldW9

    # --- Omni Click Action (runtime_omnistudio_flexcards-flex-action; runtime_omnistudio_common-
    #     action, 58 measured hosts on the committed captures, is a decoy REFUSED BY NAME) -----------
    # Host resolution + decoy refusal PROOF: fsc7f, same page/session, VERIFIED-PASS -- a nonexistent
    # key correctly raised, naming the 6 real actions offered and the 4 decoy hosts excluded.
    Run Keyword And Expect Error    OmniElementNotFound: *    Omni Click Action    NoSuchActionW9

    # LANDING is COULD-NOT-CHECK for this specific action -- NOT asserted as a pass here. PROOF:
    # fsc7f, same page/session: the host and its a.slds-action_item resolved and were clicked (full
    # pointer sequence, retried), but neither the URL nor the visible-modal count moved within 8s.
    # The keyword correctly refuses to report a pass rather than guess whether the action is a
    # genuine no-op on this card -- left as a comment so this suite does not assert a landing that
    # was never actually observed:
    # ${result}=    Omni Click Action    partyprofilevalue    # raises CouldNotCheck -- see above
    # Other real actions on this page, NOT individually landing-tested this session either
    # (inventory only, from the same evidence file): appformvalue (AF-00000006), emailvalue
    # (janesmith93@gmail.com), contactvalue, accountvalue, editaction (the BUTTON-shaped action, two
    # shadow roots deep -- the second clickable shape this keyword resolves).
