# Test Agent guide: reading a page, calling a control, checking the result

This job ships three keywords made for you, the CRT Test Agent. They are imported by
`resources/common.robot`, so they are in your test-keywords list whenever a suite here is open.

| Keyword | Arguments | What it does |
|---|---|---|
| `Gz Read Page` | `page=1`, `include_chrome=False`, `org=` | Reads the current page and prints its controls, 20 per page, each with the exact call to use. It does not act on the page. |
| `Gz Show` | `label`, `index=` | Prints one control in full: every way to call it, strongest first. It does not act on the page. |
| `Gz Verify` | `label`, `expected_value`, `index=`, `on_mismatch=fail` | Reads the control's value back without touching it, then prints a verdict. |

## 1. Confirm a keyword before you call it

- Look in your test-keywords list first.
- Before the first call, run `lookup_keyword` with the EXACT name. The name is `Gz Read Page`, not
  `Read Page`. A call to a name that does not exist cannot run, so it cannot pass.
- Never call a keyword from memory, and never rebuild your keyword list from file names.

## 2. Read the page before you act

Call `Gz Read Page`. The output ends like this:

```
GZ READ PAGE slockard|/lightning/n/Zoo_Nightmare_Inputs -- 38 controls to act on (fresh read)
  14 of 38 calls passed live before (# verified, from the job's store); the rest are derived from this page
 1. (no label) [field] TypeText    xpath\=//*[normalize-space(text())\="Contract Term"]/following-sibling::*//input[@type\="text"]    <value>
 2. Contract Term (1 of 2) [field] TypeText    Contract Term    <value>    # verified x1
 ...
 6. Amount (3 of 3) [field] TypeText    Amount    <value>    anchor=3    # verified x1
  not listed: 41 chrome (Gz Read Page    include_chrome=True lists them); 5 with no call (Gz Show    <label> says why); 27 hidden subtrees never captured
GZ READ PAGE page 1 of 2 ref 614a5266 -- NEXT: Gz Read Page    page=2    (...)
```

How to read one line: `<number>. <label as a person sees it> [<kind>] <the call to use>`.

- `# verified xN`: this exact call passed live N times before. Prefer it.
- `(2 of 3)`: the label appears 3 times on the page and this is the second. The call already has
  `anchor=2`. Keep it.
- Replace the placeholder with your data: `<value>`, `<option>` (a real option of that picklist),
  `<on|off>`, `<record name>` (a real record), `<date>` (typed in the user's own date format, never
  picked from the calendar).
- `(no label)`: nothing on the page names this control, so the call uses a relative xpath. Use it as
  written.
- The LAST line says whether there is more. `NEXT: Gz Read Page    page=2` means there is. `END of the
  page plan` means you have seen every control.
- `a modal is open: run UseModal    On ...` means: call `UseModal    On` before acting in the modal,
  and `UseModal    Off` once it closes.
- `not listed:` counts what was left out and why. Chrome is the app's own header and navigation, and
  `include_chrome=True` lists it. Controls behind an open modal cannot be reached until it closes.

## 3. When a call fails

1. Call `Gz Show    <label>`. Use `index=<n>` when the label repeats. It lists every rung in order:
   the keyword form, then `ClickItem`, then a relative xpath.
2. Try the next rung down. Never write an absolute xpath (`/html/...`) and never count positions.
3. If every rung fails, say so and stop. A guessed locator is worse than a reported failure.

## 4. Check every value you set

After you type, pick or tick something, call `Gz Verify    <label>    <value>`. On a repeated label,
add `index=<n>` with the same number the page plan showed.

| Last console line | Step result | Meaning |
|---|---|---|
| `VERIFIED-PASS: reads '25,000.00', equal to '25000' by meaning` | PASS | The value is there. `10/08/2026` equals `10/8/2026`, and `25,000.00` equals `25000`. |
| `CAUGHT-BUG: reads '12', expected '24'` | FAIL | The page holds something else. Report it. Do not re-type over it. |
| `CAUGHT-BUG: the read returned the field's own LABEL ...` | FAIL | The read found the label, not the value. |
| `COULD-NOT-CHECK: ...` | FAIL | Nothing could be read, for the reason given. This is not a pass. |

A `try_keyword` PASS on a TypeText or ClickText means the keyword ran. It does not mean the value
landed. Only a `Gz Verify` VERIFIED-PASS shows that.

## 5. Finding the output

Every answer prints to the CONSOLE and ends with the line that matters: the page pointer, the call
to use, or the verdict.

- `read_executor_output` returns the last lines of the whole session. If you cannot see the
  `GZ READ PAGE ... ref ...` line, `GZ SHOW ...: use` line or verdict line, ask for MORE lines.
- Never run a step again to find its output. Running it again adds more output, which pushes the
  answer further up.
- If someone asks what a keyword returned, quote its last line word for word, including the `ref`.

## 6. What these keywords never do

They never click, type or save to read a page. They never print a call built on an absolute xpath.
They never treat a blank read-back as a pass. The full page plan, every control and every cut with
its reason, is written to the run's output folder as `gz-page-plan-<page>.json` for people and tools.
You cannot open that file. Use `Gz Show` instead.
