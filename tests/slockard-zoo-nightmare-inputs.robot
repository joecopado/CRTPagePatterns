*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 14 steps, 0 controls listed as comments (11 buckets)

*** Test Cases ***
Keyword form -- /lightning/n/Zoo_Nightmare_Inputs
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Nightmare_Inputs
    # Contract Term  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # no keyword reaches this control (measured live) -- see the XPath form
    # Renewal Notice (days)
    TypeText    Renewal Notice (days)    60
    # Amount
    TypeText    Amount    12345    anchor=List Price
    # Amount  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    TypeText    Amount    12345    anchor=2
    # Amount
    TypeText    Amount    12345    anchor=3
    # Approved Budget
    # no keyword reaches this control (measured live) -- see the XPath form
    # Add Line  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Add Line    anchor=1    partial_match=False
    # Add Line
    ClickText    Add Line    anchor=2    partial_match=False
    # Save -- commits; run it yourself after checking the form:
    # ClickText    Save    anchor=1    partial_match=False
    # Save & New -- commits; run it yourself after checking the form:
    # ClickText    Save & New    partial_match=False
    # Save -- commits; run it yourself after checking the form:
    # ClickText    Save    anchor=2    partial_match=False
    # Territory  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    DropDown    Territory    Southwest
    # Product Lines Covered
    ClickElement    xpath\=(//*[normalize-space(text())\="Product Lines Covered"]/following::input[@type\="text"])[1]
    ClickText    Agentforce
    # Support Tier
    ClickElement    xpath\=(//*[normalize-space(text())\="Support Tier"]/following::input[@type\="text"])[1]
    ClickText    Premier Success
    # Escalation Regions
    DropDown    Escalation Regions    EMEA
    # Entitled Services
    ClickText    Health Check    partial_match=False
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
    # 
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    # 
    # 
    # 

XPath form -- /lightning/n/Zoo_Nightmare_Inputs
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Nightmare_Inputs
    # Contract Term  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=(//c-zoo-nightmare-inputs//input[@type\="text"])[2]    24
    # Renewal Notice (days)
    TypeText    xpath\=(//*[normalize-space(text())\="Renewal Notice (days)"]/following::input[@type\="text"])[1]    60
    # Amount
    TypeText    xpath\=//*[normalize-space(text())\="List Price"]/following-sibling::*//input[@type\="text"]    12345
    # Amount  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//*[normalize-space(text())\="Negotiated Discount"]/following-sibling::*//input[@type\="text"]    12345
    # Amount
    TypeText    xpath\=//*[normalize-space(text())\="Net to Customer"]/following-sibling::*//input[@type\="text"]    12345
    # Approved Budget
    TypeText    xpath\=(//*[normalize-space(text())\="to"]/following::input[@type\="text"])[1]    130000
    # Add Line  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button[normalize-space(.)\="Add Line"])[1]
    # Add Line
    ClickElement    xpath\=(//c-zoo-nightmare-inputs//button)[6]
    # Save -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button[normalize-space(.)\="Save"])[1]
    # Save & New -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button[normalize-space(.)\="Save & New"])[1]
    # Save -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//c-zoo-nightmare-inputs//button[normalize-space(.)\="Save"])[2]
    # Territory  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    DropDown    xpath\=(//*[normalize-space(text())\="Territory & Coverage"]/following::select)[1]    Southwest
    # Product Lines Covered
    ClickElement    xpath\=(//*[normalize-space(text())\="Product Lines Covered"]/following::input[@type\="text"])[1]
    ClickText    Agentforce
    # Support Tier
    ClickElement    xpath\=(//*[normalize-space(text())\="Support Tier"]/following::input[@type\="text"])[1]
    ClickText    Premier Success
    # Escalation Regions
    DropDown    xpath\=(//*[normalize-space(text())\="Escalation Regions"]/following::select)[1]    EMEA
    # Entitled Services
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
    # 
    TypeText    xpath\=(//*[normalize-space(text())\="More"]/following::c-zoo-nightmare-inputs)[1]    GZREV 
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Onsite Schedule"]/following::c-zoo-nightmare-row)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Kickoff Workshop"]/following::c-zoo-nightmare-row)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Discovery Review"]/following::c-zoo-nightmare-row)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Save & New"]/following::c-zoo-nightmare-combos)[1]
