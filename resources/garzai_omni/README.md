# resources/garzai_omni/ -- OmniStudio (OmniScript + FlexCard) keywords, ported

Source: `agentic-crt-orchestrator` repo, `tools/qforce-lite/keywords_omni.py` + `tools/qforce-lite/confirm.py`,
per `docs/audit/non-qforce-keywords-inventory-2026-09-18.md` section 2. Both files are copied
**verbatim** (see `MANIFEST.txt` for the sha256 proof) -- nothing in this port edited the Python.

## What is and is not excluded

The inventory's own scope note flags that some ported files "lean on a local-only dependency"
(the org map at `~/.claude/state/org-map/<alias>.json`, or `tools/sf_session.py`) that does not
exist on a CRT VM, and those dependants are supposed to be named here and left out.

**Nothing in this port has that dependency.** Checked directly against both files' import
statements:

- `keywords_omni.py` imports only `time` (stdlib), `confirm` (this directory), and
  `from QWeb.internal import browser as browser_internal` -- wrapped in
  `try/except ImportError` in the source itself specifically so the module imports cleanly with
  no QWeb installed at all (`browser_internal = None`). QWeb is part of the standard CRT library
  set (`common.robot`'s five-library block), so on a real CRT VM this import succeeds and
  `_driver()` resolves the real Selenium browser object QWeb is already driving.
- `confirm.py` imports only `re`, `datetime`, `decimal` (all stdlib).

No org-map read, no `sf_session.py` token mint, no `~/.claude/state/...` path, no CRUD/Tooling
call. This is why the structural import-closure check (see the repo root README / port report)
found nothing to fix or exclude -- the whole surface is pure DOM/JS mechanics plus one shared
verification module.

## The wiring bug found and fixed during this port

`tools/qforce-lite/templates/crt/resources/garzai_recorder.robot` (the source CRT template) wires
nine of its sixteen `Omni *` keywords -- `Omni Type`, `Omni Select`, `Omni Radio`, `Omni
Checkbox`, `Omni Date`, `Omni Lookup`, `Omni Typeahead`, `Omni Edit Block Add Row`, `Omni Next
Step` (lines 264-360 there) -- to `RunKeyword    Omni Verify Output    ${key}    ${value}
${family}`, which resolves to `keywords_omni.verify_omni_value` -- a **READ-and-compare only**
call. None of those nine wrappers, as shipped in the source template, ever calls its own setter
(`omni_type`, `omni_select`, `omni_radio`, ...). A suite author calling `Omni Type` there gets a
keyword that reads the control's CURRENT value and asserts it equals the argument -- it never
types anything. If the field already happened to hold the expected value (e.g. re-running a
suite against a record left in that state by a previous pass), this is a **vacuous green with
the exact shape CLAUDE.md's whole doctrine exists to catch**: a keyword whose name promises a
write and which never performs one, silently.

This is a genuine bug in the shipped template, not a stated design choice -- the four *correctly*
wired `Omni *` keywords in the same file (`Omni Multiselect`, `Omni Read Output`, `Omni Verify
Output Field`, `Omni Click Action`, lines 932-990) all call
`Evaluate    __import__('keywords_omni').<their own function>(...)`, proving the intended
mechanism. `resources/garzai_omni.robot` in this port **corrects the wiring** for all nine so
each keyword calls its own real setter function, and documents the fix in each keyword's own
`[Documentation]` (see that file). The live-proof citations from
`docs/audit/non-qforce-keywords-inventory-2026-09-18.md` are carried over unchanged -- they were
measured directly against the Python callables (via `tools/interop/up.py --op kw` or a session
script), never through the broken Robot wrapper, so the proof itself is unaffected by the wiring
bug; only the shipped Robot keyword was silently non-functional.

## The name collision, resolved

The inventory also names a **naming** collision (distinct from the wiring bug above): the source
template defines two DIFFERENT keywords whose names both read "Omni Verify Output" --
`garzai_recorder.robot:361` (`Omni Verify Output`, wraps `verify_omni_value` -- asserts an
OmniScript INPUT control) and `garzai_recorder.robot:961` (`Omni Verify Output Field`, wraps
`verify_omni_output` -- asserts a FlexCard OUTPUT field). Robot Framework keyword name matching
ignores spaces/case, so these do not collide as RF keyword names, but a reader scanning by eye
can easily mistake one for the other. Per the port brief's own suggested resolution, the older
input-control keyword is renamed in this port:

    Omni Verify Output          (source, garzai_recorder.robot:361, verify_omni_value)
      -> Omni Verify Output Legacy   (this port, resources/garzai_omni.robot)

kept, not dropped -- `verify_omni_value` is a real, independently useful keyword (assert an
OmniScript INPUT control's value, format-aware) and is not superseded by `verify_omni_output`
(which reads an entirely different DOM family, FlexCard OUTPUT fields with no `data-omni-key` at
all). `Omni Verify Output Field` (the FlexCard assert) keeps its source name unchanged.

## Import wiring

`resources/garzai_omni.robot` Library-imports `keywords_omni.py` directly
(`Library    ${CURDIR}/garzai_omni/keywords_omni.py    WITH NAME    OmniRaw`) -- not because
this port calls the auto-generated `OmniRaw.*` keywords (it does not; every keyword in
`garzai_omni.robot` is hand-written with its own `[Documentation]` and read-back), but because
importing ANY `.py` file from a directory as an RF `Library` adds that directory to `sys.path`
(confirmed against the source template's own two `Library`-imported files,
`keywords_recordtype.py` / `keywords_upload.py`, which exist there for exactly this side effect).
That is what lets every keyword body's
`Evaluate    __import__('keywords_omni').<fn>(...)` resolve the module -- the same mechanism 2
the source template uses for every other `keywords_*.py` file (see
`docs/audit/non-qforce-keywords-inventory-2026-09-18.md` section 2, "How a keyword file gets into
a job"). The `WITH NAME` prefix keeps the auto-generated library keywords (`OmniRaw.Omni Type`,
etc.) out of the unqualified namespace so they cannot collide with the hand-written keywords of
the same un-prefixed name in this resource file.
