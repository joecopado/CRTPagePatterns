*** Settings ***
Resource                      ../../resources/common.robot
Resource                      ../../resources/garzai_console.robot
Resource                      ../../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 404 steps, 0 controls listed as comments (31 buckets)
*** Test Cases ***
Review /lightning/r/copado__User_Story__c/{id}/view
    # Inline steps: no custom keywords. Authenticates with the suite's own JWT variables, then Generated from docs/recorder/captures/cicd-demo/user-story-record-build-tab.html
    # SECICD -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idCICD}    ${usernameCICD}    ${private_keyCICD}
    JwtLogin
    Open Record Page    copado__User_Story__c    Name    US-0000071
    VerifyText    User Story    timeout=30
    # STATE precondition: the capture behind this table was the Build tab (Deployment Steps live there)
    ClickText    Build    partial_match=False
    VerifyText    Deployment Steps    timeout=15

    # ===== 1. every control resolves (non-mutating) =====
    # row 3  checkbox  "Select 5 items"  [unreviewed]  -- 3 of 6 same-shape controls (bucket b14)
    VerifyElement    xpath\=(//*[normalize-space(text())\="Updated a few seconds ago"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 4  checkbox  "Select Item 1"  [unreviewed]  -- member of bucket b14
    VerifyElement    xpath\=(//*[normalize-space(text())\="Commit Message"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 5  checkbox  "Select Item 2"  [unreviewed]  -- member of bucket b14
    VerifyElement    xpath\=(//*[normalize-space(text())\="ffe1793"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 6  checkbox  "Select Item 3"  [unreviewed]  -- member of bucket b14
    VerifyElement    xpath\=(//*[normalize-space(text())\="12/16/2022, 12:24 PM"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 7  checkbox  "Select Item 4"  [unreviewed]  -- member of bucket b14
    VerifyElement    xpath\=(//*[normalize-space(text())\="3b2cbf4"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 8  checkbox  "Select Item 5"  [unreviewed]  -- member of bucket b14
    VerifyElement    xpath\=(//*[normalize-space(text())\="5696983"]/following::input[@type\="checkbox"])[1]    timeout=5
    # row 182  output_field  "Sprint"  [accepted]  -- 3 of 6 same-shape controls (bucket b16)
    VerifyElement    xpath\=(//*[normalize-space(text())\="Open Pull Request"]/following::records-highlights-details-item)[1]    timeout=5
    # row 185  output_field  "Project"  [accepted]  -- member of bucket b16
    VerifyElement    xpath\=(//*[normalize-space(text())\="CC Sprint 1"]/following::records-highlights-details-item)[1]    timeout=5
    # row 188  output_field  "Release"  [accepted]  -- member of bucket b16
    VerifyElement    xpath\=(//*[normalize-space(text())\="MCDX Feature Project"]/following::records-highlights-details-item)[1]    timeout=5
    # row 191  output_field  "Record Type"  [accepted]  -- member of bucket b16
    VerifyElement    xpath\=(//*[normalize-space(text())\="TDX Release"]/following::records-highlights-details-item)[1]    timeout=5
    # row 192  output_field  "Progress"  [accepted]  -- member of bucket b16
    VerifyElement    xpath\=(//*[normalize-space(text())\="Record Type"]/following::records-highlights-details-item)[1]    timeout=5
    # row 193  output_field  "Status"  [accepted]  -- member of bucket b16
    VerifyElement    xpath\=(//*[normalize-space(text())\="60%"]/following::records-highlights-details-item)[1]    timeout=5
    # row 174  button  "Follow"  [accepted]  -- 3 of 12 same-shape controls (bucket b8)
    VerifyText    Follow    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="More"]/following::button[normalize-space(.)\="Follow"])[1]    timeout=5
    # row 175  button  "Edit"  [accepted]  -- member of bucket b8
    VerifyText    Edit    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="Edit"]    timeout=5
    # row 176  button  "Get Copado Help"  [accepted]  -- member of bucket b8
    VerifyText    Get Copado Help    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__Get_Copado_Help"]    timeout=5
    # row 177  button  "Open Org"  [accepted]  -- member of bucket b8
    VerifyText    Open Org    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Get Copado Help"]/following::button[@type\="button"])[1]    timeout=5
    # row 178  button  "Commit Changes"  [accepted]  -- member of bucket b8
    VerifyText    Commit Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__Commit_Changes"]    timeout=5
    # row 179  button  "Validate Changes"  [accepted]  -- member of bucket b8
    VerifyText    Validate Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__ValidateChanges"]    timeout=5
    # row 180  button  "Open Pull Request"  [accepted]  -- member of bucket b8
    VerifyText    Open Pull Request    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__Open_Pull_Request"]    timeout=5
    # row 181  button  "Show more actions"  [accepted]  -- 3 of 13 same-shape controls (bucket b7)
    VerifyText    Show more actions    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Open Pull Request"]/following::button[@type\="button"])[1]    timeout=5
    # row 184  button  "Preview"  [unreviewed]  -- 3 of 12 same-shape controls (bucket b9)
    VerifyItem    Preview    tag=button    anchor=10    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[10]    timeout=5
    # row 187  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=11    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[11]    timeout=5
    # row 190  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=12    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Last Modified Date"]/following::button[@type\="button"])[1]    timeout=5
    # row 194  iframe  "accessibility title"  [accepted]
    VerifyItem    accessibility title    tag=iframe    partial_match=False    timeout=5
    VerifyElement    xpath\=//iframe[@title\="accessibility title"]    timeout=5
    # row 195  link  "here"  [unreviewed]  -- 3 of 20 same-shape controls (bucket b2)
    VerifyText    here    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Action Required"]/following::a)[1]    timeout=5
    # row 196  link  "Plan"  [unreviewed]  -- 3 of 8 same-shape controls (bucket b13)
    VerifyText    Plan    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab8__item"]    timeout=5
    # row 197  link  "Build"  [unreviewed]  -- member of bucket b13
    VerifyText    Build    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab9__item"]    timeout=5
    # row 198  link  "Test"  [unreviewed]  -- member of bucket b13
    VerifyText    Test    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab10__item"]    timeout=5
    # row 199  link  "Deliver"  [unreviewed]  -- member of bucket b13
    VerifyText    Deliver    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab11__item"]    timeout=5
    # row 200  link  "Related"  [unreviewed]  -- member of bucket b13
    VerifyText    Related    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab12__item"]    timeout=5
    # row 201  button  "Information"  [accepted]  -- member of bucket b8
    VerifyText    Information    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Related"]/following::button)[1]    timeout=5
    # row 202  button  "Help Credential"  [accepted]  -- member of bucket b7
    VerifyText    Help Credential    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Credential"]/following::button[@type\="button"])[1]    timeout=5
    # row 203  button  "Edit Credential"  [accepted]  -- 3 of 5 same-shape controls (bucket b18)
    VerifyElement    xpath\=//button[@title\="Edit Credential"]    timeout=5
    # row 205  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=13    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[13]    timeout=5
    # row 206  button  "Help Environment"  [accepted]  -- member of bucket b7
    VerifyText    Help Environment    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Environment"]/following::button[@type\="button"])[1]    timeout=5
    # row 207  button  "Edit Environment"  [accepted]  -- member of bucket b18
    VerifyElement    xpath\=//button[@title\="Edit Environment"]    timeout=5
    # row 209  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=14    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[14]    timeout=5
    # row 210  button  "Help Platform"  [accepted]  -- member of bucket b7
    VerifyText    Help Platform    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Platform"]/following::button[@type\="button"])[1]    timeout=5
    # row 211  button  "Help Base Branch"  [accepted]  -- member of bucket b7
    VerifyText    Help Base Branch    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Base Branch"]/following::button[@type\="button"])[1]    timeout=5
    # row 212  button  "Edit Base Branch"  [accepted]  -- member of bucket b18
    VerifyElement    xpath\=//button[@title\="Edit Base Branch"]    timeout=5
    # row 213  button  "Edit Developer"  [accepted]  -- member of bucket b18
    VerifyElement    xpath\=//button[@title\="Edit Developer"]    timeout=5
    # row 215  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=15    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[15]    timeout=5
    # row 216  button  "Help View in Git"  [accepted]  -- member of bucket b7
    VerifyText    Help View in Git    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Developer"]/following::button[normalize-space(.)\="Help View in Git"])[1]    timeout=5
    # row 217  link  "feature/US-0000071"  [unreviewed]  -- member of bucket b2
    VerifyText    feature/US-0000071    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Developer"]/following::a[normalize-space(.)\="feature/US-0000071"])[1]    timeout=5
    # row 218  button  "Edit Latest Commit Date"  [accepted]  -- member of bucket b18
    VerifyElement    xpath\=//button[@title\="Edit Latest Commit Date"]    timeout=5
    # row 219  button  "New"  [accepted]  -- member of bucket b8
    VerifyText    New    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="New"]    timeout=5
    # row 220  button  "Order"  [accepted]  -- member of bucket b8
    VerifyText    Order    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Order"]    timeout=5
    # row 221  link  "User Story Commits (5)"  [unreviewed]  -- member of bucket b2
    VerifyText    User Story Commits (5)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//article[@aria-label\="User Story Commits"]//a)[1]    timeout=5
    # row 222  button  "List View Controls"  [unreviewed]  -- member of bucket b9
    VerifyItem    List View Controls    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="List View Controls"]    timeout=5
    # row 223  button  "Refresh"  [unreviewed]  -- member of bucket b9
    VerifyItem    refreshButton    tag=button    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="refreshButton"]    timeout=5
    # row 224  link  "View All User Story Commits"  [unreviewed]  -- member of bucket b2
    VerifyText    View All User Story Commits    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="4c24b49"]/following::a)[1]    timeout=5
    # row 225  link  "User Story Metadata (4)"  [unreviewed]  -- member of bucket b2
    VerifyText    User Story Metadata (4)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-component2[@data-target-selection-name\="force_relatedListSingleContainer20"]//a)[1]    timeout=5
    # row 226  link  "View All User Story Metadata"  [unreviewed]  -- member of bucket b2
    VerifyText    View All User Story Metadata    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="7/20/2023, 9:28 AM"]/following::a)[1]    timeout=5
    # row 227  link  "Overlap Awareness"  [unreviewed]  -- member of bucket b13
    VerifyText    Overlap Awareness    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="flexipage_tab__item"]    timeout=5
    # row 228  link  "User Story Metadata (3+)"  [unreviewed]  -- member of bucket b2
    VerifyText    User Story Metadata (3+)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::a)[1]    timeout=5
    # row 230  button  "Preview"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b25)
    VerifyText    Preview    anchor=16    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::button[@type\="button"])[1]    timeout=5
    # row 231  link  "Casey Pine"  [unreviewed]  -- member of bucket b2
    VerifyText    Casey Pine    anchor=4    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::a[normalize-space(.)\="Casey Pine"])[1]    timeout=5
    # row 232  button  "Show Actions"  [accepted]  -- member of bucket b7
    VerifyText    Show Actions    anchor=19    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::button[normalize-space(.)\="Show Actions"])[1]    timeout=5
    # row 234  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=17    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[17]    timeout=5
    # row 235  link  "Indigo Northeaa"  [unreviewed]  -- member of bucket b2
    VerifyText    Indigo Northeaa    anchor=4    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::a[normalize-space(.)\="Indigo Northeaa"])[1]    timeout=5
    # row 236  button  "Show Actions"  [accepted]  -- member of bucket b7
    VerifyText    Show Actions    anchor=20    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-component2[@data-target-selection-name\="force_relatedListSingleContainer"]//button[@type\="button"])[4]    timeout=5
    # row 238  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=18    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[18]    timeout=5
    # row 239  link  "Indigo Northeaa"  [unreviewed]  -- member of bucket b2
    VerifyText    Indigo Northeaa    anchor=5    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//a[@title\="Indigo Northeaa"])[5]    timeout=5
    # row 240  button  "Show Actions"  [accepted]  -- member of bucket b7
    VerifyText    Show Actions    anchor=21    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-component2[@data-target-selection-name\="force_relatedListSingleContainer"]//button[@type\="button"])[6]    timeout=5
    # row 241  link  "View All User Story Metadata"  [unreviewed]  -- member of bucket b2
    VerifyText    View All User Story Metadata    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-component2[@data-target-selection-name\="force_relatedListSingleContainer"]//a)[8]    timeout=5
    # row 242  button  "Refresh to fetch the latest information from the Pull Request record"  [unreviewed]  -- member of bucket b9
    VerifyItem    Refresh to fetch the latest information from the Pull Request record    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Refresh to fetch the latest information from the Pull Request record"]    timeout=5
    # row 243  button  "View Pull Request"  [accepted]  -- member of bucket b8
    VerifyText    View Pull Request    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Pull Request Details"]/following::button[normalize-space(.)\="View Pull Request"])[1]    timeout=5
    # row 244  link  "Set up OAuth"  [unreviewed]  -- member of bucket b2
    VerifyText    Set up OAuth    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="View Pull Request"]/following::a)[1]    timeout=5
    # row 245  link  "Not approved"  [unreviewed]  -- member of bucket b2
    VerifyText    Not approved    partial_match=False    timeout=5
    VerifyElement    xpath\=//*[normalize-space(text())\="Reviewers:"]/following-sibling::*//a    timeout=5
    # row 246  link  "Relationships"  [unreviewed]  -- member of bucket b13
    VerifyText    Relationships    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab14__item"]    timeout=5
    # row 247  link  "Approval History"  [unreviewed]  -- member of bucket b13
    VerifyText    Approval History    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab15__item"]    timeout=5
    # row 248  link  "Parent User Stories (0)"  [unreviewed]  -- member of bucket b2
    VerifyText    Parent User Stories (0)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Approval History"]/following::a)[1]    timeout=5
    # row 249  button  "Show actions for Parent User Stories"  [accepted]  -- member of bucket b7
    VerifyText    Show actions for Parent User Stories    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Parent User Stories"]/following::button[@type\="button"])[1]    timeout=5
    # row 250  link  "Child User Stories (2)"  [unreviewed]  -- member of bucket b2
    VerifyText    Child User Stories (2)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Parent User Stories"]/following::a)[1]    timeout=5
    # row 251  button  "Show actions for Child User Stories"  [accepted]  -- member of bucket b7
    VerifyText    Show actions for Child User Stories    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Parent User Stories"]/following::button[normalize-space(.)\="Show actions for Child User Stories"])[1]    timeout=5
    # row 253  button  "Preview"  [unreviewed]  -- member of bucket b25
    VerifyText    Preview    anchor=19    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[19]    timeout=5
    # row 254  link  "US-0000747"  [unreviewed]  -- member of bucket b2
    VerifyText    US-0000747    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@title\="US-0000747"]    timeout=5
    # row 255  link  "Jamie Hollow"  [unreviewed]  -- member of bucket b2
    VerifyText    Jamie Hollow    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="US-0000747"]/following::a)[1]    timeout=5
    # row 256  button  "Show Actions"  [accepted]  -- member of bucket b7
    VerifyText    Show Actions    anchor=22    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="US-0000747"]/following::button[@type\="button"])[1]    timeout=5
    # row 258  button  "Preview"  [unreviewed]  -- member of bucket b9
    VerifyItem    Preview    tag=button    anchor=20    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[20]    timeout=5
    # row 259  link  "US-0000751"  [unreviewed]  -- member of bucket b2
    VerifyText    US-0000751    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@title\="US-0000751"]    timeout=5
    # row 260  link  "Jamie Hollow"  [unreviewed]  -- member of bucket b2
    VerifyText    Jamie Hollow    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="US-0000751"]/following::a)[1]    timeout=5
    # row 261  button  "Show Actions"  [accepted]  -- member of bucket b7
    VerifyText    Show Actions    anchor=23    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="US-0000751"]/following::button[@type\="button"])[1]    timeout=5
    # row 262  link  "View All Child User Stories"  [unreviewed]  -- member of bucket b2
    VerifyText    View All Child User Stories    partial_match=False    timeout=5
    VerifyElement    xpath\=(//article[@aria-label\="Child User Stories"]//a)[8]    timeout=5
    # row 263  button  "Dismiss"  [accepted]  -- member of bucket b8
    VerifyText    Dismiss    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Just so you know"]/following::button)[1]    timeout=5
    # row 272  link  "Sales DX Dev 2 Sales DX Dev 2 - 0 ahead, 9 behind"  [unreviewed]  -- 3 of 4 same-shape controls (bucket b20)
    VerifyText    Sales DX Dev 2 Sales DX Dev 2 - 0 ahead, 9 behind    partial_match=False    timeout=5
    # row 273  link  "Sales DX Int Sales DX Int"  [unreviewed]  -- member of bucket b20
    VerifyText    Sales DX Int Sales DX Int    partial_match=False    timeout=5
    # row 274  link  "MCDX-UAT MCDX-UAT"  [unreviewed]  -- member of bucket b20
    VerifyText    MCDX-UAT MCDX-UAT    partial_match=False    timeout=5
    # row 275  link  "MCDX Production MCDX Production"  [unreviewed]  -- member of bucket b20
    VerifyText    MCDX Production MCDX Production    partial_match=False    timeout=5

    # ===== 2. fill controls, each read back (nothing is saved) =====
    # row 3  checkbox  "Select 5 items"  [unreviewed]  -- 3 of 6 same-shape controls (bucket b14)
    Click Table Cell    Select 5 items    anchor=1
    # row 4  checkbox  "Select Item 1"  [unreviewed]  -- member of bucket b14
    Click Table Cell    Select Item 1    anchor=2
    # row 5  checkbox  "Select Item 2"  [unreviewed]  -- member of bucket b14
    Click Table Cell    Select Item 2    anchor=3
    # row 6  checkbox  "Select Item 3"  [unreviewed]  -- member of bucket b14
    Click Table Cell    Select Item 3    anchor=4
    # row 7  checkbox  "Select Item 4"  [unreviewed]  -- member of bucket b14
    Click Table Cell    Select Item 4    anchor=5
    # row 8  checkbox  "Select Item 5"  [unreviewed]  -- member of bucket b14
    Click Table Cell    Select Item 5    anchor=6
    # row 182  output_field  "Sprint"  [accepted]  -- 3 of 6 same-shape controls (bucket b16)
    VerifyField    Sprint    CC Sprint 1    partial_match=True
    # row 185  output_field  "Project"  [accepted]  -- member of bucket b16
    VerifyField    Project    <value>
    # row 188  output_field  "Release"  [accepted]  -- member of bucket b16
    VerifyField    Release    <value>
    # row 191  output_field  "Record Type"  [accepted]  -- member of bucket b16
    VerifyField    Record Type    <value>
    # row 192  output_field  "Progress"  [accepted]  -- member of bucket b16
    VerifyField    Progress    <value>
    # row 193  output_field  "Status"  [accepted]  -- member of bucket b16
    VerifyField    Status    <value>

    # ===== 3. clicks, each preceded by a fresh GoTo (many of these navigate away) =====
    # row 174  button  "Follow"  [accepted]  -- 3 of 12 same-shape controls (bucket b8)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Follow    partial_match=False
    # row 175  button  "Edit"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Edit    anchor=1    partial_match=False
    # row 176  button  "Get Copado Help"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Get Copado Help    partial_match=False
    # row 177  button  "Open Org"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Open Org    partial_match=False
    # row 178  button  "Commit Changes"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Commit Changes    partial_match=False
    # row 179  button  "Validate Changes"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Validate Changes    partial_match=False
    # row 180  button  "Open Pull Request"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Open Pull Request    partial_match=False
    # row 181  button  "Show more actions"  [accepted]  -- 3 of 13 same-shape controls (bucket b7)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show more actions    partial_match=False
    # row 184  button  "Preview"  [unreviewed]  -- 3 of 12 same-shape controls (bucket b9)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=10    partial_match=False
    # row 187  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=11    partial_match=False
    # row 190  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=12    partial_match=False
    # row 194  iframe  "accessibility title"  [accepted]
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    accessibility title    tag=iframe    partial_match=False
    # row 195  link  "here"  [unreviewed]  -- 3 of 20 same-shape controls (bucket b2)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    here    partial_match=False
    # row 196  link  "Plan"  [unreviewed]  -- 3 of 8 same-shape controls (bucket b13)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Plan    partial_match=False
    # row 197  link  "Build"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Build    anchor=1    partial_match=False
    # row 198  link  "Test"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Test    anchor=1    partial_match=False
    # row 199  link  "Deliver"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Deliver    partial_match=False
    # row 200  link  "Related"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Related    partial_match=False
    # row 201  button  "Information"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Information    anchor=1    partial_match=False
    # row 202  button  "Help Credential"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Help Credential    partial_match=False
    # row 203  button  "Edit Credential"  [accepted]  -- 3 of 5 same-shape controls (bucket b18)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Edit Credential    tag=button
    # row 205  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=13    partial_match=False
    # row 206  button  "Help Environment"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Help Environment    partial_match=False
    # row 207  button  "Edit Environment"  [accepted]  -- member of bucket b18
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Edit Environment    tag=button
    # row 209  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=14    partial_match=False
    # row 210  button  "Help Platform"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Help Platform    partial_match=False
    # row 211  button  "Help Base Branch"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Help Base Branch    partial_match=False
    # row 212  button  "Edit Base Branch"  [accepted]  -- member of bucket b18
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Edit Base Branch    tag=button
    # row 213  button  "Edit Developer"  [accepted]  -- member of bucket b18
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Edit Developer    tag=button
    # row 215  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=15    partial_match=False
    # row 216  button  "Help View in Git"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Help View in Git    partial_match=False
    # row 217  link  "feature/US-0000071"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    feature/US-0000071    partial_match=False
    # row 218  button  "Edit Latest Commit Date"  [accepted]  -- member of bucket b18
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Edit Latest Commit Date    tag=button
    # row 219  button  "New"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    New    partial_match=False
    # row 220  button  "Order"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Order    partial_match=False
    # row 221  link  "User Story Commits (5)"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    User Story Commits (5)    partial_match=False
    # row 222  button  "List View Controls"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    List View Controls    tag=button    partial_match=False
    # row 223  button  "Refresh"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    refreshButton    tag=button    anchor=1    partial_match=False
    # row 224  link  "View All User Story Commits"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    View All User Story Commits    partial_match=False
    # row 225  link  "User Story Metadata (4)"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    User Story Metadata (4)    partial_match=False
    # row 226  link  "View All User Story Metadata"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    View All User Story Metadata    anchor=1    partial_match=False
    # row 227  link  "Overlap Awareness"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Overlap Awareness    partial_match=False
    # row 228  link  "User Story Metadata (3+)"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    User Story Metadata (3+)    partial_match=False
    # row 230  button  "Preview"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b25)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Preview    anchor=16    partial_match=False
    # row 231  link  "Casey Pine"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Casey Pine    anchor=4    partial_match=False
    # row 232  button  "Show Actions"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show Actions    anchor=19    partial_match=False
    # row 234  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=17    partial_match=False
    # row 235  link  "Indigo Northeaa"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Indigo Northeaa    anchor=4    partial_match=False
    # row 236  button  "Show Actions"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show Actions    anchor=20    partial_match=False
    # row 238  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=18    partial_match=False
    # row 239  link  "Indigo Northeaa"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Indigo Northeaa    anchor=5    partial_match=False
    # row 240  button  "Show Actions"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show Actions    anchor=21    partial_match=False
    # row 241  link  "View All User Story Metadata"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    View All User Story Metadata    anchor=2    partial_match=False
    # row 242  button  "Refresh to fetch the latest information from the Pull Request record"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Refresh to fetch the latest information from the Pull Request record    tag=button    partial_match=False
    # row 243  button  "View Pull Request"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    View Pull Request    partial_match=False
    # row 244  link  "Set up OAuth"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Set up OAuth    partial_match=False
    # row 245  link  "Not approved"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Not approved    partial_match=False
    # row 246  link  "Relationships"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Relationships    partial_match=False
    # row 247  link  "Approval History"  [unreviewed]  -- member of bucket b13
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Approval History    partial_match=False
    # row 248  link  "Parent User Stories (0)"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Parent User Stories (0)    partial_match=False
    # row 249  button  "Show actions for Parent User Stories"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show actions for Parent User Stories    partial_match=False
    # row 250  link  "Child User Stories (2)"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Child User Stories (2)    partial_match=False
    # row 251  button  "Show actions for Child User Stories"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show actions for Child User Stories    partial_match=False
    # row 253  button  "Preview"  [unreviewed]  -- member of bucket b25
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Preview    anchor=19    partial_match=False
    # row 254  link  "US-0000747"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    US-0000747    partial_match=False
    # row 255  link  "Jamie Hollow"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Jamie Hollow    anchor=1    partial_match=False
    # row 256  button  "Show Actions"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show Actions    anchor=22    partial_match=False
    # row 258  button  "Preview"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickItem    Preview    tag=button    anchor=20    partial_match=False
    # row 259  link  "US-0000751"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    US-0000751    partial_match=False
    # row 260  link  "Jamie Hollow"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Jamie Hollow    anchor=2    partial_match=False
    # row 261  button  "Show Actions"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Show Actions    anchor=23    partial_match=False
    # row 262  link  "View All Child User Stories"  [unreviewed]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    View All Child User Stories    partial_match=False
    # row 263  button  "Dismiss"  [accepted]  -- member of bucket b8
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Dismiss    partial_match=False
    # row 272  link  "Sales DX Dev 2 Sales DX Dev 2 - 0 ahead, 9 behind"  [unreviewed]  -- 3 of 4 same-shape controls (bucket b20)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Sales DX Dev 2 Sales DX Dev 2 - 0 ahead, 9 behind    partial_match=False
    # row 273  link  "Sales DX Int Sales DX Int"  [unreviewed]  -- member of bucket b20
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    Sales DX Int Sales DX Int    partial_match=False
    # row 274  link  "MCDX-UAT MCDX-UAT"  [unreviewed]  -- member of bucket b20
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    MCDX-UAT MCDX-UAT    partial_match=False
    # row 275  link  "MCDX Production MCDX Production"  [unreviewed]  -- member of bucket b20
    GoTo    https://copado-se-demo.lightning.force.com/lightning/r/copado__User_Story__c/a1v7Q000001LJnRQAW/view
    VerifyText    Home    timeout=30
    ClickText    MCDX Production MCDX Production    partial_match=False

    # ===== 29 chrome controls (nav bar, search, global actions) reviewed once for this org; --include-chrome to export them =====

    # ===== not exported: containers / hidden / no keyword =====
    # row 0  datatable  "Navigation Mode Show Name column actions Show Type column actions Show Execution Sequence column act"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b21)  -- no keyword
    # row 1  datatable  "Select 5 items"  [unreviewed]  -- no keyword
    # row 2  datatable  "Navigation Mode Preview Show Actions Preview Show Actions Preview Show Actions Preview Show Actions"  [unreviewed]  -- member of bucket b21  -- no keyword
    # row 9  column_header  "Row Number"  [accepted]  -- 3 of 17 same-shape controls (bucket b4)  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 10  column_header  "Name"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 11  button  "Show Name column actions"  [accepted]  -- 3 of 17 same-shape controls (bucket b5)  -- no keyword
    # row 12  column_header  "Type"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 13  button  "Show Type column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 14  column_header  "Execution Sequence"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 15  button  "Show Execution Sequence column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 16  column_header  "Actions"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 17  link  "Notify Users of Lockout"  [accepted]  -- 3 of 19 same-shape controls (bucket b3)  -- no keyword
    # row 18  table_cell  "Type"  [accepted]  -- 3 of 30 same-shape controls (bucket b0)  -- no keyword
    # row 19  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 20  table_cell  "Show actions"  [accepted]  -- 3 of 20 same-shape controls (bucket b1)  -- no keyword
    # row 21  button  "Show actions"  [accepted]  -- 3 of 15 same-shape controls (bucket b6)  -- no keyword
    # row 22  link  "Run Account Updater Record Creation Script"  [accepted]  -- member of bucket b3  -- no keyword
    # row 23  table_cell  "Type"  [accepted]  -- member of bucket b0  -- no keyword
    # row 24  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 25  table_cell  "Show actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 26  button  "Show actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 27  link  "Update CPQ Config"  [accepted]  -- member of bucket b3  -- no keyword
    # row 28  table_cell  "Type"  [accepted]  -- member of bucket b0  -- no keyword
    # row 29  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 30  table_cell  "Show actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 31  button  "Show actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 32  link  "Post Deploy Automation"  [accepted]  -- member of bucket b3  -- no keyword
    # row 33  table_cell  "Type"  [accepted]  -- member of bucket b0  -- no keyword
    # row 34  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 35  table_cell  "Show actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 36  button  "Show actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 37  link  "Update Public Groups"  [accepted]  -- member of bucket b3  -- no keyword
    # row 38  table_cell  "Type"  [accepted]  -- member of bucket b0  -- no keyword
    # row 39  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 40  table_cell  "Show actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 41  button  "Show actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 42  link  "Update CPQ Config"  [accepted]  -- member of bucket b3  -- no keyword
    # row 43  table_cell  "Type"  [accepted]  -- member of bucket b0  -- no keyword
    # row 44  table_cell  "Execution Sequence"  [accepted]  -- member of bucket b0  -- no keyword
    # row 45  table_cell  "Show actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 46  button  "Show actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 47  column_header  "Row Number"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 48  table_cell  "Choose a Row Select 5 items"  [accepted]  -- no keyword
    # row 49  column_header  "User Story Commit: US Commit"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 50  button  "User Story Commit: US Commit"  [accepted]  -- 3 of 5 same-shape controls (bucket b17)  -- no keyword
    # row 51  button  "Show User Story Commit: US Commit column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 52  column_header  "User Story Commit: Created By"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 53  button  "User Story Commit: Created By"  [accepted]  -- member of bucket b17  -- no keyword
    # row 54  button  "Show User Story Commit: Created By column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 55  column_header  "Commit Date"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 56  button  "Commit Date"  [accepted]  -- member of bucket b17  -- no keyword
    # row 57  button  "Show Commit Date column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 58  column_header  "View in Git"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 59  button  "View in Git"  [accepted]  -- member of bucket b17  -- no keyword
    # row 60  button  "Show View in Git column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 61  column_header  "Commit Message"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 62  button  "Commit Message"  [accepted]  -- member of bucket b17  -- no keyword
    # row 63  button  "Show Commit Message column actions"  [accepted]  -- member of bucket b5  -- no keyword
    # row 64  column_header  "Action"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 65  table_cell  "Select Item 1"  [accepted]  -- member of bucket b1  -- no keyword
    # row 66  link  "None"  [accepted]  -- 3 of 10 same-shape controls (bucket b12)  -- no keyword
    # row 67  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 68  link  "Casey Pine"  [accepted]  -- member of bucket b3  -- no keyword
    # row 69  table_cell  "Commit Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 70  link  "ffe1793"  [accepted]  -- member of bucket b3  -- no keyword
    # row 71  table_cell  "Commit Message"  [accepted]  -- member of bucket b0  -- no keyword
    # row 72  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 73  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 74  table_cell  "Select Item 2"  [accepted]  -- member of bucket b1  -- no keyword
    # row 75  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 76  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 77  link  "Indigo Northeaa"  [accepted]  -- member of bucket b3  -- no keyword
    # row 78  table_cell  "Commit Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 79  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 80  table_cell  "Commit Message"  [accepted]  -- member of bucket b0  -- no keyword
    # row 81  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 82  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 83  table_cell  "Select Item 3"  [accepted]  -- member of bucket b1  -- no keyword
    # row 84  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 85  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 86  link  "Emery Brooka"  [accepted]  -- member of bucket b3  -- no keyword
    # row 87  table_cell  "Commit Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 88  link  "3b2cbf4"  [accepted]  -- member of bucket b3  -- no keyword
    # row 89  table_cell  "Commit Message"  [accepted]  -- member of bucket b0  -- no keyword
    # row 90  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 91  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 92  table_cell  "Select Item 4"  [accepted]  -- member of bucket b1  -- no keyword
    # row 93  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 94  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 95  link  "Emery Brooka"  [accepted]  -- member of bucket b3  -- no keyword
    # row 96  table_cell  "Commit Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 97  link  "5696983"  [accepted]  -- member of bucket b3  -- no keyword
    # row 98  table_cell  "Commit Message"  [accepted]  -- member of bucket b0  -- no keyword
    # row 99  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 100  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 101  table_cell  "Select Item 5"  [accepted]  -- member of bucket b1  -- no keyword
    # row 102  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 103  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 104  link  "Emery Brooka"  [accepted]  -- member of bucket b3  -- no keyword
    # row 105  table_cell  "Commit Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 106  link  "4c24b49"  [accepted]  -- member of bucket b3  -- no keyword
    # row 107  table_cell  "Commit Message"  [accepted]  -- member of bucket b0  -- no keyword
    # row 108  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 109  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 110  column_header  "User Story Metadata Name"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 111  column_header  "Status Icon"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 112  column_header  "Last Modified By"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 113  column_header  "Last Modified Date"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 114  column_header  "Action"  [accepted]  -- member of bucket b4  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 115  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 116  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 117  table_cell  "Status Icon"  [accepted]  -- member of bucket b0  -- no keyword
    # row 118  link  "Casey Pine"  [accepted]  -- member of bucket b3  -- no keyword
    # row 119  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 120  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 121  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 122  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 123  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 124  table_cell  "Status Icon"  [accepted]  -- member of bucket b0  -- no keyword
    # row 125  link  "Indigo Northeaa"  [accepted]  -- member of bucket b3  -- no keyword
    # row 126  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 127  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 128  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 129  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 130  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 131  table_cell  "Status Icon"  [accepted]  -- member of bucket b0  -- no keyword
    # row 132  link  "Indigo Northeaa"  [accepted]  -- member of bucket b3  -- no keyword
    # row 133  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 134  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 135  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 136  link  "None"  [accepted]  -- member of bucket b12  -- no keyword
    # row 137  button  "Preview"  [accepted]  -- member of bucket b5  -- no keyword
    # row 138  table_cell  "Status Icon"  [accepted]  -- member of bucket b0  -- no keyword
    # row 139  link  "Casey Pine"  [accepted]  -- member of bucket b3  -- no keyword
    # row 140  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b0  -- no keyword
    # row 141  table_cell  "Show Actions"  [accepted]  -- member of bucket b1  -- no keyword
    # row 142  button  "Show Actions"  [accepted]  -- member of bucket b6  -- no keyword
    # row 143  native_table  "Show Name column actions Show Type column actions Show Execution Sequence column actions Show action"  [unreviewed]  -- 2 of 2 same-shape controls (bucket b22)  -- no keyword
    # row 144  native_table  "Select 5 items"  [accepted]  -- no keyword
    # row 145  native_table  "Preview Show Actions Preview Show Actions Preview Show Actions Preview Show Actions"  [unreviewed]  -- member of bucket b22  -- no keyword
    # row 183  link  "None"  [accepted]  -- 3 of 11 same-shape controls (bucket b11)  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 186  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 189  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 204  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 208  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 214  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 229  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 233  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 237  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 252  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 257  link  "None"  [accepted]  -- member of bucket b11  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 265  custom_component  "None"  [accepted]  -- 2 of 2 same-shape controls (bucket b26)  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 266  custom_component  "None"  [accepted]  -- member of bucket b26  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 267  custom_component  "None"  [accepted]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 268  custom_component  "None"  [unreviewed]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 269  custom_component  "None"  [unreviewed]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 270  custom_component  "None"  [unreviewed]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 271  custom_component  "None"  [unreviewed]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
