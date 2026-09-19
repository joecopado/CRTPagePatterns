*** Settings ***
Documentation     GarzAI generated data (2026-09-19, build n7) -- the small, stdlib-only value
...               generator the composed pane calls. THE CONTAINER MAY NOT HAVE `faker`, so
...               nothing here imports anything outside the Python standard library and Robot's
...               own BuiltIn/String/DateTime/Collections.
...
...               WHY THIS EXISTS (user, 2026-09-19): "Every value is hard-coded, so the second run
...               fails on duplication rules." A recorded fill whose typed value is a SENTINEL
...               (`asdf`, or the explicit `@@` grammar) composes a VARIABLE line above the fill --
...               `${lead_last_name}=    Gz Unique Text    Last Name` -- and the fill uses the
...               variable, so a later verify or cleanup step reuses the SAME value.
...
...               THE RUN STAMP IS THE CLEANUP TAG. `Gz Run Stamp` mints one stamp per run
...               (`yyyymmdd-hhmmss-rand4`), keeps it in the global `${GZ_RUN_STAMP}`, and every
...               text-shaped generated value carries it. A teardown step deletes by that tag:
...                   ${stamp}=    Gz Run Stamp
...                   ...    SELECT Id FROM Lead WHERE LastName LIKE '%${stamp}%'
...               Teardown is a STEP, not a Suite Teardown -- CRT Live Testing skips Teardown
...               (CLAUDE.md), so a cleanup that only runs there never runs at all.
...
...               EVERY KEYWORD LOGS ITS VALUE TO THE CONSOLE ONCE, because a generated value that
...               nobody can read is a value nobody can check. `print()` is invisible in Live
...               Testing, so the log goes through `Log To Console`.
...
...               COULD-NOT-CHECK IS A REAL ANSWER. `Gz Pick` with no options it can trust FAILS
...               with the word COULD-NOT-CHECK in the message. It never invents a picklist value:
...               an invented option is the quiet-wrong-answer failure this repo is built around.
...
...               The composer-side twin of the sentinel table is
...               `tools/recorder/crt_override/compose_live.py` (`sentinel_spec`,
...               `SF_TYPE_GENERATOR`); `Gz Is Sentinel` below must agree with it, and
...               `tools/recorder/tests/test_crt_override_generated_data_2026_09_19.py` asserts
...               they do over the same table.
Library           Collections


*** Variables ***
# Minted by `Gz Run Stamp` on first use and kept for the whole run. A suite that wants a stamp of
# its own (re-running a cleanup against yesterday's data) sets it in its own Variables.
${GZ_RUN_STAMP}          ${EMPTY}
# RFC 2606 reserved: nothing generated here can ever be delivered to a real mailbox.
${GZ_EMAIL_DOMAIN}       example.invalid
# Path to a JSON file the suite ships with, read by `Gz Field Options`. Two shapes are accepted:
# the flat `{"Lead": {"Salutation": ["Mr.", "Ms."]}}`, and an org-map projection
# `{"objects": {"Lead": {"inventory": {"fields": {"value": {"Salutation": {"picklist_values": [...],
# "label": "Salutation"}}}}}}}` -- the same file `discover.py` writes. Empty means COULD-NOT-CHECK,
# never an invented option.
${GZ_FIELD_OPTIONS}      ${EMPTY}
# The object `Gz Pick` looks a bare label up under when the caller gave no options.
${GZ_DEFAULT_OBJECT}     ${EMPTY}
@{GZ_GENERATED}


*** Keywords ***
Gz Run Stamp
    [Documentation]    The ONE run stamp for this run: `yyyymmdd-hhmmss-rand4`. Minted on first
    ...    use, kept in the global `${GZ_RUN_STAMP}`, carried inside every text-shaped generated
    ...    value, and the tag a cleanup step deletes by. Calling it twice returns the same stamp --
    ...    two stamps in one run would mean two cleanup tags and one of them would be missed.
    IF    $GZ_RUN_STAMP not in (None, '')
        RETURN    ${GZ_RUN_STAMP}
    END
    ${stamp}=    Evaluate
    ...    datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(4))
    ...    modules=datetime, random
    Set Global Variable    ${GZ_RUN_STAMP}    ${stamp}
    Log To Console    GarzAI data: run stamp ${stamp} -- every generated value carries it; a cleanup step deletes by it.
    RETURN    ${stamp}


Gz Log Generated
    [Documentation]    One console line per generated value, and the value kept in
    ...    @{GZ_GENERATED} so `Gz Generated Tally` can print the whole run's data at the end.
    [Arguments]    ${keyword}    ${value}
    Log To Console    GarzAI data: ${keyword} -> '${value}'
    Append To List    ${GZ_GENERATED}    ${keyword} -> ${value}
    Set Suite Variable    ${GZ_GENERATED}
    RETURN    ${value}


Gz Generated Tally
    [Documentation]    Prints every value generated this run and returns the count -- run it as a
    ...    step before the cleanup step, so the pane shows what is about to be deleted.
    ${n}=    Get Length    ${GZ_GENERATED}
    Log To Console    GarzAI data: ${n} generated values this run (run stamp '${GZ_RUN_STAMP}')
    FOR    ${v}    IN    @{GZ_GENERATED}
        Log To Console    - ${v}
    END
    RETURN    ${n}


Gz Unique Text
    [Documentation]    `<base> <run stamp>` -- unique per run, so a second run of the same
    ...    recording does not trip a duplicate rule. `max_length` truncates from the LEFT of the
    ...    base (never of the stamp: the stamp is the cleanup tag and losing it loses the record),
    ...    and says so on the console when it fires. 0 means no limit.
    [Arguments]    ${base}    ${max_length}=0
    ${stamp}=    Gz Run Stamp
    ${value}=    Evaluate    ((str($base).strip() or 'GZ') + ' ' + $stamp)
    ${limit}=    Evaluate    int($max_length)
    IF    ${limit} > 0 and len($value) > ${limit}
        ${keep}=    Evaluate    max(0, ${limit} - len($stamp) - 1)
        ${value}=    Evaluate    (str($base).strip()[:${keep}] + ' ' + $stamp).strip()[-${limit}:]
        Log To Console    GarzAI data: Gz Unique Text truncated the BASE to fit ${limit} characters; the run stamp is kept whole (it is the cleanup tag).
    END
    ${value}=    Gz Log Generated    Gz Unique Text    ${value}
    RETURN    ${value}


Gz Email
    [Documentation]    A unique address in the RFC 2606 reserved domain `${GZ_EMAIL_DOMAIN}`
    ...    (`example.invalid`) -- it cannot resolve, so nothing generated here can be delivered to
    ...    a real person. Carries the run stamp.
    [Arguments]    ${base}=gz
    ${stamp}=    Gz Run Stamp
    ${local}=    Evaluate    (re.sub(r'[^a-z0-9]+', '.', str($base).strip().lower()).strip('.') or 'gz')    modules=re
    ${value}=    Evaluate    $local + '.' + $stamp + '@' + $GZ_EMAIL_DOMAIN
    ${value}=    Gz Log Generated    Gz Email    ${value}
    RETURN    ${value}


Gz Phone
    [Documentation]    A number in the 555-0100..555-0199 block North American numbering reserves
    ...    for fiction -- it can never reach a real line. Rendered `(555) 555-01NN`; a formatted
    ...    read-back compares by DIGITS (`Values Match` tier 3), so the widget may reformat it.
    ...    A phone carries no run stamp: there is nowhere in ten digits to put one, so a suite that
    ...    cleans up by tag tags a TEXT field, not this.
    ${n}=    Evaluate    random.randint(100, 199)    modules=random
    ${value}=    Set Variable    (555) 555-0${n}
    ${value}=    Gz Log Generated    Gz Phone    ${value}
    RETURN    ${value}


Gz Number
    [Documentation]    A random integer in [min, max], inclusive, as a string. No run stamp -- a
    ...    number field has nowhere to carry one.
    [Arguments]    ${min}    ${max}
    ${lo}=    Evaluate    int($min)
    ${hi}=    Evaluate    int($max)
    IF    ${hi} < ${lo}
        Fail    COULD-NOT-CHECK: Gz Number(${min}, ${max}): max is below min, so there is no value to generate.
    END
    ${value}=    Evaluate    str(random.randint(${lo}, ${hi}))    modules=random
    ${value}=    Gz Log Generated    Gz Number    ${value}
    RETURN    ${value}


Gz Date
    [Documentation]    Today plus `offset` DAYS. `+30`, `30` and `-1` all read the same way.
    ...    `format`: the default `MM/DD/YYYY` is what a Salesforce date input renders in a US
    ...    locale; `--iso` gives `YYYY-MM-DD`, which is what `Omni Date` takes.
    ...    THE OFFSET IS THE POINT: a recorded literal date drifts into the past and the field
    ...    rejects it; an offset picks a date the same distance away on every later run.
    [Arguments]    ${offset}    ${format}=us
    ${days}=    Evaluate    int(str($offset).strip().lstrip('+'))
    ${fmt}=    Evaluate    '%Y-%m-%d' if str($format).strip().lower() in ('--iso', 'iso', 'yyyy-mm-dd') else '%m/%d/%Y'
    ${value}=    Evaluate    (datetime.date.today() + datetime.timedelta(days=${days})).strftime($fmt)    modules=datetime
    ${value}=    Gz Log Generated    Gz Date    ${value}
    RETURN    ${value}


Gz Text
    [Documentation]    `length` characters. The run stamp is embedded when the length allows it
    ...    (and the console line SAYS when it did not), so a long text field is still cleanable by
    ...    tag while a short one is honest about not being.
    [Arguments]    ${length}
    ${n}=    Evaluate    int($length)
    IF    ${n} <= 0
        Fail    COULD-NOT-CHECK: Gz Text(${length}): a length of ${n} has no value to generate.
    END
    ${stamp}=    Gz Run Stamp
    ${fits}=    Evaluate    ${n} >= len($stamp) + 1
    IF    ${fits}
        ${value}=    Evaluate    ($stamp + ' ' + ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(${n})))[:${n}]    modules=random
    ELSE
        ${value}=    Evaluate    ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(${n}))    modules=random
        Log To Console    GarzAI data: Gz Text(${n}) is too short to carry the run stamp '${stamp}' -- this value is NOT cleanable by tag.
    END
    ${value}=    Gz Log Generated    Gz Text    ${value}
    RETURN    ${value}


Gz Pick
    [Documentation]    A valid value for a picklist, chosen from the options GIVEN, or -- when
    ...    none are -- from `Gz Field Options ${GZ_DEFAULT_OBJECT} <label>`. The listbox's own
    ...    "nothing chosen" entries (`-- None --`, `-- No Value --`, `Select an Option`, ...) are
    ...    never chosen: picking one leaves the field where it began, which is not a step
    ...    (measured live on fsc7f 2026-09-19 13:13).
    ...    WITH NOTHING TO CHOOSE FROM IT FAILS, naming COULD-NOT-CHECK. It never invents an
    ...    option -- an invented picklist value is rejected by the org, or worse, accepted.
    [Arguments]    ${label}    @{options}
    ${usable}=    Gz Usable Options    @{options}
    ${n}=    Get Length    ${usable}
    IF    ${n} == 0
        ${usable}=    Gz Field Options    ${GZ_DEFAULT_OBJECT}    ${label}
        ${n}=    Get Length    ${usable}
    END
    IF    ${n} == 0
        Fail    COULD-NOT-CHECK: Gz Pick('${label}'): no usable option was given and none was found in ${GZ_FIELD_OPTIONS} -- an option is never invented.
    END
    ${value}=    Evaluate    random.choice($usable)    modules=random
    ${value}=    Gz Log Generated    Gz Pick('${label}')    ${value}
    RETURN    ${value}


Gz Usable Options
    [Documentation]    The given options with blanks, duplicates and every "nothing chosen"
    ...    placeholder removed, in the order they arrived.
    [Arguments]    @{options}
    ${out}=    Evaluate    [o for o in dict.fromkeys(re.sub(r'\\s+', ' ', str(x)).strip() for x in $options) if o and o.casefold() not in ('-- no value --', '--none--', '-- none --', 'none', 'select an option', 'select...', 'select', '--select--', '-- select --', '--select an option--')]    modules=re
    RETURN    ${out}


Gz Field Options
    [Documentation]    The active picklist values of `<object>.<field>` read from the JSON file at
    ...    `${GZ_FIELD_OPTIONS}` -- the org map is the input (CLAUDE.md), never a live describe
    ...    from inside a test. `field` matches the API name OR the rendered label.
    ...    Returns an EMPTY list, with the reason on the console, when the suite carries no map
    ...    path or the field is not in it: the caller turns that into COULD-NOT-CHECK. It never
    ...    invents an option.
    [Arguments]    ${object}    ${field}
    ${none}=    Create List
    IF    $GZ_FIELD_OPTIONS in (None, '')
        Log To Console    GarzAI data: COULD-NOT-CHECK: Gz Field Options('${object}', '${field}'): this suite carries no ${GZ_FIELD_OPTIONS} path, so no option list is known.
        RETURN    ${none}
    END
    ${data}=    Evaluate    json.loads(pathlib.Path($GZ_FIELD_OPTIONS).read_text())    modules=json, pathlib
    # the org-map projection nests the object under `objects`; the flat shape does not
    ${obj}=    Evaluate    ($data.get('objects') or {}).get(str($object)) or $data.get(str($object)) or {}
    # ... and the fields under inventory.fields.value; the flat shape IS the field table
    ${fields}=    Evaluate    ((($obj.get('inventory') or {}).get('fields') or {}).get('value')) or $obj
    ${want}=    Evaluate    re.sub(r'\\s+', ' ', str($field)).strip().strip('*').strip().casefold()    modules=re
    # By API name first, then by the RENDERED label -- the composer only ever knows the label.
    # THE INDEXES ARE BUILT FIRST AND LOOKED UP SECOND, deliberately. A `next((v for k, v in
    # $fields.items() if ... == $want), None)` reads correctly and FAILS at run time: Robot injects
    # `$want` as a local, and a generator expression opens a scope that cannot see the enclosing
    # locals, so Robot raises "variable '$want' is used in a scope where it cannot be seen".
    # `--dryrun` does not execute expressions, so it passed; the real run is what found it
    # (2026-09-19, building n7). A dict comprehension over `$fields` alone is safe -- the outermost
    # iterable is the one thing such a scope CAN see.
    ${by_label}=    Evaluate    {str(v.get('label') or '').strip().casefold(): v for k, v in $fields.items() if isinstance(v, dict)}
    ${by_name}=    Evaluate    {str(k).casefold(): v for k, v in $fields.items()}
    ${entry}=    Evaluate    $fields.get(str($field)) or $by_label.get($want) or $by_name.get($want) or {}
    ${opts}=    Evaluate    [str(x) for x in (($entry.get('picklist_values') if isinstance($entry, dict) else $entry) or []) if str(x).strip()]
    ${opts}=    Gz Usable Options    @{opts}
    ${n}=    Get Length    ${opts}
    IF    ${n} == 0
        Log To Console    GarzAI data: COULD-NOT-CHECK: Gz Field Options('${object}', '${field}'): ${GZ_FIELD_OPTIONS} carries no picklist values for it.
    END
    RETURN    ${opts}


Gz Is Sentinel
    [Documentation]    True when a value IS a sentinel -- the bare `asdf` (case-insensitive,
    ...    surrounding whitespace ignored) or the explicit `@@` grammar (`@@email`, `@@phone`,
    ...    `@@pick`, `@@unique <base>`, `@@date+N`, `@@date-N`, `@@int <min> <max>`,
    ...    `@@text <len>`). NOTHING ELSE: `asdfasdf`, `test`, `qwer` are values a person typed on
    ...    purpose, and treating one as a sentinel would silently replace data they meant.
    ...    The composer's own `compose_live.sentinel_spec` is the twin of this table.
    [Arguments]    ${value}
    ${hit}=    Evaluate    bool(re.fullmatch(r'(?i)\\s*(asdf|@@(email|phone|pick)|@@unique(\\s+\\S.*)?|@@date\\s*[+-]\\s*\\d+|@@int\\s+-?\\d+\\s+-?\\d+|@@text\\s+\\d+)\\s*', str($value)))    modules=re
    RETURN    ${hit}


Gz Sentinel Verdict
    [Documentation]    THE SENTINEL-LANDED VERDICT. A value read back off the page that is ITSELF
    ...    a sentinel means the generated-data rule never fired for that field and the literal
    ...    `asdf` went into the record -- `CAUGHT-BUG: sentinel landed`, never a quiet pass.
    ...    Returns True when it fired, so the caller can stop before printing a pass.
    ...    Honours `${GZ_ON_MISMATCH}` the same way the TypeText override does (default `warn`:
    ...    print, keep, continue).
    [Arguments]    ${where}    ${actual}
    ${landed}=    Gz Is Sentinel    ${actual}
    IF    not ${landed}
        RETURN    ${False}
    END
    ${line}=    Set Variable    ${where}: the value read back is the SENTINEL '${actual}' -- the generated-data rule never fired for this field, so a literal sentinel went into the record.
    Log To Console    CAUGHT-BUG: sentinel landed -- ${line}
    ${mode}=    Get Variable Value    ${GZ_ON_MISMATCH}    warn
    IF    '${mode}' == 'warn'
        Log    CAUGHT-BUG: sentinel landed -- ${line}    level=WARN
    ELSE
        Fail    CAUGHT-BUG: sentinel landed -- ${line}
    END
    RETURN    ${True}
