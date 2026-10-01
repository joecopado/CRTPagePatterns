*** Settings ***
Documentation     Click a switch inside a NATIVE shadow root only when its aria-checked is "true".
...               Graham's question (2026-10-01), answered as one test case against the mock page
...               beside this file, which mirrors chrome://extensions:
...                   <cr-toggle id="enableToggle" role="switch" aria-checked="true"> inside an open shadow root.
...               Only QWeb is imported, so every keyword below is called by its plain name.
Library           QWeb
Suite Setup       Open Mock Page
Suite Teardown    CloseAllBrowsers

*** Variables ***
${MOCK}           file://${CURDIR}/cr_toggle_mock.html
${HEADLESS}       False    # locally: robot -v HEADLESS:True ...   (leave False in CRT)

*** Keywords ***
Open Mock Page
    SetConfig         Headless    ${HEADLESS}
    OpenBrowser       ${MOCK}    chrome
    SetConfig         DefaultTimeout    5

*** Test Cases ***
Click the extension toggle only when aria-checked is true
    # 1. Item keywords only look inside shadow roots when this is on. Without it the toggle is
    #    "not found" even though it is on screen.
    SetConfig         ShadowDOM    True

    # 2. Read the attribute from the element itself. "enableToggle" matches because, with
    #    ShadowDOM on, ClickItem/GetAttribute match the text against the VALUE of any attribute
    #    on every <cr-toggle> they find (here the id). element_type=item makes GetAttribute use
    #    the same item search ClickItem uses.
    ${state}=         GetAttribute    enableToggle    aria-checked    element_type=item    tag=cr-toggle
    Log To Console    aria-checked before: ${state}

    # 3. The conditional click.
    IF    '${state}' == 'true'
        ClickItem     enableToggle    tag=cr-toggle
    END

    # 4. Read it back: the click flipped the switch, so it must now be "false".
    ${after}=         GetAttribute    enableToggle    aria-checked    element_type=item    tag=cr-toggle
    Log To Console    aria-checked after: ${after}
    Should Be Equal   ${after}    false

    # What does NOT work, measured on this page:
    #   ClickItem    enableToggle    tag=cr-toggle    aria-checked=true
    #       -> aria-checked=true is NOT a filter. It is ignored, and the click reports PASS even when
    #          the toggle is false. Use GetAttribute + IF as above.
    #   ClickItem    aria-checked\=true    tag=cr-toggle
    #       -> not found. No attribute has the literal value "aria-checked=true".
    #   ClickItem    true    tag=cr-toggle
    #       -> works, but matches ANY attribute on ANY cr-toggle whose value is "true". Fragile.
