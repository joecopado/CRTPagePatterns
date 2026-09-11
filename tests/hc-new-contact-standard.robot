*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/o/Contact/new
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Object Page    Contact    new
    # Contact Owner  (1 of 19 same-shape controls -- the same lines with the other label)
    VerifyField    Contact Owner    <value>
    # Phone  (1 of 13 same-shape controls -- the same lines with the other label)
    # keyword form measured CAUGHT-BUG live (QWebInstanceDoesNotExistError: Found 1 elements. Given anchor was 2) -- see the XPath form
    # TypeText    Phone    GZREV Phone 2    anchor=2
    # Salutation  (1 of 2 same-shape controls -- the same lines with the other label)
    PickList    Salutation    GZREV Salutation
    # First Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    First Name    GZREV First Name
    # Account Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    Account Name    GZREV Account Name 1    anchor=1
    # Reports To  (1 of 4 same-shape controls -- the same lines with the other label)
    # keyword form measured CAUGHT-BUG live (QWebInstanceDoesNotExistError: Found 1 elements. Given anchor was 2) -- see the XPath form
    # TypeText    Reports To    GZREV Reports To 2    anchor=2
    # Mailing Street  (1 of 3 same-shape controls -- the same lines with the other label)
    TypeText    Mailing Street    GZREV Mailing Street 1    anchor=1
    # Select a date for Birthdate
    ClickItem    Select a date for Birthdate    tag=button    partial_match=False
    # Save & New -- commits; run it yourself after checking the form:
    # ClickText    Save & New    partial_match=False

XPath form -- /lightning/o/Contact/new
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Object Page    Contact    new
    # Contact Owner  (1 of 19 same-shape controls -- the same lines with the other label)
    # (blank field)
    # Phone  (1 of 13 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@name\="Phone"]    GZREV Phone 2
    # Salutation  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="salutation"]
    ClickText    GZREV Salutation
    # First Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@name\="firstName"]    GZREV First Name
    # Account Name  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@aria-label\="Account Name"]    GZREV Account Name 1
    # Reports To  (1 of 4 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//input[@aria-label\="Reports To"]    GZREV Reports To 2
    # Mailing Street  (1 of 3 same-shape controls -- the same lines with the other label)
    TypeText    xpath\=//label[normalize-space(.)\="Mailing Street"]/following::textarea[1]    GZREV Mailing Street 1
    # Select a date for Birthdate
    ClickElement    xpath\=//button[@title\="Select a date for Birthdate"]
    # Save & New -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="SaveAndNew"]
