*** Settings ***
Documentation                 THE PARSER, STEP BY STEP -- run this suite to see what happens between "a page is open"
...                           and "the Test Agent is told what to do on it", and what actually goes over to the AI.
...
...                           One test per page. Each test runs the same six stages, in this order, and LOGS what each one
...                           produced (the console shows them as they happen; the Robot log keeps the same lines):
...
...                           1. OPEN     the job's own login and URL-first navigation put the browser on the page.
...                           2. CAPTURE  the page is serialized as the parser receives it: size in bytes, how many shadow
...                                       roots were opened, how many hidden subtrees were dropped.
...                           3. PARSE    the parser reads that capture: how many elements, which are the app's chrome and
...                                       which are the page's own, by family, and the first ten as label / family / tag.
...                           4. CALLS    for those same ten: the CRT line the parser proposes, its backup, and what the
...                                       Test Agent is finally told (a verified line from the job's store, or the derived one).
...                           5. PLAN     Gz Read Page, the keyword the Test Agent calls: the exact text it hands over, in
...                                       lines and bytes, beside the raw capture.
...                           6. SUMMARY  one line: page KB -> parser elements -> plan lines and bytes for the AI.
...
...                           Stages 2, 3, 4 and 6 are keywords in resources/garzai_parser_walkthrough.py (a new file beside
...                           garzai_page_reader.py; it calls the page reader's own functions on the same parser bundle and
...                           re-implements nothing). Stage 5 is the page reader's own Gz Read Page, unchanged.
...
...                           This suite only READS the page: no click, no type, no save. To walk another page, copy the test,
...                           change the login triple and the navigation line, and leave stages 2 to 6 as they are.
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_navigation.robot
Library                       ../resources/garzai_parser_walkthrough.py
Suite Setup                   Setup Browser
Suite Teardown                End suite


*** Test Cases ***
Parser walkthrough -- Slockard Zoo Nightmare Inputs
    [Documentation]           Walk the Zoo Nightmare Inputs page (a custom Lightning app page with 38 controls the Test
    ...                       Agent is told about) through the six stages above, logging each stage's numbers.
    # STAGE 1 -- OPEN THE PAGE (the job's own JWT login for Slockard, then the page by its tab name)
    ${token}=                 JwtAuthenticate             ${client_idSlock}           ${usernameSlock}            ${private_keySlock}
    JwtLogin
    Open Nav Tab              Zoo_Nightmare_Inputs
    # wait until the page has drawn its first label, so the capture below is of the finished page
    VerifyText                Contract Term               timeout=30
    ${url}=                   GetUrl
    Log                       GZ WALK 1 OPEN -- the browser is on ${url}    console=True
    # STAGE 2 -- CAPTURE: the page serialized the way the parser receives it
    Gz Walk Capture
    # STAGE 3 -- PARSE: the parser's elements, by family, and the first ten as label / family / tag
    Gz Walk Parse
    # STAGE 4 -- CLASSIFY + CALLS: for those same ten, the proposed keyword line, its backup, what the agent is told
    Gz Walk Calls
    # STAGE 5 -- PLAN FOR THE AI: Gz Read Page is the keyword the Test Agent calls; read every page it offers
    ${first}=                 Gz Read Page
    ${total}=                 Gz Walk Pages Total         ${first}
    @{pages}=                 Create List                 ${first}
    ${stop}=                  Evaluate                    int(${total}) + 1
    FOR    ${p}    IN RANGE    2    ${stop}
        ${text}=              Gz Read Page                page=${p}
        Append To List        ${pages}                    ${text}
    END
    Gz Walk Plan Size         ${pages}
    # STAGE 6 -- SUMMARY: the whole pipeline on one line
    Gz Walk Summary
