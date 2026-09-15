*** Settings ***
Resource                      ../../resources/common.robot
Resource                      ../../resources/garzai_console.robot
Resource                      ../../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 103 steps, 0 controls listed as comments (11 buckets)
*** Test Cases ***
Review /en/commit/{id}
    # Inline steps: no custom keywords. Authenticates with the suite's own JWT variables, then Generated from docs/recorder/captures/cicd-demo/commit-experience-after-get-changes-search.html
    # SECICD -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idCICD}    ${usernameCICD}    ${private_keyCICD}
    JwtLogin
    # TRANSITION: the Commit Experience is a separate app (na.devops.copado.com); the same browser session carries the auth
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Find Metadata    timeout=30
    # STATE precondition: rows exist only after Get Changes; the capture behind this table had the search box filled
    ClickText    Get Changes    partial_match=False
    VerifyText    Quick Find    timeout=30
    TypeText    Search    Opportunity_Creation
    VerifyText    Opportunity_Creation_Automation    timeout=15    partial_match=True

    # ===== 1. every control resolves (non-mutating) =====
    # row 8  input_field  "Last modified by"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b8)
    VerifyElement    xpath\=//input[@name\="modifiedBy"]    timeout=5
    # row 9  input_field  "All metadata types"  [unreviewed]  -- member of bucket b8
    VerifyElement    xpath\=//input[@name\="types"]    timeout=5
    # row 10  input_field  "Metadata API name"  [accepted]  -- 2 of 2 same-shape controls (bucket b9)
    VerifyInputElement    Metadata API name    timeout=5
    VerifyElement    xpath\=//input[@name\="apiName"]    timeout=5
    # row 18  input_field  "Search"  [accepted]  -- member of bucket b9
    VerifyInputElement    Search    timeout=5
    VerifyElement    xpath\=//input[@placeholder\="Search"]    timeout=5
    # row 4  button  "Refresh Changes"  [accepted]
    VerifyText    Refresh Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Find Metadata"]/following::a)[1]    timeout=5
    # row 6  button  "×"  [accepted]  -- 3 of 5 same-shape controls (bucket b0)
    VerifyText    ×    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Changed since last commit"]/following::button[@type\="button"])[1]    timeout=5
    # row 12  button  "Get Changes"  [accepted]  -- member of bucket b0
    VerifyText    Get Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Find managed package changes"]/following::button[@type\="submit"])[1]    timeout=5
    # row 13  button  "Select Changes"  [accepted]  -- member of bucket b0
    VerifyText    Select Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Get Changes"]/following::button[@type\="button"])[1]    timeout=5
    # row 14  button  "Get Previously Commited (4)"  [accepted]  -- member of bucket b0
    VerifyText    Get Previously Commited (4)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Quick Find"]/following::button[@type\="button"])[1]    timeout=5
    # row 15  link  "Changes"  [accepted]  -- 3 of 3 same-shape controls (bucket b4)
    VerifyText    Changes    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="vcicd3-0services1-36-a249fb9c"]/following::a)[1]    timeout=5
    # row 16  link  "Selected metadata 0"  [accepted]  -- member of bucket b4
    VerifyText    Selected metadata 0    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Changes"]/following::a)[1]    timeout=5
    # row 17  link  "Selected Data 0"  [accepted]  -- member of bucket b4
    VerifyText    Selected Data 0    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Selected metadata"]/following::a)[1]    timeout=5
    # row 19  button  "Dependency Analysis"  [accepted]  -- member of bucket b0
    VerifyText    Dependency Analysis    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="0 of 1178 items selected"]/following::button)[1]    timeout=5
    # row 20  unknown  "Select all rows"  [accepted]  -- 3 of 4 same-shape controls (bucket b2)
    VerifyItem    Select all rows    tag=label    partial_match=False    timeout=5
    VerifyElement    xpath\=//label[@aria-label\="Select all rows"]    timeout=5
    # row 22  unknown  "Select row Flow:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    VerifyItem    Select row Flow:Opportunity_Creation_Automation    tag=label    partial_match=False    timeout=5
    VerifyElement    xpath\=//label[@aria-label\="Select row Flow:Opportunity_Creation_Automation"]    timeout=5
    # row 24  unknown  "Select row WorkflowFlowAutomation:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    VerifyItem    Select row WorkflowFlowAutomation:Opportunity_Creation_Automation    tag=label    partial_match=False    timeout=5
    VerifyElement    xpath\=//label[@aria-label\="Select row WorkflowFlowAutomation:Opportunity_Creation_Automation"]    timeout=5
    # row 26  unknown  "Select row FlowDefinition:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    VerifyItem    Select row FlowDefinition:Opportunity_Creation_Automation    tag=label    partial_match=False    timeout=5
    VerifyElement    xpath\=//label[@aria-label\="Select row FlowDefinition:Opportunity_Creation_Automation"]    timeout=5
    # row 28  unknown  "Source"  [accepted]  -- 3 of 4 same-shape controls (bucket b3)
    VerifyItem    source    tag=cds-select-input    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=//cds-select-input[@name\="source"]    timeout=5
    # row 29  unknown  "Select a date"  [accepted]  -- member of bucket b3
    VerifyItem    Select a date    tag=cds-select-input    partial_match=False    timeout=5
    VerifyElement    xpath\=//cds-select-input[@aria-label\="Select a date"]    timeout=5
    # row 30  unknown  "Last modified by"  [accepted]  -- member of bucket b3
    VerifyItem    modifiedBy    tag=cds-select-input    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=//cds-select-input[@name\="modifiedBy"]    timeout=5
    # row 31  unknown  "Metadata Type"  [accepted]  -- member of bucket b3
    VerifyItem    types    tag=cds-select-input    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=//cds-select-input[@name\="types"]    timeout=5

    # ===== 2. fill controls, each read back (nothing is saved) =====
    # row 8  input_field  "Last modified by"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b8)
    TypeText    Last modified by    GZREV Last modified by 1    timeout=40
    ClickItem    GZREV Last modified by 1    tag=div
    # COULD-NOT-RENDER clarity-lookup: no 'host_id' for this row
    # row 9  input_field  "All metadata types"  [unreviewed]  -- member of bucket b8
    TypeText    All metadata types    GZREV All metadata types 1    timeout=40
    ClickItem    GZREV All metadata types 1    tag=div
    # COULD-NOT-RENDER clarity-lookup: no 'host_id' for this row
    # row 10  input_field  "Metadata API name"  [accepted]  -- 2 of 2 same-shape controls (bucket b9)
    TypeText    Metadata API name    GZREV Metadata API name
    VerifyInputValue    Metadata API name    GZREV Metadata API name
    # row 18  input_field  "Search"  [accepted]  -- member of bucket b9
    TypeText    Search    GZREV Search
    VerifyInputValue    Search    GZREV Search

    # ===== 3. clicks, each preceded by a fresh GoTo (many of these navigate away) =====
    # row 4  button  "Refresh Changes"  [accepted]
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Refresh Changes    partial_match=False
    # row 6  button  "×"  [accepted]  -- 3 of 5 same-shape controls (bucket b0)
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    ×    partial_match=False
    # row 12  button  "Get Changes"  [accepted]  -- member of bucket b0
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Get Changes    partial_match=False
    # row 13  button  "Select Changes"  [accepted]  -- member of bucket b0
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Select Changes    partial_match=False
    # row 14  button  "Get Previously Commited (4)"  [accepted]  -- member of bucket b0
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Get Previously Commited (4)    partial_match=False
    # row 15  link  "Changes"  [accepted]  -- 3 of 3 same-shape controls (bucket b4)
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Changes    anchor=1    partial_match=False
    # row 16  link  "Selected metadata 0"  [accepted]  -- member of bucket b4
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Selected metadata 0    partial_match=False
    # row 17  link  "Selected Data 0"  [accepted]  -- member of bucket b4
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Selected Data 0    partial_match=False
    # row 19  button  "Dependency Analysis"  [accepted]  -- member of bucket b0
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickText    Dependency Analysis    partial_match=False
    # row 20  unknown  "Select all rows"  [accepted]  -- 3 of 4 same-shape controls (bucket b2)
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    Select all rows    tag=label    partial_match=False
    # row 22  unknown  "Select row Flow:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    Select row Flow:Opportunity_Creation_Automation    tag=label    partial_match=False
    # row 24  unknown  "Select row WorkflowFlowAutomation:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    Select row WorkflowFlowAutomation:Opportunity_Creation_Automation    tag=label    partial_match=False
    # row 26  unknown  "Select row FlowDefinition:Opportunity_Creation_Automation"  [accepted]  -- member of bucket b2
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    Select row FlowDefinition:Opportunity_Creation_Automation    tag=label    partial_match=False
    # row 28  unknown  "Source"  [accepted]  -- 3 of 4 same-shape controls (bucket b3)
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    source    tag=cds-select-input    anchor=2    partial_match=False
    # row 29  unknown  "Select a date"  [accepted]  -- member of bucket b3
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    Select a date    tag=cds-select-input    partial_match=False
    # row 30  unknown  "Last modified by"  [accepted]  -- member of bucket b3
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    modifiedBy    tag=cds-select-input    anchor=2    partial_match=False
    # row 31  unknown  "Metadata Type"  [accepted]  -- member of bucket b3
    GoTo    https://na.devops.copado.com/en/commit/a1v7Q000001LJnRQAW
    VerifyText    Last modified by    timeout=30
    ClickItem    types    tag=cds-select-input    anchor=2    partial_match=False

    # ===== 3 chrome controls (nav bar, search, global actions) reviewed once for this org; --include-chrome to export them =====

    # ===== not exported: containers / hidden / no keyword =====
    # row 3  button  "None"  [accepted]  -- a button is actuated by a click rung (ClickText / ClickItem), not filled or asserted as a value.
    # row 5  input_field  "None"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b7)  -- no keyword
    # row 7  input_field  "None"  [unreviewed]  -- member of bucket b7  -- no keyword
    # row 11  checkbox  "None"  [accepted]  -- 3 of 5 same-shape controls (bucket b1)  -- no keyword
    # row 21  checkbox  "None"  [accepted]  -- member of bucket b1  -- checkbox routes to ClickCheckbox, but this control has no resolvable label -- the keyword cannot target it
    # row 23  checkbox  "None"  [accepted]  -- member of bucket b1  -- checkbox routes to ClickCheckbox, but this control has no resolvable label -- the keyword cannot target it
    # row 25  checkbox  "None"  [accepted]  -- member of bucket b1  -- checkbox routes to ClickCheckbox, but this control has no resolvable label -- the keyword cannot target it
    # row 27  checkbox  "None"  [accepted]  -- member of bucket b1  -- checkbox routes to ClickCheckbox, but this control has no resolvable label -- the keyword cannot target it
    # row 32  button  "None"  [accepted]  -- 3 of 3 same-shape controls (bucket b5)  -- a button is actuated by a click rung (ClickText / ClickItem), not filled or asserted as a value.
    # row 33  button  "None"  [accepted]  -- member of bucket b5  -- a button is actuated by a click rung (ClickText / ClickItem), not filled or asserted as a value.
    # row 34  button  "None"  [accepted]  -- member of bucket b5  -- a button is actuated by a click rung (ClickText / ClickItem), not filled or asserted as a value.
