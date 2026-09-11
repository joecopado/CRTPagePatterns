*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/n/Zoo_Nightmare_Inputs
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    GoTo    ${login_url}/lightning/n/Zoo_Nightmare_Inputs
    # Contract Term  (1 of 6 same-shape controls -- the same lines with the other label)
    # no keyword reaches this control (measured live) -- see the XPath form
    # Amount  (1 of 9 same-shape controls -- the same lines with the other label)
    TypeText    Amount    12345    anchor=2
    # Add Line  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Add Line    anchor=1    partial_match=False
    # Save -- commits; run it yourself after checking the form:
    # ClickText    Save    anchor=1    partial_match=False
    # Territory  (1 of 2 same-shape controls -- the same lines with the other label)
    DropDown    Territory    Southwest
    # Product Lines Covered
    ClickElement    xpath\=(//*[normalize-space(text())\="Product Lines Covered"]/following::input[@type\="text"])[1]
    ClickText    Agentforce
    # Support Tier
    ClickElement    xpath\=(//*[normalize-space(text())\="Support Tier"]/following::input[@type\="text"])[1]
    ClickText    Premier Success
    # Entitled Services
    ClickText    Health Check    partial_match=False
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]

XPath form -- /lightning/n/Zoo_Nightmare_Inputs
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    GoTo    ${login_url}/lightning/n/Zoo_Nightmare_Inputs
    # Contract Term  (1 of 6 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=(//c-zoo-nightmare-inputs//input[@type\="text"])[2]    24
    # Amount  (1 of 9 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//*[normalize-space(text())\="Negotiated Discount"]/following-sibling::*//input[@type\="text"]    12345
    # Add Line  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button[normalize-space(.)\="Add Line"])[1]
    # Save -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button[normalize-space(.)\="Save"])[1]
    # Territory  (1 of 2 same-shape controls -- the same lines with the other label)
    DropDown    xpath\=(//*[normalize-space(text())\="Territory & Coverage"]/following::select)[1]    Southwest
    # Product Lines Covered
    ClickElement    xpath\=(//*[normalize-space(text())\="Product Lines Covered"]/following::input[@type\="text"])[1]
    ClickText    Agentforce
    # Support Tier
    ClickElement    xpath\=(//*[normalize-space(text())\="Support Tier"]/following::input[@type\="text"])[1]
    ClickText    Premier Success
    # Entitled Services
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
