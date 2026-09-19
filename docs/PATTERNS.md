# Locator patterns behind the CRT suites in this repo

Generated 2026-09-18, companion to `docs/SUITES.md`. Every pattern here is either an entry in the
orchestrator repo's `docs/recorder/patterns/library.json` (cited by its exact `id`) or a mechanism
described in a suite's own comments / the coordinator's additions. Every claim about a recipe cites
its `library.json` entry name; every claim about a live verdict cites a review row number
(`docs/recorder/review/slockard-zoo-nightmare-inputs/review.json`) or an evidence part
(`docs/recorder/evidence/crt-live-testing-recorder-network-2026-09-18.md`, parts 6–9). These are all
read-only citations into the orchestrator repo — nothing there was modified.

## How a pattern gets picked: verdict-led, not preference-led

`tools/recorder/review_table.py`'s export and the recorder-override composer both choose between a
control's **keyword form** (label-addressed: `ClickText`, `TypeText`, `DropDown`, …) and its
**xpath form** (structure-addressed: `ClickElement xpath=...`) by the **live verdict measured on that
exact control**, never by a stylistic preference:

- **VERIFIED-PASS live → keyword form.** The label call resolved the right node and the read-back
  matched.
- **COULD-NOT-CHECK or CAUGHT-BUG on the keyword form, VERIFIED-PASS on the xpath form → xpath
  form.** The label call either never reached the control or landed on the wrong one; the structural
  xpath is the one proven to work.
- **No visible label at all → xpath form only**, by construction (there is nothing for a label call
  to address).

Part 9 of the evidence doc (`docs/recorder/evidence/crt-live-testing-recorder-network-2026-09-18.md`)
quotes the resulting numbers on the Zoo Nightmare Inputs page: **9 of 20 recorder-composed lines
passed live vs. 16 of 16 GarzAI review-composed lines**, same session, same values — the review's
lines are verdict-led (keyword form where VERIFIED-PASS, xpath form otherwise); the CRT cloud
recorder's own lines are neither (it never re-probes what it emits — part 5: *"No recorded line was
executed... The line is never proven to resolve at record time"*). The three review rows that were
`COULD-NOT-CHECK` on the keyword form (71, 72, 74 — see `tests/zoo-composed-lines.robot` Test Case 2)
are the concrete case: each shipped in xpath form until probed live and promotable to label form.

Cited row-by-row (review.json, `slockard-zoo-nightmare-inputs`, 84 rows probed 2026-09-11):

| Row | Label | Keyword-form verdict | Xpath-form verdict | Form shipped in the suites |
|---|---|---|---|---|
| 42 | Contract Term | CAUGHT-BUG | VERIFIED-PASS | xpath |
| 43 | Renewal Notice (days) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 44 | Amount (member 1) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 45 | Amount (member 2) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 46 | Amount (member 3) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 52 | Billable to customer (member 1) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 65 | Add Line (member 1) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 70 | Territory (native select) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 71 | Territory (member 2, combobox) | COULD-NOT-CHECK | VERIFIED-PASS | xpath (probe pending promotion) |
| 72 | Coverage Owner | COULD-NOT-CHECK | VERIFIED-PASS | xpath (probe pending promotion) |
| 73 | Product Lines Covered | CAUGHT-BUG | VERIFIED-PASS | xpath |
| 74 | Support Tier | COULD-NOT-CHECK | VERIFIED-PASS | xpath (probe pending promotion) |
| 75 | Escalation Regions (native select) | VERIFIED-PASS | VERIFIED-PASS | keyword |
| 77 | Entitled Services (dual listbox) | VERIFIED-PASS | VERIFIED-PASS | keyword |

Evidence part 6's table (same rows, its own numbering) corroborates this exactly, plus the finding
that the *recorder's* absolute xpaths (part 6/7) fail portability across sessions entirely — a
different failure mode from ours, since ours never emits an absolute path (see "The label is what a
person sees", CLAUDE.md locator doctrine).

---

## Patterns actually used by the suites in this repo

### `clarity-lookup` — search-as-you-type lookup (`cds-select-input`): type, pick the option inside the host, read back the pill
**Platform:** copado-devops. **Used in:** `tests/dreamforce-2026/03_data360.robot` (the metadata-type
filter), `tests/copado-cicd-pages/02_commit-experience.robot` (Last modified by, All metadata types,
Metadata API name, Search, Source, Select a date).
**Keyword form:**
```
TypeText    {label}    {value}    timeout=40
ClickItem    {value}    tag=div
VerifyElement    xpath=//cds-select-input[@id="{host_id}"]//span[normalize-space(.)="{value}"]    timeout=20
```
**Xpath form:** identical shape with the first line's locator as
`xpath=//cds-select-input[@id="{host_id}"]//input[@role="searchbox"]`.
**Read-back:** the selected-value pill `span.csi__single-value-label` under the host — the
searchbox's placeholder disappears on pick, so a placeholder-based `VerifyInputValue` cannot be the
check.
**Wait:** a dependent lookup stays `aria-disabled` until its parent is picked and its own choices
load (13.0 s measured); the keyword's own timeout is the wait, never a sleep.
**Known failure:** `ClickText {value}` resolves the same text anywhere on the page (the templates
table behind the modal had 23 instances of "Account"); `anchor=<label>` fails when the label text is
also a table header; the option must be qualified first (e.g. a credential's own validated-status
field), never clicked on bare text alone.
**In these suites specifically:** `02_commit-experience.robot`'s "fill" section (rows for Last
modified by / All metadata types) hits `# COULD-NOT-RENDER clarity-lookup: no 'host_id' for this
row` — the recipe's 3rd line (the scoped `VerifyElement`) needs a `host_id` pattern arg the capture
did not carry for those two rows, so only the first two lines (type + pick) render.
**Evidence:** `docs/recorder/evidence/joint-validation-data-template-2026-09-10.md` (rows 75, 77).

### `native-select-dropdown` — a native `<select>`: `DropDown` by label, `VerifySelectedOption`
**Platform:** salesforce-lightning. **Used in:** `slockard-zoo-nightmare-inputs.robot` and
`zoo-composed-lines.robot` (Territory, Escalation Regions — review rows 70, 75), `slockard-zoo-forms-advanced.robot`
(Country, State render as a combobox trigger instead — see `pill-combobox-click-then-text` there).
**Keyword form:** `DropDown    {label}    {value}` / `VerifySelectedOption    {label}    {value}`.
**Xpath form:** `DropDown    xpath={xpath}    {value}` / same verify.
**Read-back:** the select's `selectedOptions` text.
**Known failure:** `PickList` (the Lightning-combobox keyword) does **not** select a native
`<select>` — measured 2026-09-10; `DropDown` by label works even when the label is a cousin element,
not a `<label for=…>`.
**Evidence:** `docs/recorder/evidence/joint-validation-nightmare-inputs-2026-09-10.md`.
**Landed mid-task, 2026-09-18 (`docs/recorder/patterns/library.json` changed on disk while this doc
was being written):** this was the recipe where the anchor gap was actually found — a `<select>`
whose label repeats (`group_size > 1`) used to emit `DropDown {label} {value}` with **no** anchor at
all, silently landing on the wrong member. The library's `{anchor_kw}` placeholder now renders
`    anchor=<n>` whenever the row's `group_size > 1` and nothing when it occurs once
(`pattern_library.recipe()`, via `disambiguation_args.to_call_kwargs` — the same converter this
document's `repeated-label-member` pattern already uses everywhere else); every other `{label}`- or
`{label_base}`-addressed recipe in this library (`clarity-lookup`, `adjacent-span-label-button`,
`count-suffixed-button`, `tab-with-count-in-same-node`) was audited and given the same slot in the
same pass. A recipe that locates by an attribute or an xpath instead
(`inline-edit-pencil`, `slotted-text-button-by-value`, `dueling-list-hand-built`,
`pill-combobox-click-then-text`) or a fixed literal (`lightning-modal-cancel-and-close`) is out of
scope for this slot — its locator never resolved by the row's own label text in the first place, so
there was nothing to silently miss.

### `pill-combobox-click-then-text` — a combobox whose label QWeb cannot reach: click the selector box by xpath, then `ClickText` the option
**Platform:** salesforce-lightning. **Used in:** `slockard-zoo-nightmare-inputs.robot` /
`zoo-composed-lines.robot` (Product Lines Covered → row 73, Support Tier → row 74),
`slockard-zoo-forms-advanced.robot`'s xpath form (Industry, Country, State comboboxes).
**Keyword/xpath form (identical):**
```
ClickElement    xpath={xpath}
ClickText    {value}
VerifyText    {value}    timeout=5
```
**Read-back:** the option text visible after the pick (a pill, or the input's own value).
**Known failure:** `ClickText <label>` only clicks the trigger's own label text, never opens the list
(user, 2026-09-10) — the click **must** target the input/trigger by xpath first; a "list opened"
check that just counts always-visible options is vacuous.
**Caveat measured live (evidence part 7):** on Product Lines Covered, `ClickText Revenue Cloud`
clicked an option that was **already selected** from an earlier run in the same session — a
multi-select pick needs a read-back of the selected pills to be fully honest, and the exported form
for this control does not carry one yet. Recorded as a recipe gap, not fixed here.
**Evidence:** `docs/recorder/evidence/joint-validation-nightmare-inputs-2026-09-10.md` (Product Lines
Covered, Support Tier); part 7 of the 2026-09-18 network evidence for the caveat.

### `dueling-list-hand-built` — an SLDS dueling list without `lightning-dual-listbox`: `ClickText` the option, click the move-right control, verify it under Selected
**Platform:** salesforce-lightning. **Used in:** `slockard-zoo-nightmare-inputs.robot` /
`zoo-composed-lines.robot` (Entitled Services, review row 77).
**Keyword/xpath form (identical):**
```
ClickText    {value}    partial_match=False
ClickElement    xpath=//*[normalize-space(text())="{label}"]/following::*[contains(@class,"zn-arrow-r")][1]
VerifyText    {value}    anchor=Selected
```
**Read-back:** the option text under the Selected column.
**Known failure:** the move control's class (`zn-arrow-r`) is this page's own, not an SLDS standard
— a real `lightning-dual-listbox` takes the QForce `MultiPickList` keyword instead, a completely
different call shape. `status: verified-on-one-page` in the library — do not assume the class name
generalises to another org's custom dual-listbox.
**How the recorder failed at this control (evidence part 8):** the move arrow is a textless element;
the CRT cloud recorder's rule table has no branch for a textless clickable, so its `recordStep` is
never reached and nothing is emitted for it at all. GarzAI's override adds its own capture-phase
click listener that posts a synthetic event for exactly this case, matched to this recipe's own
`ClickElement` step by DOM identity (evidence part 8's table, "the dual-listbox move arrow… recorded
nothing" → part 9 "the move arrow recorded" after the fix).
**Evidence:** `docs/recorder/evidence/joint-validation-nightmare-inputs-2026-09-10.md` (Entitled
Services); network evidence parts 8–9 for the recorder gap and its fix.

### `repeated-label-member` — a control whose label repeats on the page: the member's index as QWeb's numeric anchor
**Platform:** salesforce-lightning. **Used pervasively** — every FSC/HC suite in `docs/SUITES.md`
sections 5–6 (Edit `anchor=1`, Related `anchor=1`, Activity `anchor=1`, Preview `anchor=N`, …), the
copado-cicd-pages bucket rows (`Preview anchor=10`, `Sprint`/`Project`/… buckets), and the Zoo pages
(Amount `anchor=1/2/3`, Add Line `anchor=1/2`, Start Date/End Date `anchor=1`).
**Keyword form:** `TypeText {label} {value} anchor={index}` / `VerifyInputValue {label} {value}
anchor={index}`. For a click target the same idea applies with `ClickText`/`ClickItem`, though the
library's formal entry only names the `input_field` family.
**Xpath form:** `TypeText xpath={xpath} {value}` / matching verify — no anchor argument, since the
xpath already pins the exact node.
**Read-back:** `VerifyInputValue` with the same anchor.
**Known failure, cited exactly:** a member QWeb cannot see (a wizard step not yet rendered, or — as
measured on `hc-new-contact-standard.robot`, review row context — a member the label-resolver simply
never reaches) makes `anchor=2` land on member 1, raising `QWebInstanceDoesNotExistError: Found 1
elements. Given anchor was 2`; this exact error appears commented-out **six times** across
`hc-new-contact-standard.robot` (Phone, Mobile, Email, Reports To, Address Search #2, Other Country)
— every one of those rows falls back silently to the xpath form
(`//label[normalize-space(.)="{label}"]/following::input[1]`), which is why the "Keyword form" test
case in that suite has 6 fewer executable lines than its own candidate count.
**Evidence:** `docs/recorder/evidence/joint-validation-phase1-2026-09-10.md` (Deal Name ×3).

### `inline-edit-pencil` — a record page's inline-edit pencil: `ClickItem` by its title
**Platform:** salesforce-lightning. **Used pervasively** in every FSC/HC suite's `Edit <field>` rows
(Edit Name, Edit Title, Edit Description, Edit Phone, Edit Fax, Edit Category, Edit Type, …) and the
copado-cicd-pages bucket `b18`/`b2` (Edit Credential, Edit Environment, Edit Title, Edit Status, …).
**Keyword form:** `ClickItem    {attr_title}    tag=button` (the value literally IS the button's
`title` attribute — `Edit Description`, not a generic "Edit").
**Xpath form:** `ClickElement    xpath=//button[@title="{attr_title}"]`.
**Read-back:** the field's own input appears (`VerifyInputElement <field label>`).
**Known failure:** the pencil carries no visible text at all — `ClickText` finds nothing; it only
resolves through its `title` attribute, which is why every one of these rows is a `ClickItem` with
`tag=button`, never a plain `ClickText`.
**Evidence:** `docs/recorder/evidence/joint-validation-account-record-2026-09-10.md` (55 buttons, all
resolved).

### `slotted-text-button-by-value` — a button whose visible text arrives through a `<slot>` and repeats on the page: `ClickItem` by its `value` attribute
**Platform:** salesforce-lightning. **Used in every FSC/HC suite's activity-panel rows**: `ClickItem
NewTask tag=button`, `ClickItem NewEvent tag=button`, `ClickItem LogACall tag=button`, `ClickItem
SendEmail tag=button` — and `slockard-account-record.robot`'s `ClickItem NewTask tag=button` (library
evidence names this exact control, "New Task").
**Keyword form:** `ClickItem    {attr_value}    tag=button` (the value passed is the element's own
`value` attribute — `NewTask`, `NewEvent`, `LogACall`, `SendEmail` — not the rendered label "New
Task"/"New Event"/"Log a Call"/"Email").
**Xpath form:** `ClickElement    xpath=//button[@value="{attr_value}"]`.
**Read-back:** the action's panel opens (`VerifyText <panel heading>`).
**Known failure, cited exactly:** "ClickText index 1 and 2 both landed on the other 'New Task' (the
text is slotted)" — the visible text lives in a `<slot>` child, so QWeb's text resolver cannot
distinguish two same-labelled activity buttons by text at all; the `value` attribute is the only
stable handle.
**Evidence:** `docs/recorder/evidence/joint-validation-account-record-2026-09-10.md` (New Task).

### `clarity-grid-row-checkbox` — a Clarity data-grid row checkbox (`cds-checkbox` host carries the `aria-label`, the input does not)
**Platform:** copado-devops. **Used in:** `tests/copado-cicd-pages/00_transitions.robot` (Select row
Flow:Opportunity_Creation_Automation) and `02_commit-experience.robot` (Select all rows, Select row
×3, bucket `b2`).
**Keyword form:** **none exists** — `ClickCheckbox {aria_label}` found nothing live in 15 s,
recorded as-is in the library (`"# no keyword reaches this control..."`).
**Xpath form (the only working form):**
`ClickElement    xpath=//cds-checkbox[@aria-label="{aria_label}"]//input    timeout=15`.
**Read-back:** the input's `is_selected()` flips true; on the Commit Experience, ticking a row
auto-fires Dependency Analysis ("Analyzing dependencies" → enabled) — that state change is itself
confirmation the click registered, beyond `is_selected()`.
**Known failure:** the `aria-label` sits on the `<cds-checkbox>` custom-element host; QWeb's checkbox
locator reads the `<input>` and its `<label>`, neither of which carries the text — `00_transitions.robot`
documents this exact CAUGHT-BUG on its commented-out `ClickCheckbox` line before the corrected xpath
form two lines later.
**Held on:** `na.devops.copado.com|/en/commit/{id}`.

### `clarity-grid-action-cell` — a Clarity data-grid action cell (`cds-table-cell role=button` holding only an icon, e.g. Compare)
**Platform:** copado-devops. **Used in:** `00_transitions.robot` and
`tests/dreamforce-2026/01_standard_user_story.robot` (the Compare-row click).
**Keyword form:** **none** — the cell has no text, only a `cds-icon` svg; `ClickItem` needs an
attribute value the icon does not carry.
**Xpath form (the only working form):**
`ClickElement    xpath=//cds-table-row[.//span[normalize-space()="{row_text}"]]//cds-table-cell[@role="button"]    timeout=15`.
**Read-back:** the panel it opens (a spinner, then the diagram 8–12 s later, 0.5 s when cached).
**Wait:** poll for the panel heading, then for its Changes strip before clicking anything inside it —
`01_standard_user_story.robot`'s own comment documents exactly this: `Explain Changes` clicked before
the diagram finished rendering never opened its panel (`00_transitions.robot`'s commented-out step,
verdict COULD-NOT-CHECK).
**Known failure:** while the grid's search box highlights a match, the row text is split by a
`<mark>` element — a bare `contains()` on `<mark>` only matches the highlighted fragment;
`normalize-space()` on the whole `<span>` still matches the full text (which is why
`01_standard_user_story.robot`'s xpath uses `.//mark[contains(.,'Opportunity_Creation')]` as a
qualifier alongside the full-span match, not `<mark>`'s own text as the target).
**Held on:** `na.devops.copado.com|/en/commit/{id}`.

### `count-suffixed-button` — a button whose label carries a live count in parentheses (or a bare trailing number): click by the label without the count, partial match ON
**Platform:** any. **Used in:** `01_standard_user_story.robot`/`02_agentforce.robot` (`Dependency
Analysis`, `Get Previously Commited (9)`), `02_commit-experience.robot` (bucket `b0`'s counted
members), `03_revenue-cloud-settings-modal.robot` (`User Story Metadata (3)`).
**Keyword form:** `ClickText    {label_base}    timeout=15` (no `partial_match=False` — the count is
part of what changes, so the click must tolerate it).
**Xpath form:** `ClickElement    xpath=//button[starts-with(normalize-space(),"{label_base}")]    timeout=15`.
**Read-back:** the label itself — it reads "Dependency Analysis" before the analysis runs and
"Dependency Analysis (2)" after; the count IS the state to check.
**Known failure, cited exactly and reproduced in this repo:** `partial_match=False` on the counted
form fails the moment the count changes. `02_agentforce.robot` gets this right for `Get Previously
Commited` (explicit comment: *"button text includes a live count... do not use partial_match=False
here"*) but then clicks `Dependency Analysis` with `partial_match=False` two lines later — the same
control that `01_standard_user_story.robot` clicks correctly (bare, no `partial_match`), and that
`00_transitions.robot`'s driven session shows growing a count after the click. **This is an internal
inconsistency across two Dreamforce suites on the same button**, worth fixing before Tuesday: either
`02_agentforce.robot`'s exact-match Dependency Analysis click is wrong, or the count genuinely never
appears on that story's version of the button before the click (unverified either way in this repo).
**Evidence:** the store's match rule (`pom/match.py`) drops the count when matching, so the stored
element survives the relabel; `na.devops.copado.com|/en/commit/{id}`.

### `clarity-offcanvas-close` — the close X of a Clarity offcanvas panel (`aria-label="Close diff"`): native click is intercepted by the fixed header — click through JavaScript
**Platform:** copado-devops. **Used in:** `00_transitions.robot` (closing the Flow compare panel).
**Keyword form:** **none** — `ClickItem {aria_label}` is intercepted:
`element click intercepted ... <header class=global-topbar> would receive the click`.
**Xpath form (the only working form, and it is not an xpath at all):**
`ExecuteJavascript    document.querySelector('button[aria-label="{aria_label}"]').click()`.
`00_transitions.robot` instead ships `ClickElement //button[@aria-label='Close diff']` and marks it
`VERIFIED-PASS` — i.e. the suite's own driven session resolved this one natively, without needing the
JS-click escape hatch the library records as the fallback. Both are valid; the library's JS form is
the fallback for when the native click IS intercepted, not the default.
**Read-back:** the panel heading is gone from the DOM (a 250 ms poll on its absence).
**Held on:** `na.devops.copado.com|/en/commit/{id}`.

### `lightning-modal-cancel-and-close` — the X of a Lightning quick-action modal: its title is "Cancel and close", never "Close"
**Platform:** salesforce-lightning. **Used in:** `04_revenue_management.robot` (row 9, `ClickText
Cancel and close`), `00_transitions.robot` (row 33, xpath form), `03_revenue-cloud-settings-modal.robot`
(row 134, member of bucket `b3`).
**Keyword form:** `ClickText    Cancel and close    timeout=10`.
**Xpath form:** `ClickElement    xpath=//button[contains(@class,"slds-modal__close")]    timeout=10`.
**Read-back:** the modal title is gone and the URL returns from `/lightning/action/quick/...` to the
record (the quick action is its own page key while open — see `03_revenue-cloud-settings-modal.robot`'s
background-page note in SUITES.md).
**Known failure, cited exactly:** `//button[@title="Close"]` resolves a **different** button (a toast
or banner dismiss) and the modal stays open — measured 2026-09-15 on this exact modal on cicd-demo.
`04_revenue_management.robot`'s own comment credits this to "the user's own correction 2026-09-15."
**Held on:** `cicd-demo|/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration`.

### `tab-with-count-in-same-node` — a tab or pill whose count sits in the same text node as its label ("Standard Rules 2"): verify with partial match, never exact
**Platform:** salesforce-lightning. **Used in:** `04_revenue_management.robot` (rows 6–8, correct),
`00_transitions.robot` (rows 28–32, both the CAUGHT-BUG exact-match commented lines and the corrected
`partial_match=True` lines), `03_revenue-cloud-settings-modal.robot` (rows 135–137, **NOT corrected —
see caveat below**).
**Keyword form:** `VerifyText    {label_base}    partial_match=True    timeout=10` /
`ClickText    {label_base}    timeout=10`.
**Xpath form:** `ClickElement    xpath=//*[self::button or self::a][starts-with(normalize-space(),"{label_base}")]    timeout=10`.
**Read-back:** the tab's `aria-selected` flips; the count is the number of rows under it.
**Known failure, cited exactly:** `VerifyText {label_base}` exact resolves and the read-back guard
refuses it as `SilentWrongValue` ("asked for Standard Rules but resolved Standard Rules\n2") —
loosening the guard is explicitly named as the wrong fix; `partial_match=True` is "the honest form."
**Live caveat in this repo (not in the library, found while writing this doc):**
`03_revenue-cloud-settings-modal.robot` rows 135–137 (`VerifyText Standard Rules/Advanced
Rules/Automations partial_match=False`) were generated by `review_table.py` **before** this fix
landed and were never re-probed — they ship the exact-match form the library and `00_transitions.robot`
both document as broken. Treat those three rows as unreliable until re-exported.
**Held on:** `cicd-demo|/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration`.

### `save-never-live` — Save / Submit / Delete: exported as a comment, run by the user after checking the form
**Platform:** any. **Status:** `policy`, not a live-measured recipe. **Used in:** every suite with a
mutating control — `slockard-zoo-forms-advanced.robot` (Save Account), `slockard-zoo-nightmare-inputs.robot`
(Save ×2, Save & New), `hc-new-contact-standard.robot` (Save, Save & New), `fsc-financial-account.robot`
(Delete), `hc-appointment-console.robot` (Delete), `hc-provider-contract.robot` (Delete),
`hc-um-case.robot` (Delete).
**Keyword form:** `# ClickText    {label}    partial_match=False` (commented out in every generated
suite).
**Xpath form:** `# ClickElement    xpath={xpath}` (also commented out).
**Read-back:** SOQL, after the user's own click — never automated.
**Known failure, cited exactly (CLAUDE.md D13):** `ClickText Save` without `partial_match=False`
clicks "Save & New" instead.
**Exception in this repo:** `zoo-composed-lines.robot` Test Case 1 (`Replay The 29 Composed Lines`)
runs `ClickText Save anchor=1` / `Save anchor=2` / `Save & New partial_match=False` **live, not
commented out** — this is deliberate: the suite's own Documentation states read-only intent ("the
page is the Zoo demo LWC; Save is the page's own button") and the point of that suite is proving the
composer reproduces the CRT recorder's editor pane verbatim, including a Save the user chose to
record. It is the one place in this repo where `save-never-live` is knowingly overridden by an
explicit, documented exception — not a suite that forgot the policy.
**Evidence:** CLAUDE.md D13.

### `adjacent-span-label-button` — a button whose visible label is two adjacent spans: the parser joins them with a space the DOM does not have
**Platform:** copado-devops. **Status:** `measured-failure-only` — **not used by any suite in this
repo** (its one cited page, `cicd-demo-data-template-detail`, is not among `tests/`'s captures).
Included here only because it is in `library.json` and the task asked for the rest of the library in
a shorter appendix (see below); no suite in this repo instantiates it.

---

## Clearing a text field before typing

**Landed mid-task** (a parallel stream, per two coordinator corrections): `resources/garzai_typetext_override.robot`
and `tests/zoo-text-clearing.robot`. The mechanism is **not** a new keyword name — it is an
**override** of `TypeText` itself. The resource file defines a user keyword literally named
`TypeText`, and Robot Framework gives a resource-defined keyword precedence over a library keyword of
the same name with no ambiguity error (unlike two *libraries* both publishing `TypeText`, which
raises `Multiple keywords with name 'TypeText' found`) — so **importing the resource silently changes
what every bare `TypeText` call in the whole suite does; no call site changes.** Every call to the
real keyword inside the override file is fully qualified `QForce.TypeText` (only QForce is
`Library`-imported by `resources/common.robot`), both to resolve unambiguously and so the override
doesn't recurse into itself. Commenting the `Resource` line back out restores stock QForce/QWeb
`TypeText` for the whole file. Two more explicit-level keywords live in the same file for a caller
that wants to pick a level by name rather than by import: `Type Text Select All` (the `clear_key`
mechanics alone, no read-back) and `Verify Input Value` (the lenient read-back alone). Composed lines
(from `zoo-composed-lines.robot` / `zoo-recorder-override.robot`) and hand-written suite lines both
stay plain `TypeText` either way — **the import decides the behaviour, not the call site.**

**Why this exists — three levels, measured, not theoretical:**

1. **Plain QWeb `TypeText`** does not reliably clear a pre-populated Lightning input before typing.
   Three real, separately-dated bugs (cited in the override file's own Documentation):
   - **2026-07-29**, New Opportunity form (`tools/qforce-lite/qforce_lite.py`, `type_text_clearing`
     docstring, orchestrator repo, read-only): a time-picker combobox concatenated `"12:00 PM"` +
     `"9:00 AM"` → `"12:00 PM9:00 AM"`; a percent-formatted numeric field grew across repeated
     attempts, `"25%"` → `"2,025%"` → `"202,525%"`, **even with** `clear_key={CONTROL + a}` applied
     (real QWeb's own documented fix) — the synthetic Ctrl+A-then-type chord did not clear, so each
     retry's keystrokes landed on top of the last.
   - **2026-08-26** (`python3 tools/errors/lookup.py "type_text_clearing appends"`, orchestrator
     repo): a second, subtler bug — the repair pass's own verification re-resolved the caller's
     original **label** (e.g. `"Phone"`) with QWeb's generic text resolver, which returns the field's
     `<label>` node, not an element with a `.value` attribute; `get_attribute("value")` came back
     `None`, and the guard's own `actual is not None` check silently skipped the repair it promised.
     Reproduced against a real Contact's pre-populated Phone field:
     `TypeText("Phone", "R20probe")` produced `(415) 555-1212R20probe` uncaught.
   - **2026-09-10** (`docs/errors/entries/576d7e8859.json`, slockard `Zoo_Forms_Advanced`, a macOS
     holder): **neither** `{CONTROL + a}` **nor** the macOS `{COMMAND + a}` variant cleared a
     reactive Lightning input at all — typing `"GZREV Phone"` into a field already holding
     `"GZREV Phone"` read back `"GZREV PhoneGZREV Phone"`, a plain append (not a formatting-driven
     growth like case 1). This is the gap the user named directly: *"this is clearly an area CRT
     missed."*
2. **The override's own repair ladder**, in order: clear (`clear_key={CONTROL + a}`, merged in unless
   the caller already passed one) → type → read back (`GetInputValue`, routed through
   `Read Input Value Or Blank` so a resolution failure reads as blank rather than raising) → lenient
   match. **Only on a blank read-back**: repair 1 is the macOS `{COMMAND + a}` variant tried as its
   **own independent attempt** (never chained onto the failed `{CONTROL + a}` chord — error ledger
   576d7e8859 measured both failing *together* on a macOS holder, so chaining them would not help);
   if still blank, repair 2 is the proven raw mechanism from `qforce_lite.type_text_clearing`
   (`PressKey {CONTROL + a}` → `PressKey {BACKSPACE}` → a plain retype with no `clear_key` chord at
   all). A repair pass that still reads blank afterward is a loud `Fail` (COULD-NOT-CHECK, not a
   silent pass).
3. **The project's D13 decision** (CLAUDE.md), enforced verbatim in the override's `Values Match`
   keyword: repair runs **only on a blank read-back**; a **non-blank mismatch fails loudly, naming
   expected vs. actual, and is never re-typed** — this is *why* the `25% → 2,025% → 202,525%` growth
   is a fixable-by-not-retrying bug, not a fixable-by-retrying one (retrying on a non-blank mismatch
   is exactly how each retyped attempt landed on top of the last). `Values Match` trims both sides,
   and if **both**, once trimmed, look like a number (`[\s0-9,.$%+-]+` — digits, separators, currency
   and percent marks only) it compares **digits only**, so a numeric field's own re-render
   (`'25000'` read back as `'25,000.00'`) still passes; otherwise it's plain trimmed-string equality.
   It never rescues a blank `actual` — a blank routes to the repair ladder above instead.

**`tests/zoo-text-clearing.robot` — the four test cases, all on `/lightning/n/Zoo_Nightmare_Inputs`,
org slockard, `${client_idSlock}` triple:**

| Test case | What it proves | Field(s) (review.json row) | Pattern |
|---|---|---|---|
| `Baseline -- Stock TypeText Appends On Renewal Notice (days)` | the documented failure, reproduced deliberately, via the **fully-qualified** `QForce.TypeText` (bypasses the override on purpose so the "no override" case is visible without a second file/run) | Renewal Notice (days), row 43 (no sibling, group_size null — the plainest repro: one field, one label, two writes) | plain QForce native, override bypassed |
| `With The Override -- TypeText Clears First On Renewal Notice (days)` | the *same* field, same two values (90 then 24), through the bare `TypeText` that now resolves to the override | Renewal Notice (days), row 43 | **TypeText override** (clear→type→read-back→lenient-match) |
| `With The Override -- Amount anchor=1..3` | the override composed with `repeated-label-member`: a `FOR ${idx} IN RANGE 1 4` loop, baseline-then-retype through the override, once per anchor | Amount, rows 44–46 (group_size 3) | **TypeText override** + **repeated-label-member** |
| `Type Text Select All -- The clear_key Mechanics Alone, No Read-Back` | the lighter level composed explicitly: `Type Text Select All` (clear_key only) then a separate `Verify Input Value` call, so the two halves are visibly independent | Approved Budget, rows 47–48 (group_size 2, anchor=1 exercised) | **Type Text Select All** + **Verify Input Value** (composed, not the full override) |

Every test authenticates (`JwtAuthenticate`/`JwtLogin`, `${client_idSlock}` triple), navigates
(`GetInstanceUrl` + `GoTo .../Zoo_Nightmare_Inputs`, `VerifyText Nightmare timeout=30`), then runs its
proof; verification throughout is the override's own lenient read-back (`Log To Console` prints the
actual value read for a human to eyeball against the expected concatenation-vs-clean-value shape —
this suite is itself the demonstration, so nothing is asserted with a hard `Should Be Equal` beyond
what the override/composed keywords already fail loudly on).

**When a suite picks each level:**
- A suite driving a page known to have reactive/pre-populated Lightning inputs (the Zoo Nightmare
  Inputs page named throughout this document — Amount, Approved Budget, Contract Term, the date
  range) should `Resource    ../resources/garzai_typetext_override.robot` so every `TypeText` call
  gets the clear+read-back behaviour without touching a single call site.
- A suite on a plain, non-reactive form (most of the FSC/HC record-detail pages in this document,
  which mostly `ClickItem Edit <field>` into a fresh, empty inline-edit input) has no reason to import
  it — stock `TypeText` is sufficient there, and importing it everywhere by default would mask a
  genuinely-broken locator behind a repair pass that only exists for the clearing failure mode.
- `Type Text Select All` alone (no read-back) is for a caller that wants the `clear_key` behaviour but
  intends to verify some other way (e.g. a follow-up `VerifyField` against SOQL, per this project's
  "the read-back never mutates its target" rule).
- `Verify Input Value` alone is for a caller that typed with plain `TypeText` (or some other method)
  and only wants the read-back half.

**Known gap, evidence part 7 (`crt-live-testing-recorder-network-2026-09-18.md`):** the CRT-recorder
composer's exported lines are plain `TypeText`, which relies on QWeb's own documented clear-before-type
— the same clearing this whole section exists because of. Stage A's fields were pre-filled (36, 90,
148,500.00) and whether the typed values replaced or appended was never read back — disclosed as
COULD-NOT-CHECK in that evidence. The fix belongs in the export path: emit the override-resource
import (or an explicit `Clear` step) for any input the review measured as prefilled — not yet wired
into `export_flow.py` or `review_table.py`, even though the override itself has now landed.

---

## OmniStudio (OmniScript + FlexCard) locator patterns

**Landed 2026-09-18/19** (port stream): `resources/garzai_omni.robot` + `resources/garzai_omni/` +
`tests/omnistudio/`. Not in `library.json` — OmniStudio elements live inside
`runtime_omnistudio_*` LWC shadow roots this document's other patterns never reach at all (the
`patterns actually used` section above is entirely QWeb/QForce label-proximity resolution over
regular Lightning DOM; OmniStudio needs its own host anchor because it is not addressable that
way). Full keyword-by-keyword citations: `resources/garzai_omni.robot`'s own `[Documentation]`
blocks and `tests/omnistudio/README.md`.

**The anchor, not a label.** Every keyword resolves a control via `__host(key)` trying, in order:
`[data-omni-key="<key>"]` (OmniScript — equals `OmniProcessElement.Name`, an author-controlled
metadata id present on 23/23 elements measured on dev1), `[data-element-label="<norm(key)>"]`
(FlexCard — the Designer's own Element Label, lowercased/despaced, on the
`runtime_omnistudio_flexcards-*` wrapper one level above the actual input), then `aria-label` or
`placeholder` on the leaf control (FlexCard last resort). **Never a page-wide text search** — a
page-wide option scan was measured once clicking "Agentforce" in the Lightning nav bar and
reporting a pass; every keyword here is host-scoped first, and reads its own write back through
`confirm.py` before returning.

**Two mechanics a generic `ClickText`/`TypeText`/native-value-write cannot do:**
- **Selecting an OmniStudio combobox option needs the full pointer sequence**
  (`mouseover`→`mousedown`→`mouseup`→`click`) dispatched on the deepest node whose text matches,
  scoped to the combobox's OWN listbox via `aria-controls` — a bare `.click()` on the option leaves
  the field EMPTY, measured twice independently (dev1 and fsc7f).
- **The OmniStudio/SLDS Date control only commits through its own calendar widget** — a plain
  native-value write into the visible text input reads back the just-written string in the SAME
  call (self-referential, vacuous) but a genuine second read comes back empty. `Omni Date` drives
  the widget itself: open picker → select year from its own `<select>` → click prevMonth/nextMonth
  until the header shows the target month (polling the RENDERED day-cell year, not the `<select>`'s
  own synchronous `.value` — a same-month edge case was measured stale otherwise) → click the day
  cell whose `aria-label` matches `Date().toDateString()`.

**A sibling control can reset a field you already set, on a FlexCard.** Measured live on the fsc7f
Digital Lending loan-calculator card: a Select value read back correctly immediately after the
call, then read back EMPTY after a SIBLING radio group changed — the card's own reactive logic, not
a resolver defect. General form of this codebase's "a picklist can overwrite a field you already
typed" pattern, here triggered by a different control entirely. `Omni Type`/`Omni Select`/etc. do
not defend against this (they cannot know the card's own dependency graph); an example suite that
needs a value to SURVIVE should set the dependent field LAST and re-verify.

**Two DOM families need two different Omni keyword groups, not one.** `omni-output`
(`runtime_omnistudio_common-output-field`, 217 hosts measured, ZERO carrying any of the three
anchors above — only a generated `data-style-id`) and `omni-action`
(`runtime_omnistudio_flexcards-flex-action`, real clickable node inside its own shadow root) are
each their own family with their own locator, entirely separate from the input-control anchor
above:
- `Omni Read Output`/`Omni Verify Output Field` resolve an output field by its RENDERED LABEL
  (there is no key attribute at all) and refuse a caption-only host structurally — a caption host
  has no label/value pair, so a reader that fell back to "first span in the host" would return the
  caption text itself (this project's six-times bug, `get_field_value("Stage") -> "Stage"`, in its
  purest form). An empty `.field-value` on a LABELLED host is COULD-NOT-CHECK, never `''` — 29 of
  217 measured hosts render exactly that shape.
- `Omni Click Action` refuses `runtime_omnistudio_common-action` BY NAME — 58 measured hosts, every
  one attribute-free, wrapping an empty `<slot name="action">` with nothing assigned. Accepting one
  would report a successful click on a node that cannot be clicked (the `ClickItem`-without-`tag=`
  failure shape, generalised). The read-back requires the URL to change OR the count of VISIBLE,
  content-bearing modals to rise — a raw `querySelectorAll` modal count is not an oracle by itself,
  because one action host pre-renders an empty modal, so the count is already ≥1 before any click.

**Wiring: `Evaluate __import__('keywords_omni').<fn>(...)`, not a native `Library` import of that
file.** `resources/garzai_omni.robot` Library-imports `keywords_omni.py` itself (`WITH NAME
OmniRaw`) purely for the `sys.path` side effect that lets the `Evaluate __import__` calls resolve
the module — the same two-mechanism split the source template uses (see
`docs/audit/non-qforce-keywords-inventory-2026-09-18.md` section 2). `WITH NAME` keeps the
auto-generated per-function library keywords out of the unqualified namespace so they cannot
collide with the hand-written keywords of the same name in this file.

---

## Appendix — the rest of `library.json`, not used by any suite in this repo

All 15 entries in `docs/recorder/patterns/library.json` are covered above **except one**, listed here
for completeness since the task asked for the whole library in a shorter form:

- **`adjacent-span-label-button`** (copado-devops) — see its own short section above; no suite in
  `tests/` touches the Data Template detail page it was measured on.

Every other entry in the library — `clarity-lookup`, `native-select-dropdown`,
`pill-combobox-click-then-text`, `dueling-list-hand-built`, `inline-edit-pencil`,
`slotted-text-button-by-value`, `clarity-grid-row-checkbox`, `clarity-grid-action-cell`,
`count-suffixed-button`, `clarity-offcanvas-close`, `lightning-modal-cancel-and-close`,
`tab-with-count-in-same-node`, `repeated-label-member`, `save-never-live` — is instantiated by at
least one suite in this repo and is documented in full above.
