# Demo quick hits, 2026-10-08 -- evidence for tests/demo-quick-hits.robot

What ran, where, and what that does and does not prove. Every PROVEN line in the suite points here or at a file in the
orchestrator repo that already existed.

## How the cases were run locally

`local_run.py` (this folder) brings up a headless browser on its own slot for ONE org (slockard or healthcloud, both `full` on the
orchestrator's allowlist), then runs the named test cases of `tests/demo-quick-hits.robot` with Robot Framework inside that
browser process, against real QWeb 3.8.3 (the orchestrator's `.venv-qweb`). Nothing is saved: every form is Cancelled or left
open and the browser is taken down at the end. `parse_out.py` reads the Robot `output.xml`.

Assumptions of this rung, stated once:

* The browser is already logged in, so `JwtAuthenticate` / `JwtLogin` are no-ops here. The credential's own proof is separate:
  `crt-jwt-setup local --verify-only` for healthcloud, VERIFIED-PASS 2026-10-08.
* `QForce.TypeText` is QWeb's own `type_text` (the same assumption as the orchestrator's `override_proof.py`).
* `ComboBox` and `PickList` are the orchestrator's hardened versions (`qforce_lite.combo_box` / `pick_list`), NOT the licensed
  QForce ones, which cannot run on this Mac. So any local pass of a `ComboBox` / `PickList` line says our keyword works; it says
  nothing about CRT's.
* `UseModal` sets QWeb's `ActiveAreaXpath`. The local Chrome renders native shadow DOM; CRT's cloud Chrome is where the stock recorder
  wrote its absolute paths. An xpath that does not resolve here may resolve there, and the other way round.

## Results of the final run (2026-10-08, both orgs, one run each)

| case | org | result locally | what that means |
|---|---|---|---|
| 01 Lookup, stock lines | slockard | FAIL at `ClickElement <absolute path>` (case-01-stock-abs-xpath-not-found-locally.png) | the stock path does not resolve in this Chrome; the stock lines are unproven as a replay |
| 02 Lookup, our label line | slockard | PASS: `ComboBox Account Name Edge Communications`, then `VerifyInputValue` read back "Edge Communications" (slockard-lookup.png) | our keyword works on the label; a stock QWeb read-back reads the picked record |
| 03 Lookup, our label line | healthcloud | PASS: `ComboBox Account Name Acme Partners`, `VerifyInputValue` matched (healthcloud-lookup.png) | same on a second org and object |
| 04 Picklist, one line | slockard | PASS: `PickList Stage Prospecting` | |
| 05 Picklist, with backups | slockard | PASS for the line; backups run separately (below) | |
| 06 Aura picklist, stock keyword | slockard | PASS, but with OUR `pick_list` standing in for CRT's `PickList` | proves nothing about CRT's PickList; the twin itself is real (capture + screenshot slockard-aura-status.png) |
| 07 Aura PickList, ours | slockard | PASS: `Aura PickList Status Working New`, all three QWeb lines | real QWeb |
| 08 override line, one line | slockard | `ClickText Status New partial_match=False` did NOT resolve ("Unable to find element for locator Status New"); the case is wrapped and stays green | the override's own line for this control does not run here |
| 09 override line with backup | slockard | line failed, xpath backup resolved, `ClickText Working` and `VerifyText Working anchor=Status` passed | the backup heals the line |
| 10 Test Agent lines | slockard | PASS: `Gz Read Page` (2 pages), `Gz Show Amount`, `TypeText Amount 25000 anchor=3` (our TypeText emptied the filled `136,100.00` first), `Gz Verify` VERIFIED-PASS, `Gz Verify ... 99999 on_mismatch=warn` passed the step | the prompts themselves were not typed to the live agent |
| 11 TypeText on a filled field | slockard | the field held 90; stock read back 24 (replaced, in this QWeb); ours emptied 90, typed, read back 24 VERIFIED-PASS | stock appended in Live Testing on 2026-10-06 and replaced in job 205089: it depends on the build |

The row-by-row output of that final run is `local-run-results.txt`. Cases 02-05 were also run before `UseModal On/Off` was
added around the modal steps; the results did not change.

Separate runs (scratch suite, same session and method): `Gz Verify    Account Name    Edge Communications    index=2` after the pick said
`VERIFIED-PASS: reads 'Edge Communications', exactly as expected`; without `index=` it says COULD-NOT-CHECK, because the Opportunity
form has two controls labelled Account Name (the output field and the lookup). The stage backups: each opener followed by `ClickText Prospecting` and a
read-back. Backup `ClickText --None-- anchor=Stage` PASS; backup `ClickText Stage` PASS; backup
`ClickElement xpath=//label[...]/following::*[@role="combobox"][1]` FAIL (no element in this Chrome).

## What the override and the page reader wrote

* `override-replay-excerpts.txt` -- verbatim lines the SHIPPED recorder override (build 2026-09-23n13) composes over two 2026-10-08
  captures of slockard, offline (`replay.py run`): Stage as `PickList Stage <option>` with four dormant backups; the Account Name
  lookup gets no composed line; the Aura Status box becomes `ClickText Status New partial_match=False` with one xpath backup;
  the Aura Contact Name lookup becomes a `TypeText ... gz_family=combobox` pair.
* `gz-read-page-offline.txt` -- the shipped page reader (`Gz Read Page`, `Gz Show`) run offline over the same captures and the
  Zoo Nightmare Inputs capture: `30. Account Name [lookup] ComboBox    Account Name    <record name>` on the Opportunity form;
  `95. Status New [link] ClickText    Status New    partial_match=False` and `Contact Name ... TypeText` on the Aura panel; `Gz Show Amount` names
  the three Amount inputs apart by the anchors List Price, Negotiated Discount and Net to Customer.

## What stock records for a lookup (the user's own sessions, not re-run)

* slockard, 2026-09-18, Live Testing network harvest: `ClickElement /html[1]/body[1]/...` then `QForce.ComboBox    Search Accounts...    Edge Communications`
  (orchestrator `docs/recorder/evidence/crt-live-testing-recorder-network-2026-09-18.md`, Part 11).
* fsc7f, 2026-09-23, stock recorder, Opportunity New: `ClickText *Account Name`, `ClickElement /html[1]/body[1]/... (758 characters)`,
  `ComboBox    Search Accounts...    asdf    index=1`; with the override (build n13) the same two lines came through unchanged
  (orchestrator `docs/recorder/evidence/sessions/2026-09-23-fsc7f-four-pages-{stock,override-n13}-user/`).
* healthcloud: never recorded. The suite's path for Contact New is derived from the live DOM with the recorder's own path rule and is
  marked as derived.

## What is NOT shown by any of this

* Nothing here ran in a CRT build. The licensed QForce `ComboBox` / `PickList` / `UseModal` are untested on these pages.
* The recorder override does not write the label-form lookup line today (measured live in the user's n13 session and by replay).
* Prompts 2 and 4 of case 10 were not typed to the live Test Agent. Prompts 1, 3 and 5 are the user's own 2026-10-06 wording.
* The healthcloud login inside a CRT build with the `*HealthCloud` project variables.
