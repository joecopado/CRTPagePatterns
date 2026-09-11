*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/PartyRelationshipGroup/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyRelationshipGroup    Name    Adams Household
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Account  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyField    Account    Adams Household    partial_match=True
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Name  (1 of 14 same-shape controls -- the same lines with the other label)
    VerifyField    Name    Adams Household
    # Edit Name  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Name    tag=button
    # 47 West 13th Street New York, NY 10011 United States
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator 47 West 13th Street New York…) -- see the XPath form
    # ClickText    47 West 13th Street New York, NY 10011 United States    partial_match=False
    # Map of 47 West 13th Street New York NY 10011 United States
    ClickItem    Map of 47 West 13th Street New York NY 10011 United States    tag=iframe    partial_match=False
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False
    # 
    # 

XPath form -- /lightning/r/PartyRelationshipGroup/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyRelationshipGroup    Name    Adams Household
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Account  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyText    Adams Household    anchor=Account
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Party Relationship Group"]/following::a)[1]
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Name  (1 of 14 same-shape controls -- the same lines with the other label)
    VerifyText    Adams Household    anchor=Name
    # Edit Name  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # 47 West 13th Street New York, NY 10011 United States
    ClickElement    xpath\=//a[@aria-label\="47 West 13th Street
New York, NY 10011
United States"]
    # Map of 47 West 13th Street New York NY 10011 United States
    ClickElement    xpath\=//iframe[@title\="Map of 47 West 13th Street New York NY 10011 United States"]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Primary Address"]/following::lightning-formatted-address)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="United States"]/following::lightning-static-map)[1]
