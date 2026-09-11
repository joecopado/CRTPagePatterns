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
    # Account Name  (1 of 3 same-shape controls -- the same lines with the other label)
    TypeText    Account Name    GZREV Account Name
    # Industry  (1 of 4 same-shape controls -- the same lines with the other label)
    PickList    Industry    Technology
    # Save Account -- commits; run it yourself after checking the form:
    # ClickText    Save Account    partial_match=False
    # Deal Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    Deal Name    GZREV Deal Name 1    anchor=1
    # Deal Info - Current Stage  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Deal Info - Current Stage    partial_match=False
    # Deal Name
    # no keyword reaches this control (measured live) -- see the XPath form
    # Back  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Back    partial_match=False

XPath form -- /lightning/n/Zoo_Forms_Advanced
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Forms_Advanced
    # Account Name  (1 of 3 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@name\="Name"]    GZREV Account Name
    # Industry  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Industry"]
    ClickText    Technology
    # Save Account -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=(//*[normalize-space(text())\="Website"]/following::button[@type\="submit"])[1]
    # Deal Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@aria-label\="Deal Name"]    GZREV Deal Name 1
    # Deal Info - Current Stage  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[.//text()[normalize-space(.)\="Deal Info - Current Stage"]]
    # Deal Name
    TypeText    xpath\=//label[normalize-space(.)\="Deal Name"]/following::input[1]    GZREV Deal Name 2
    # Back  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Review"]/following::button[@type\="button"])[1]
