*** Settings ***
Documentation                 DATETIME FIELDS SIDE BY SIDE (2026-10-08) -- a customer's question, reproduced on slockard's New Change Request
...                           modal: "Start Time (Estimated)" and "End Time (Estimated)" sit side by side, each a Date box plus a Time box,
...                           and a third datetime, "Reviewed On", sits higher up the same form.
...
...                           Case 1 runs the anchored lines the customer wrote. Case 2 types the dates and PICKS the time from its list.
...                           After the steps, "Show Every Datetime Box" reads all six boxes through each field's own group (an xpath on
...                           the field's legend, independent of any anchor) and prints where every value actually went.
...                           Nothing is saved: each case ends with Cancel.
...
...                           PROVEN locally, 2026-10-08 (stock QWeb, headless Chrome on a Mac, every box read back after every step):
...                             - TypeText Date ... anchor=<field label> landed correctly ONLY with the fields on screen; below the fold the
...                               anchored lines wrote into Reviewed On's Date box instead.
...                             - TypeText Time ... anchor=End Time (Estimated) wrote into Reviewed On's Date box in 5 of 5 variants (anchor,
...                               partial_match=False, anchor=3, the click / select-all / delete / type sequence, and an ActiveAreaXpath
...                               scoped to the End field) -- and every step reported success.
...                             - Setting a date fills its time with 12:00 PM; TypeText over that APPENDS ("12:00 PM12:45 PM").
...                             - Opening the End field's own time box and clicking the option worked: 1:15 PM, read back.
...                           NOT-YET-RUN: anything in this file inside a CRT build or Live Testing. CRT's window size differs from the
...                           Mac's, so the anchored lines may land differently there: the "Show Every Datetime Box" lines will say where.
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite


*** Variables ***
# Each box located through its own field's legend -- independent of any anchor. Kept as variables: an `=` inside an
# xpath written inline in a step makes Robot read it as a named argument.
${START_DATE}                 //fieldset[legend[contains(normalize-space(.),'Start Time (Estimated)')]]//input[not(@role)]
${START_TIME}                 //fieldset[legend[contains(normalize-space(.),'Start Time (Estimated)')]]//input[@role='combobox']
${END_DATE}                   //fieldset[legend[contains(normalize-space(.),'End Time (Estimated)')]]//input[not(@role)]
${END_TIME}                   //fieldset[legend[contains(normalize-space(.),'End Time (Estimated)')]]//input[@role='combobox']
${REVIEWED_DATE}              //fieldset[legend[contains(normalize-space(.),'Reviewed On')]]//input[not(@role)]
${REVIEWED_TIME}              //fieldset[legend[contains(normalize-space(.),'Reviewed On')]]//input[@role='combobox']


*** Test Cases ***
1 Anchored lines, the customer's pattern
    [Documentation]           The customer's lines on our form, with different dates (9/1 and 9/2) so a value in the wrong box shows.
    ...                       Expected from the local run: both dates correct while the fields are on screen; the 12:30 PM lands in
    ...                       Reviewed On, and the End time stays 12:00 PM. Every step passes either way -- read the console lines.
    ${token}=                 JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Object Page          ChangeRequest    new
    VerifyText                End Time (Estimated)    timeout=30
    ScrollText                End Time (Estimated)
    TypeText                  Date              9/1/2026        anchor=Start Time (Estimated)
    TypeText                  Date              9/2/2026        anchor=End Time (Estimated)
    TypeText                  Time              12:30 PM        anchor=End Time (Estimated)
    Show Every Datetime Box
    Run Keyword And Warn On Failure    VerifyInputValue    ${END_TIME}    12:30 PM
    [Teardown]                ClickText         Cancel          partial_match=False

2 Type the date, pick the time
    [Documentation]           The form that worked locally: the dates typed with their field label as the anchor (fields on screen), the
    ...                       time PICKED by opening the End field's own time box and clicking the option. The checks at the end are
    ...                       real: this case fails if the End time is not 1:15 PM.
    ${token}=                 JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Object Page          ChangeRequest    new
    VerifyText                End Time (Estimated)    timeout=30
    ScrollText                End Time (Estimated)
    TypeText                  Date              9/1/2026        anchor=Start Time (Estimated)
    TypeText                  Date              9/2/2026        anchor=End Time (Estimated)
    ClickElement              ${END_TIME}
    ClickText                 1:15 PM           partial_match=False
    Show Every Datetime Box
    VerifyInputValue          ${START_DATE}     9/1/2026
    VerifyInputValue          ${END_DATE}       9/2/2026
    VerifyInputValue          ${END_TIME}       1:15 PM
    [Teardown]                ClickText         Cancel          partial_match=False


*** Keywords ***
Show Every Datetime Box
    [Documentation]           Read all six boxes through each field's own group (independent of any anchor) and print them.
    FOR    ${name}    ${date_box}    ${time_box}    IN
    ...    Reviewed On    ${REVIEWED_DATE}    ${REVIEWED_TIME}
    ...    Start          ${START_DATE}       ${START_TIME}
    ...    End            ${END_DATE}         ${END_TIME}
        ${date}=              GetInputValue     ${date_box}
        ${time}=              GetInputValue     ${time_box}
        Log To Console        ${name}: date=${date} time=${time}
        Log                   ${name}: date=${date} time=${time}
    END
