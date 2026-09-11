*** Settings ***
Documentation     Lightning CONSOLE keywords CRT/QForce does not ship (GarzAI, 2026-09-11) -- pure Robot over QWeb, so
...               they import into a CRT project as-is. Behaviour was measured live through the Python twins in
...               tools/qforce-lite/keywords_console.py (health90 Health Cloud Console 4 tabs -> 0, slockard Sales Console
...               2 -> 0, dev1 Digital Experiences console 2 -> 0); THIS Robot form is UNMEASURED until a CRT build runs it --
...               treat its first CRT result as the proof, not this file.
Library           QWeb


*** Variables ***
${CONSOLE_TAB}          //a[@role\="tab" and @data-tabid and contains(@class,"tabHeader") and contains(@class,"slds-context-bar__label-action")]
${CONSOLE_STRIP}        //*[contains(@class,"navexConsoleTabset") or contains(@class,"oneConsoleTabset")]
${CLOSE_ALL_DIALOG}     //*[@role\="dialog" and (contains(@class,"slds-fade-in-open") or contains(@class,"slds-modal_open"))][.//*[contains(normalize-space(.),"Close all tabs")]]


*** Keywords ***
Close All Console Tabs
    [Documentation]    A console scenario starts from an EMPTY workspace tab strip (user, 2026-09-11: with a dozen
    ...                tabs open, duplicates and misclicks follow). Sends the console shortcut Shift+W, which opens the
    ...                console's own "Close all tabs? Don't worry, pinned tabs stay open." dialog; answers Close All;
    ...                waits for the strip to empty (tabs close one by one, ~2 s); repeats up to ${rounds} times because
    ...                a last tab sometimes survives a round. Read-back: no unpinned workspace tab left. A dialog OTHER
    ...                than that confirmation (unsaved changes) is left open and the keyword fails -- never dismissed.
    [Arguments]    ${rounds}=3    ${timeout}=10
    ${is_console}=    Run Keyword And Return Status    VerifyElement    ${CONSOLE_STRIP}    timeout=3
    IF    not ${is_console}
        Log    Not a console app (no workspace tab strip) -- nothing to close    console=True
        RETURN
    END
    FOR    ${round}    IN RANGE    ${rounds}
        ${open}=    Run Keyword And Return Status    VerifyElement    ${CONSOLE_TAB}    timeout=2
        IF    not ${open}    BREAK
        ClickElement    ${CONSOLE_STRIP}
        # uppercase W = Shift+w to the focused console (the Lightning console "Close all tabs" shortcut)
        PressKey    ${CONSOLE_STRIP}    W
        ${confirm}=    Run Keyword And Return Status    VerifyElement    ${CLOSE_ALL_DIALOG}    timeout=${timeout}
        IF    ${confirm}
            ClickText    Close All    anchor=Close all tabs    partial_match=False
        END
        Run Keyword And Ignore Error    VerifyNoElement    ${CONSOLE_TAB}    timeout=${timeout}
    END
    VerifyNoElement    ${CONSOLE_TAB}    timeout=${timeout}


Open Console Subtab
    [Documentation]    Activate the console WORKSPACE tab whose title is "${record_name} | <Object>" (or exactly
    ...                ${record_name} for a list tab) and read BOTH halves back: aria-selected on that tab, and the
    ...                landed URL containing the tab's own href. A tab can highlight while the pane stays on the previous
    ...                record, so aria-selected alone is a vacuous pass; a ClickText on the record name also hits the
    ...                header and split-view rows, which is why the tab is addressed by its title attribute.
    [Arguments]    ${record_name}    ${timeout}=10
    ${tab}=    Set Variable    ${CONSOLE_TAB}[@title\="${record_name}" or starts-with(@title, "${record_name} | ")]
    VerifyElement    ${tab}    timeout=${timeout}
    ClickElement    ${tab}
    VerifyElement    ${tab}[@aria-selected\="true"]    timeout=${timeout}
    ${href}=    GetAttribute    ${tab}    href
    ${url}=    GetUrl
    Should Contain    ${url}    ${href}    msg=Tab "${record_name}" is selected but the browser did not land on its href (${href}); landed: ${url}
