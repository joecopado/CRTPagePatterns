*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/Contract/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Contract    ContractNumber    00000101
    # Navigation Mode
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Click Table Cell    Navigation Mode    anchor=1
    # Name  (1 of 10 same-shape controls -- the same lines with the other label)
    #   (1 of 6 same-shape controls -- the same lines with the other label)
    Click Table Cell
    # Start Date  (1 of 21 same-shape controls -- the same lines with the other label)
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Start Date
    # Show Actions  (1 of 6 same-shape controls -- the same lines with the other label)
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Show Actions
    # Date
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Date
    # Joseph Garza
    Click Table Cell    Joseph Garza
    # 
    Click Table Cell
    # Slack  (1 of 8 same-shape controls -- the same lines with the other label)
    ClickText    Slack    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Account Name  (1 of 5 same-shape controls -- the same lines with the other label)
    VerifyField    Account Name    <value>
    # In Approval Process  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    In Approval Process    partial_match=False
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button

XPath form -- /lightning/r/Contract/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Contract    ContractNumber    00000101
    # Navigation Mode
    ClickElement    xpath\=(//*[normalize-space(text())\="New"]/following::lightning-datatable)[1]
    # Name  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//th[@aria-label\="Name"]
    #   (1 of 6 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="End Date"]/following::a)[1]
    # Start Date  (1 of 21 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Preventive Care Agreement"]/following::td)[1]
    # Show Actions  (1 of 6 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Preventive Care Agreement"]/following::td[normalize-space(.)\="Show Actions"])[1]
    # Date
    ClickElement    xpath\=(//*[normalize-space(text())\="New Value"]/following::th)[1]
    # Joseph Garza
    ClickElement    xpath\=//a[@title\="Joseph Garza"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="New"]/following::table)[1]
    # Slack  (1 of 8 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Delete"]/following::button[@type\="button"])[1]
    # Account Name  (1 of 5 same-shape controls -- the same lines with the other label)
    # (blank field)
    # In Approval Process  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="In Approval Process"]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
