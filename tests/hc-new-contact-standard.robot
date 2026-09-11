*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 13 steps, 0 controls listed as comments (10 buckets)

*** Test Cases ***
Keyword form -- /lightning/o/Contact/new
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Object Page    Contact    new
    # Contact Owner  (3 of 19 same-shape controls shown; the others take the same lines with their own label)
    # Contact Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone
    # Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    # keyword form measured CAUGHT-BUG live (QWebInstanceDoesNotExistError: Found 1 elements. Given anchor was 2) -- see the XPath form
    # TypeText    Phone    GZREV Phone 2    anchor=2
    # * Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Salutation  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    PickList    Salutation    GZREV Salutation
    # First Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    First Name    GZREV First Name
    # Last Name
    TypeText    Last Name    GZREV Last Name
    # Mobile
    # keyword form measured CAUGHT-BUG live (inherited from representative row 24: QWebInstanceDoesNotExistError: Found 1 elements. Gi…) -- see the XPath form
    # TypeText    Mobile    GZREV Mobile 2    anchor=2
    # Account Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    Account Name    GZREV Account Name 1    anchor=1
    # Email
    # keyword form measured CAUGHT-BUG live (inherited from representative row 24: QWebInstanceDoesNotExistError: Found 1 elements. Gi…) -- see the XPath form
    # TypeText    Email    GZREV Email 2    anchor=2
    # Reports To  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    # keyword form measured CAUGHT-BUG live (QWebInstanceDoesNotExistError: Found 1 elements. Given anchor was 2) -- see the XPath form
    # TypeText    Reports To    GZREV Reports To 2    anchor=2
    # Address Search
    TypeText    Address Search    GZREV Address Search 1    anchor=1
    # Mailing Country
    TypeText    Mailing Country    GZREV Mailing Country 1    anchor=1
    # Mailing Street  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    TypeText    Mailing Street    GZREV Mailing Street 1    anchor=1
    # Mailing City
    TypeText    Mailing City    GZREV Mailing City 1    anchor=1
    # Address Search
    # keyword form measured CAUGHT-BUG live (inherited from representative row 38: QWebInstanceDoesNotExistError: Found 1 elements. Gi…) -- see the XPath form
    # TypeText    Address Search    GZREV Address Search 2    anchor=2
    # Other Country
    # keyword form measured CAUGHT-BUG live (inherited from representative row 38: QWebInstanceDoesNotExistError: Found 1 elements. Gi…) -- see the XPath form
    # TypeText    Other Country    GZREV Other Country 2    anchor=2
    # Other Street
    TypeText    Other Street    GZREV Other Street 2    anchor=2
    # Lead Source
    PickList    Lead Source    GZREV Lead Source 2
    # Select a date for Birthdate
    ClickItem    Select a date for Birthdate    tag=button    partial_match=False
    # Description
    TypeText    Description    GZREV Description 2    anchor=2
    # Save & New -- commits; run it yourself after checking the form:
    # ClickText    Save & New    partial_match=False
    # Save -- commits; run it yourself after checking the form:
    # ClickText    Save    anchor=1    partial_match=False
    # Dismiss
    ClickText    Dismiss    partial_match=False

XPath form -- /lightning/o/Contact/new
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Object Page    Contact    new
    # Contact Owner  (3 of 19 same-shape controls shown; the others take the same lines with their own label)
    # Contact Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone
    # Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@name\="Phone"]    GZREV Phone 2
    # * Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Salutation  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="salutation"]
    ClickText    GZREV Salutation
    # First Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@name\="firstName"]    GZREV First Name
    # Last Name
    TypeText    xpath\=//input[@name\="lastName"]    GZREV Last Name
    # Mobile
    TypeText    xpath\=//input[@name\="MobilePhone"]    GZREV Mobile 2
    # Account Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@aria-label\="Account Name"]    GZREV Account Name 1
    # Email
    TypeText    xpath\=//input[@name\="Email"]    GZREV Email 2
    # Reports To  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//input[@aria-label\="Reports To"]    GZREV Reports To 2
    # Address Search
    TypeText    xpath\=(//*[normalize-space(text())\="Mailing Address"]/following::input[@type\="text"])[1]    GZREV Address Search 1
    # Mailing Country
    TypeText    xpath\=//input[@aria-label\="Mailing Country"]    GZREV Mailing Country 1
    # Mailing Street  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    TypeText    xpath\=//label[normalize-space(.)\="Mailing Street"]/following::textarea[1]    GZREV Mailing Street 1
    # Mailing City
    TypeText    xpath\=//label[normalize-space(.)\="Mailing City"]/following::input[1]    GZREV Mailing City 1
    # Address Search
    TypeText    xpath\=(//*[normalize-space(text())\="Other Address"]/following::input[@type\="text"])[1]    GZREV Address Search 2
    # Other Country
    TypeText    xpath\=//input[@aria-label\="Other Country"]    GZREV Other Country 2
    # Other Street
    TypeText    xpath\=//label[normalize-space(.)\="Other Street"]/following::textarea[1]    GZREV Other Street 2
    # Lead Source
    ClickElement    xpath\=//button[@aria-label\="Lead Source"]
    ClickText    GZREV Lead Source 2
    # Select a date for Birthdate
    ClickElement    xpath\=//button[@title\="Select a date for Birthdate"]
    # Description
    TypeText    xpath\=//label[normalize-space(.)\="Description"]/following::textarea[1]    GZREV Description 2
    # Save & New -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="SaveAndNew"]
    # Save -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="SaveEdit"]
    # Dismiss
    ClickElement    xpath\=(//*[normalize-space(text())\="Just so you know"]/following::button)[1]
