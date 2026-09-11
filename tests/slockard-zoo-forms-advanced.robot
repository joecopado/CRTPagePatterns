*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/n/Zoo_Forms_Advanced
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Forms_Advanced
    # Account Name  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    TypeText    Account Name    GZREV Account Name
    # Industry  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    PickList    Industry    Technology
    # Phone
    TypeText    Phone    GZREV Phone
    # Website
    TypeText    Website    GZREV Website
    # Save Account -- commits; run it yourself after checking the form:
    # ClickText    Save Account    partial_match=False
    # Country
    PickList    Country    USA
    # State
    PickList    State    Texas
    # Deal Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    Deal Name    GZREV Deal Name 1    anchor=1
    # Amount
    TypeText    Amount    12345
    # Owner Name
    TypeText    Owner Name    GZREV Owner Name
    # Deal Info - Current Stage  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Deal Info - Current Stage    partial_match=False
    # Contact - Stage Not Started
    ClickText    Contact - Stage Not Started    partial_match=False
    # Review - Stage Not Started
    ClickText    Review - Stage Not Started    partial_match=False
    # Deal Name
    # no keyword reaches this control (measured live) -- see the XPath form
    # Back  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Back    partial_match=False
    # Next
    ClickText    Next    partial_match=False

XPath form -- /lightning/n/Zoo_Forms_Advanced
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Forms_Advanced
    # Account Name  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@name\="Name"]    GZREV Account Name
    # Industry  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Industry"]
    ClickText    Technology
    # Phone
    TypeText    xpath\=//input[@name\="Phone"]    GZREV Phone
    # Website
    TypeText    xpath\=//input[@name\="Website"]    GZREV Website
    # Save Account -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//*[normalize-space(text())\="Website"]/following::button[@type\="submit"])[1]
    # Country
    ClickElement    xpath\=//button[@aria-label\="Country"]
    ClickText    USA
    # State
    ClickElement    xpath\=//button[@aria-label\="State"]
    ClickText    Texas
    # Deal Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@aria-label\="Deal Name"]    GZREV Deal Name 1
    # Amount
    TypeText    xpath\=//input[@aria-label\="Amount"]    12345
    # Owner Name
    TypeText    xpath\=//input[@name\="zoo_owner_name"]    GZREV Owner Name
    # Deal Info - Current Stage  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[.//text()[normalize-space(.)\="Deal Info - Current Stage"]]
    # Contact - Stage Not Started
    ClickElement    xpath\=//a[.//text()[normalize-space(.)\="Contact - Stage Not Started"]]
    # Review - Stage Not Started
    ClickElement    xpath\=//a[.//text()[normalize-space(.)\="Review - Stage Not Started"]]
    # Deal Name
    TypeText    xpath\=//label[normalize-space(.)\="Deal Name"]/following::input[1]    GZREV Deal Name 2
    # Back  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Review"]/following::button[@type\="button"])[1]
    # Next
    ClickElement    xpath\=(//*[normalize-space(text())\="Back"]/following::button[@type\="button"])[1]
