*** Settings ***
Documentation     ClickItem / VerifyItem / GetAttribute on a switch inside a NATIVE shadow root,
...               and how to click it CONDITIONALLY on its aria-checked value (Graham's question,
...               2026-10-01). Runs against the mock page beside this file, which mirrors
...               chrome://extensions: <cr-toggle id="enableToggle" role="switch" aria-checked="true">
...               inside an open shadow root, plus a decoy toggle that is aria-checked="false".
...               No org, no login. Every case reads the state back from the element itself.
...
...               The three facts, from the QWeb source (internal/text.py, internal/javascript.py):
...               1. Item keywords reach into shadow DOM only with `SetConfig    ShadowDOM    True`.
...               2. With it on, ClickItem walks every open shadow root, keeps elements whose tag
...                  equals `tag=`, and matches the text against the FULL VALUE of ANY attribute.
...                  So `enableToggle` matches by the id's value.
...               3. Any other kwarg (`aria-checked=true`) is NOT a filter -- it is ignored, and the
...                  click still reports PASS. The conditional click is GetAttribute + IF (case 3).
Resource          ../../resources/common.robot
Suite Setup       Open Mock Page
Suite Teardown    CloseAllBrowsers

*** Variables ***
# the mock page, beside this suite; CRT checks the repo out, so ${CURDIR} resolves in the container too
${MOCK}           file://${CURDIR}/cr_toggle_mock.html
# local runs: robot -v HEADLESS:True ...   (the CRT container streams its own screen; leave False there)
${HEADLESS}       False

*** Keywords ***
Open Mock Page
    # the repo's own convention (common.robot, Setup Browser): QForce first, QWeb second. SetConfig exists
    # in BOTH, so this suite names QWeb.SetConfig in full -- it resolves the same locally and in the container.
    Set Library Search Order    QForce    QWeb
    QWeb.SetConfig    Headless    ${HEADLESS}
    OpenBrowser       ${MOCK}    ${BROWSER}
    QWeb.SetConfig         DefaultTimeout    5
    VerifyText        Extension toggle mock

Toggle State
    [Documentation]    The aria-checked value of the enable toggle, read from the element inside the shadow root.
    QWeb.SetConfig         ShadowDOM    True
    ${state}=         GetAttribute    enableToggle    aria-checked    element_type=item    tag=cr-toggle
    RETURN            ${state}

*** Test Cases ***
1 Without the ShadowDOM config the toggle is invisible to ClickItem
    QWeb.SetConfig         ShadowDOM    False
    Run Keyword And Expect Error    QWebElementNotFoundError*    ClickItem    enableToggle    tag=cr-toggle    timeout=2
    Log               VERIFIED-PASS: not found while ShadowDOM is False

2 With ShadowDOM on, ClickItem by the id value clicks the toggle and the state flips
    QWeb.SetConfig         ShadowDOM    True
    ${before}=        Toggle State
    Should Be Equal   ${before}    true
    ClickItem         enableToggle    tag=cr-toggle
    ${after}=         Toggle State
    Should Be Equal   ${after}    false
    VerifyText        state: false
    # put it back for the next case
    ClickItem         enableToggle    tag=cr-toggle
    VerifyText        state: true

3 The conditional click: GetAttribute the state, then IF
    QWeb.SetConfig         ShadowDOM    True
    ${state}=         Toggle State
    IF    '${state}' == 'true'
        ClickItem     enableToggle    tag=cr-toggle
        Log           was true -> clicked
    ELSE
        Log           was false -> left alone
    END
    ${state2}=        Toggle State
    Should Be Equal   ${state2}    false
    VerifyText        state: false
    ClickItem         enableToggle    tag=cr-toggle
    VerifyText        state: true

4 An extra kwarg such as aria-checked=true is NOT a filter (it is ignored)
    QWeb.SetConfig         ShadowDOM    True
    # the decoy is aria-checked="false"; asking for aria-checked=true still clicks it and reports PASS
    ClickItem         otherToggle    tag=cr-toggle    aria-checked=true
    ${decoy}=         GetAttribute    otherToggle    aria-checked    element_type=item    tag=cr-toggle
    Should Be Equal   ${decoy}    true
    Log               CAUGHT-BUG shape: the kwarg was ignored and a false toggle was clicked
    ClickItem         otherToggle    tag=cr-toggle

5 aria-checked\=true as the locator text matches nothing (no attribute HAS that value)
    QWeb.SetConfig         ShadowDOM    True
    Run Keyword And Expect Error    QWebElementNotFoundError*    ClickItem    aria-checked\=true    tag=cr-toggle    timeout=2

6 Matching the bare attribute VALUE works but is ambiguous by design
    QWeb.SetConfig         ShadowDOM    True
    # 'true' equals aria-checked on the enable toggle only (the decoy is false) -- but it would also
    # match ANY cr-toggle attribute whose value is 'true'; prefer the id form with GetAttribute
    ClickItem         true    tag=cr-toggle
    VerifyText        state: false
    ClickItem         enableToggle    tag=cr-toggle
    VerifyText        state: true
    ${state}=         Toggle State
    Should Be Equal   ${state}    true
