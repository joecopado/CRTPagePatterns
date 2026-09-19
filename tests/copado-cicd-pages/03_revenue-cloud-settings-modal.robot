*** Settings ***
Resource                      ../../resources/common.robot
Resource                      ../../resources/garzai_console.robot
Resource                      ../../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 430 steps, 0 controls listed as comments (30 buckets)
*** Test Cases ***
Review /lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration
    # Inline steps: no custom keywords. Authenticates with the suite's own JWT variables, then Generated from docs/recorder/captures/cicd-demo/user-story-revenue-cloud-settings-modal.html
    # SECICD -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idCICD}    ${usernameCICD}    ${private_keyCICD}
    JwtLogin
    # TRANSITION: the modal is a Lightning quick action (copado_labs__Revenue_Cloud_Deployment_Configuration) reached from the story in the Copado app; its URL becomes /lightning/action/quick/... so it is its own page
    Open Record Page    copado__User_Story__c    Name    US-0001043    app=Copado
    ClickText    Revenue Cloud Settings    partial_match=False
    VerifyText    Revenue Cloud Deployment Configuration    timeout=20
    VerifyText    Search by Label    timeout=30

    # ===== 1. every control resolves (non-mutating) =====
    # row 51  output_field  "Sprint"  [accepted]  -- 3 of 6 same-shape controls (bucket b6)
    VerifyElement    xpath\=(//*[normalize-space(text())\="Run Compliance Scan"]/following::records-highlights-details-item)[1]    timeout=5
    # row 52  output_field  "Project"  [accepted]  -- member of bucket b6
    VerifyElement    xpath\=//records-highlights-details-item[.//*[normalize-space(.)\="Project"]]    timeout=5
    # row 55  output_field  "Release"  [accepted]  -- member of bucket b6
    VerifyElement    xpath\=//records-highlights-details-item[.//*[normalize-space(.)\="Release"]]    timeout=5
    # row 56  output_field  "Record Type"  [accepted]  -- member of bucket b6
    VerifyElement    xpath\=//records-highlights-details-item[.//*[normalize-space(.)\="Record Type"]]    timeout=5
    # row 57  output_field  "Progress"  [accepted]  -- member of bucket b6
    VerifyElement    xpath\=//records-highlights-details-item[.//*[normalize-space(.)\="Progress"]]    timeout=5
    # row 58  output_field  "Status"  [accepted]  -- member of bucket b6
    VerifyElement    xpath\=(//*[normalize-space(text())\="Progress"]/following::records-highlights-details-item)[1]    timeout=5
    # row 138  input_field  "Search by Label"  [accepted]
    VerifyInputElement    Search by Label    anchor=1    timeout=5
    VerifyElement    xpath\=//input[@placeholder\="Search..."]    timeout=5
    # row 139  dropdown  "Last Modified Date"  [accepted]  -- 3 of 3 same-shape controls (bucket b18)
    VerifyText    Last Modified Date    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@aria-label\="Last Modified Date"]    timeout=5
    # row 140  dropdown  "Last Modified By"  [accepted]  -- member of bucket b18
    VerifyText    Last Modified By    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@aria-label\="Last Modified By"]    timeout=5
    # row 141  dropdown  "Status"  [accepted]  -- member of bucket b18
    VerifyText    Status    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@aria-label\="Status"]    timeout=5
    # row 43  button  "Follow"  [accepted]  -- 3 of 19 same-shape controls (bucket b0)
    VerifyText    Follow    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="User Stories"]/following::button[normalize-space(.)\="Follow"])[1]    timeout=5
    # row 44  button  "Edit"  [accepted]  -- member of bucket b0
    VerifyText    Edit    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="Edit"]    timeout=5
    # row 45  button  "Revenue Cloud Settings"  [accepted]  -- member of bucket b0
    VerifyText    Revenue Cloud Settings    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration"]    timeout=5
    # row 46  button  "Commit Changes"  [accepted]  -- member of bucket b0
    VerifyText    Commit Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__Commit_Changes"]    timeout=5
    # row 47  button  "Validate Changes"  [accepted]  -- member of bucket b0
    VerifyText    Validate Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@name\="copado__User_Story__c.copado__ValidateChanges"]    timeout=5
    # row 48  button  "Run CRT Test Suite"  [accepted]  -- member of bucket b0
    VerifyText    Run CRT Test Suite    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Validate Changes"]/following::button[@type\="button"])[1]    timeout=5
    # row 49  button  "Run Compliance Scan"  [accepted]  -- member of bucket b0
    VerifyText    Run Compliance Scan    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Run CRT Test Suite"]/following::button[@type\="button"])[1]    timeout=5
    # row 50  button  "Show more actions"  [accepted]  -- 3 of 16 same-shape controls (bucket b1)
    VerifyText    Show more actions    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Run Compliance Scan"]/following::button[@type\="button"])[1]    timeout=5
    # row 54  button  "Preview"  [accepted]  -- 3 of 11 same-shape controls (bucket b3)
    VerifyItem    Preview    tag=button    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//records-highlights2//button[@title\="Preview"]    timeout=5
    # row 59  iframe  "accessibility title"  [accepted]
    VerifyItem    accessibility title    tag=iframe    partial_match=False    timeout=5
    VerifyElement    xpath\=//iframe[@title\="accessibility title"]    timeout=5
    # row 60  link  "User Story Commit"  [accepted]  -- 3 of 3 same-shape controls (bucket b16)
    VerifyText    User Story Commit    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Progress"]/following::a)[1]    timeout=5
    # row 62  link  "Plan"  [accepted]  -- 3 of 6 same-shape controls (bucket b7)
    VerifyText    Plan    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab3__item"]    timeout=5
    # row 63  link  "Build"  [accepted]  -- member of bucket b7
    VerifyText    Build    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab4__item"]    timeout=5
    # row 64  link  "Test"  [accepted]  -- member of bucket b7
    VerifyText    Test    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab5__item"]    timeout=5
    # row 65  link  "Deliver"  [accepted]  -- member of bucket b7
    VerifyText    Deliver    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="customTab6__item"]    timeout=5
    # row 66  link  "Related"  [accepted]  -- member of bucket b7
    VerifyText    Related    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="flexipage_tab__item"]    timeout=5
    # row 67  button  "Information"  [accepted]  -- member of bucket b0
    VerifyText    Information    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Related"]/following::button)[1]    timeout=5
    # row 68  button  "Help Title"  [accepted]  -- member of bucket b1
    VerifyText    Help Title    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Title"]/following::button[@type\="button"])[1]    timeout=5
    # row 69  button  "Edit Title"  [accepted]  -- 3 of 16 same-shape controls (bucket b2)
    VerifyElement    xpath\=//button[@title\="Edit Title"]    timeout=5
    # row 70  button  "Help Status"  [accepted]  -- member of bucket b1
    VerifyText    Help Status    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Title"]/following::button[normalize-space(.)\="Help Status"])[1]    timeout=5
    # row 71  button  "Edit Status"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Status"]    timeout=5
    # row 73  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Owner"]/following::button[@type\="button"])[1]    timeout=5
    # row 74  button  "Change Owner"  [accepted]  -- member of bucket b3
    VerifyItem    Change Owner    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Change Owner"]    timeout=5
    # row 75  button  "Edit Jira Key"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Jira Key"]    timeout=5
    # row 76  button  "Edit myNewCustomField"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit myNewCustomField"]    timeout=5
    # row 77  button  "Change Record Type"  [accepted]  -- member of bucket b3
    VerifyItem    Change Record Type    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Change Record Type"]    timeout=5
    # row 78  button  "Edit Developer"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Developer"]    timeout=5
    # row 80  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=3    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Developer"]/following::button[@type\="button"])[1]    timeout=5
    # row 81  button  "Edit Documentation Complete"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Documentation Complete"]    timeout=5
    # row 82  button  "Project Management"  [accepted]  -- member of bucket b0
    VerifyText    Project Management    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Developer"]/following::button[normalize-space(.)\="Project Management"])[1]    timeout=5
    # row 83  button  "Help Project"  [accepted]  -- member of bucket b1
    VerifyText    Help Project    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Project Management"]/following::button[@type\="button"])[1]    timeout=5
    # row 84  button  "Edit Project"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Project"]    timeout=5
    # row 86  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=4    partial_match=False    timeout=5
    VerifyElement    xpath\=(//flexipage-record-home-template-desktop2//button[@title\="Preview"])[4]    timeout=5
    # row 87  button  "Help Epic"  [accepted]  -- member of bucket b1
    VerifyText    Help Epic    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Epic"]/following::button[@type\="button"])[1]    timeout=5
    # row 88  button  "Edit Epic"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Epic"]    timeout=5
    # row 89  button  "Help Theme"  [accepted]  -- member of bucket b1
    VerifyText    Help Theme    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Theme"]/following::button[@type\="button"])[1]    timeout=5
    # row 90  button  "Edit Theme"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Theme"]    timeout=5
    # row 91  button  "Edit Feature"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Feature"]    timeout=5
    # row 93  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=5    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Feature"]/following::button[@type\="button"])[1]    timeout=5
    # row 94  button  "Help Priority"  [accepted]  -- member of bucket b1
    VerifyText    Help Priority    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Priority"]/following::button[@type\="button"])[1]    timeout=5
    # row 95  button  "Edit Priority"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Priority"]    timeout=5
    # row 96  button  "Help Release"  [accepted]  -- member of bucket b1
    VerifyText    Help Release    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Priority"]/following::button[normalize-space(.)\="Help Release"])[1]    timeout=5
    # row 97  button  "Edit Release"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Release"]    timeout=5
    # row 98  button  "Help Sprint"  [accepted]  -- member of bucket b1
    VerifyText    Help Sprint    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Priority"]/following::button[normalize-space(.)\="Help Sprint"])[1]    timeout=5
    # row 99  button  "Edit Sprint"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Sprint"]    timeout=5
    # row 100  button  "Help Team"  [accepted]  -- member of bucket b1
    VerifyText    Help Team    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Team"]/following::button[@type\="button"])[1]    timeout=5
    # row 101  button  "Edit Team"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Team"]    timeout=5
    # row 102  button  "Edit Order"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Order"]    timeout=5
    # row 103  button  "Edit Close Date"  [accepted]  -- member of bucket b2
    VerifyElement    xpath\=//button[@title\="Edit Close Date"]    timeout=5
    # row 104  button  "User Story Definition"  [accepted]  -- member of bucket b0
    VerifyText    User Story Definition    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Close Date"]/following::button[normalize-space(.)\="User Story Definition"])[1]    timeout=5
    # row 105  button  "Acceptance"  [accepted]  -- member of bucket b0
    VerifyText    Acceptance    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="User Story Definition"]/following::button)[1]    timeout=5
    # row 106  button  "Estimation"  [accepted]  -- member of bucket b0
    VerifyText    Estimation    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Acceptance"]/following::button)[1]    timeout=5
    # row 107  link  "Overlap Awareness"  [accepted]  -- member of bucket b7
    VerifyText    Overlap Awareness    partial_match=False    timeout=5
    VerifyElement    xpath\=//a[@id\="flexipage_tab8__item"]    timeout=5
    # row 108  link  "User Story Metadata (3)"  [accepted]  -- member of bucket b16
    VerifyText    User Story Metadata (3)    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::a)[1]    timeout=5
    # row 110  button  "Preview"  [unreviewed]
    VerifyText    Preview    anchor=6    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::button[@type\="button"])[1]    timeout=5
    # row 111  button  "Show Actions"  [accepted]  -- member of bucket b1
    VerifyText    Show Actions    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Overlap Awareness"]/following::button[normalize-space(.)\="Show Actions"])[1]    timeout=5
    # row 113  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=7    partial_match=False    timeout=5
    VerifyElement    xpath\=(//lst-template-list//button[@title\="Preview"])[2]    timeout=5
    # row 114  button  "Show Actions"  [accepted]  -- member of bucket b1
    VerifyText    Show Actions    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=(//lst-template-list//button[@type\="button"])[4]    timeout=5
    # row 116  button  "Preview"  [accepted]  -- member of bucket b3
    VerifyItem    Preview    tag=button    anchor=8    partial_match=False    timeout=5
    VerifyElement    xpath\=(//lst-template-list//button[@title\="Preview"])[3]    timeout=5
    # row 117  button  "Show Actions"  [accepted]  -- member of bucket b1
    VerifyText    Show Actions    anchor=3    partial_match=False    timeout=5
    VerifyElement    xpath\=(//lst-template-list//button[@type\="button"])[6]    timeout=5
    # row 118  link  "View All User Story Metadata"  [accepted]  -- member of bucket b16
    VerifyText    View All User Story Metadata    partial_match=False    timeout=5
    VerifyElement    xpath\=(//lst-related-list-view-manager//a)[5]    timeout=5
    # row 119  button  "Pin the Panel"  [accepted]
    VerifyItem    Pin the Panel    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@aria-label\="Pin the Panel"]    timeout=5
    # row 120  button  "Home"  [accepted]  -- member of bucket b1
    VerifyText    Home    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="View All"]/following::button[normalize-space(.)\="Home"])[1]    timeout=5
    # row 121  button  "Close"  [accepted]  -- member of bucket b3
    VerifyItem    Close    tag=button    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Close"]    timeout=5
    # row 122  button  "Dismiss"  [accepted]  -- member of bucket b0
    VerifyText    Dismiss    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Just so you know"]/following::button)[1]    timeout=5
    # row 123  button  "View More"  [accepted]  -- member of bucket b0
    VerifyText    View More    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Selected for You"]/following::button[@type\="button"])[1]    timeout=5
    # row 124  button  "Use Email and Salesforce Together"  [accepted]  -- 3 of 4 same-shape controls (bucket b14)
    VerifyText    Use Email and Salesforce Together    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="View More"]/following::a)[1]    timeout=5
    # row 125  button  "Sales Engagement Considerations"  [accepted]  -- member of bucket b14
    VerifyText    Sales Engagement Considerations    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="3 steps"]/following::a)[1]    timeout=5
    # row 126  button  "Salesforce User Basics"  [accepted]  -- member of bucket b14
    VerifyText    Salesforce User Basics    partial_match=False    timeout=5
    VerifyElement    xpath\=//*[normalize-space(text())\="Trailhead"]/following-sibling::*//a    timeout=5
    # row 127  button  "Help"  [accepted]  -- member of bucket b1
    VerifyText    Help    anchor=1    partial_match=False    timeout=5
    VerifyElement    xpath\=//*[normalize-space(text())\="Serviceblazer"]/following-sibling::*//button[@type\="button"]    timeout=5
    # row 130  button  "Help"  [accepted]  -- member of bucket b1
    VerifyText    Help    anchor=2    partial_match=False    timeout=5
    VerifyElement    xpath\=//*[normalize-space(text())\="Salesblazer"]/following-sibling::*//button[@type\="button"]    timeout=5
    # row 132  button  "Join the Salesblazer Community"  [accepted]  -- member of bucket b14
    VerifyText    Join the Salesblazer Community    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Salesblazer"]/following::a[normalize-space(.)\="Join the Salesblazer Community"])[1]    timeout=5
    # row 133  button  "Assign Learning Content"  [accepted]  -- member of bucket b0
    VerifyText    Assign Learning Content    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Join the Salesblazer Community"]/following::button)[1]    timeout=5
    # row 134  button  "Cancel and close"  [accepted]  -- member of bucket b3
    VerifyItem    Cancel and close    tag=button    partial_match=False    timeout=5
    VerifyElement    xpath\=//button[@title\="Cancel and close"]    timeout=5
    # row 135  button  "Standard Rules"  [accepted]  -- member of bucket b0
    VerifyText    Standard Rules    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="Jul 16, 9:06 AM"]/following::button)[1]    timeout=5
    # row 136  button  "Advanced Rules"  [accepted]  -- member of bucket b0
    VerifyText    Advanced Rules    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="2"]/following::button)[1]    timeout=5
    # row 137  button  "Automations"  [accepted]  -- member of bucket b0
    VerifyText    Automations    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="1"]/following::button)[1]    timeout=5
    # row 142  button  "Add Changes"  [accepted]  -- member of bucket b0
    VerifyText    Add Changes    partial_match=False    timeout=5
    VerifyElement    xpath\=(//*[normalize-space(text())\="validateWirelessMouse"]/following::button[@type\="button"])[1]    timeout=5
    # row 154  link  "Revenue dev Revenue dev - 0 ahead, 0 behind"  [unreviewed]  -- 3 of 6 same-shape controls (bucket b9)
    VerifyText    Revenue dev Revenue dev - 0 ahead, 0 behind    partial_match=False    timeout=5
    # row 155  link  "Revenue QA Revenue QA"  [unreviewed]  -- member of bucket b9
    VerifyText    Revenue QA Revenue QA    partial_match=False    timeout=5
    # row 156  link  "INT INT"  [unreviewed]  -- member of bucket b9
    VerifyText    INT INT    partial_match=False    timeout=5
    # row 157  link  "UAT UAT"  [unreviewed]  -- member of bucket b9
    VerifyText    UAT UAT    partial_match=False    timeout=5
    # row 158  link  "Staging Staging"  [unreviewed]  -- member of bucket b9
    VerifyText    Staging Staging    partial_match=False    timeout=5
    # row 159  link  "Production Production"  [unreviewed]  -- member of bucket b9
    VerifyText    Production Production    partial_match=False    timeout=5

    # ===== 2. fill controls, each read back (nothing is saved) =====
    # row 51  output_field  "Sprint"  [accepted]  -- 3 of 6 same-shape controls (bucket b6)
    VerifyField    Sprint    <value>
    # row 52  output_field  "Project"  [accepted]  -- member of bucket b6
    VerifyField    Project    <value>
    # row 55  output_field  "Release"  [accepted]  -- member of bucket b6
    VerifyField    Release    <value>
    # row 56  output_field  "Record Type"  [accepted]  -- member of bucket b6
    VerifyField    Record Type    <value>
    # row 57  output_field  "Progress"  [accepted]  -- member of bucket b6
    VerifyField    Progress    <value>
    # row 58  output_field  "Status"  [accepted]  -- member of bucket b6
    VerifyField    Status    <value>    anchor=4
    # row 138  input_field  "Search by Label"  [accepted]
    TypeText    Search by Label    GZREV Search by Label 1    anchor=1
    VerifyInputValue    Search by Label    GZREV Search by Label 1    anchor=1
    # row 139  dropdown  "Last Modified Date"  [accepted]  -- 3 of 3 same-shape controls (bucket b18)
    PickList    Last Modified Date    GZREV Last Modified Date 4
    VerifyText    GZREV Last Modified Date 4    timeout=5
    # row 140  dropdown  "Last Modified By"  [accepted]  -- member of bucket b18
    PickList    Last Modified By    GZREV Last Modified By 4
    VerifyText    GZREV Last Modified By 4    timeout=5
    # row 141  dropdown  "Status"  [accepted]  -- member of bucket b18
    PickList    Status    GZREV Status 5
    VerifyText    GZREV Status 5    timeout=5

    # ===== 3. clicks, each preceded by a fresh GoTo (many of these navigate away) =====
    # row 43  button  "Follow"  [accepted]  -- 3 of 19 same-shape controls (bucket b0)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Follow    partial_match=False
    # row 44  button  "Edit"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Edit    anchor=1    partial_match=False
    # row 45  button  "Revenue Cloud Settings"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Revenue Cloud Settings    partial_match=False
    # row 46  button  "Commit Changes"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Commit Changes    partial_match=False
    # row 47  button  "Validate Changes"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Validate Changes    partial_match=False
    # row 48  button  "Run CRT Test Suite"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Run CRT Test Suite    partial_match=False
    # row 49  button  "Run Compliance Scan"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Run Compliance Scan    partial_match=False
    # row 50  button  "Show more actions"  [accepted]  -- 3 of 16 same-shape controls (bucket b1)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Show more actions    partial_match=False
    # row 54  button  "Preview"  [accepted]  -- 3 of 11 same-shape controls (bucket b3)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=1    partial_match=False
    # row 59  iframe  "accessibility title"  [accepted]
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    accessibility title    tag=iframe    partial_match=False
    # row 60  link  "User Story Commit"  [accepted]  -- 3 of 3 same-shape controls (bucket b16)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    User Story Commit    partial_match=False
    # row 62  link  "Plan"  [accepted]  -- 3 of 6 same-shape controls (bucket b7)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Plan    partial_match=False
    # row 63  link  "Build"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Build    partial_match=False
    # row 64  link  "Test"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Test    anchor=1    partial_match=False
    # row 65  link  "Deliver"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Deliver    partial_match=False
    # row 66  link  "Related"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Related    partial_match=False
    # row 67  button  "Information"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Information    partial_match=False
    # row 68  button  "Help Title"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Title    partial_match=False
    # row 69  button  "Edit Title"  [accepted]  -- 3 of 16 same-shape controls (bucket b2)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Title    tag=button
    # row 70  button  "Help Status"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Status    partial_match=False
    # row 71  button  "Edit Status"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Status    tag=button
    # row 73  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=2    partial_match=False
    # row 74  button  "Change Owner"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Change Owner    tag=button    partial_match=False
    # row 75  button  "Edit Jira Key"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Jira Key    tag=button
    # row 76  button  "Edit myNewCustomField"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit myNewCustomField    tag=button
    # row 77  button  "Change Record Type"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Change Record Type    tag=button    partial_match=False
    # row 78  button  "Edit Developer"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Developer    tag=button
    # row 80  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=3    partial_match=False
    # row 81  button  "Edit Documentation Complete"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Documentation Complete    tag=button
    # row 82  button  "Project Management"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Project Management    partial_match=False
    # row 83  button  "Help Project"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Project    partial_match=False
    # row 84  button  "Edit Project"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Project    tag=button
    # row 86  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=4    partial_match=False
    # row 87  button  "Help Epic"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Epic    partial_match=False
    # row 88  button  "Edit Epic"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Epic    tag=button
    # row 89  button  "Help Theme"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Theme    partial_match=False
    # row 90  button  "Edit Theme"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Theme    tag=button
    # row 91  button  "Edit Feature"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Feature    tag=button
    # row 93  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=5    partial_match=False
    # row 94  button  "Help Priority"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Priority    partial_match=False
    # row 95  button  "Edit Priority"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Priority    tag=button
    # row 96  button  "Help Release"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Release    partial_match=False
    # row 97  button  "Edit Release"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Release    tag=button
    # row 98  button  "Help Sprint"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Sprint    partial_match=False
    # row 99  button  "Edit Sprint"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Sprint    tag=button
    # row 100  button  "Help Team"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help Team    partial_match=False
    # row 101  button  "Edit Team"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Team    tag=button
    # row 102  button  "Edit Order"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Order    tag=button
    # row 103  button  "Edit Close Date"  [accepted]  -- member of bucket b2
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Edit Close Date    tag=button
    # row 104  button  "User Story Definition"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    User Story Definition    partial_match=False
    # row 105  button  "Acceptance"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Acceptance    partial_match=False
    # row 106  button  "Estimation"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Estimation    partial_match=False
    # row 107  link  "Overlap Awareness"  [accepted]  -- member of bucket b7
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Overlap Awareness    partial_match=False
    # row 108  link  "User Story Metadata (3)"  [accepted]  -- member of bucket b16
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    User Story Metadata (3)    partial_match=False
    # row 110  button  "Preview"  [unreviewed]
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Preview    anchor=6    partial_match=False
    # row 111  button  "Show Actions"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Show Actions    anchor=1    partial_match=False
    # row 113  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=7    partial_match=False
    # row 114  button  "Show Actions"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Show Actions    anchor=2    partial_match=False
    # row 116  button  "Preview"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Preview    tag=button    anchor=8    partial_match=False
    # row 117  button  "Show Actions"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Show Actions    anchor=3    partial_match=False
    # row 118  link  "View All User Story Metadata"  [accepted]  -- member of bucket b16
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    View All User Story Metadata    partial_match=False
    # row 119  button  "Pin the Panel"  [accepted]
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Pin the Panel    tag=button    partial_match=False
    # row 120  button  "Home"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Home    partial_match=False
    # row 121  button  "Close"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Close    tag=button    anchor=2    partial_match=False
    # row 122  button  "Dismiss"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Dismiss    partial_match=False
    # row 123  button  "View More"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    View More    partial_match=False
    # row 124  button  "Use Email and Salesforce Together"  [accepted]  -- 3 of 4 same-shape controls (bucket b14)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Use Email and Salesforce Together    partial_match=False
    # row 125  button  "Sales Engagement Considerations"  [accepted]  -- member of bucket b14
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Sales Engagement Considerations    partial_match=False
    # row 126  button  "Salesforce User Basics"  [accepted]  -- member of bucket b14
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Salesforce User Basics    partial_match=False
    # row 127  button  "Help"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help    anchor=1    partial_match=False
    # row 130  button  "Help"  [accepted]  -- member of bucket b1
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Help    anchor=2    partial_match=False
    # row 132  button  "Join the Salesblazer Community"  [accepted]  -- member of bucket b14
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Join the Salesblazer Community    partial_match=False
    # row 133  button  "Assign Learning Content"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Assign Learning Content    partial_match=False
    # row 134  button  "Cancel and close"  [accepted]  -- member of bucket b3
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickItem    Cancel and close    tag=button    partial_match=False
    # row 135  button  "Standard Rules"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Standard Rules    partial_match=True    # tab label carries a count; fixed in 00_transitions, aligned here 2026-09-18
    # row 136  button  "Advanced Rules"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Advanced Rules    partial_match=True
    # row 137  button  "Automations"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Automations    partial_match=True
    # row 142  button  "Add Changes"  [accepted]  -- member of bucket b0
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Add Changes    partial_match=False
    # row 154  link  "Revenue dev Revenue dev - 0 ahead, 0 behind"  [unreviewed]  -- 3 of 6 same-shape controls (bucket b9)
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Revenue dev Revenue dev - 0 ahead, 0 behind    partial_match=False
    # row 155  link  "Revenue QA Revenue QA"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Revenue QA Revenue QA    partial_match=False
    # row 156  link  "INT INT"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    INT INT    partial_match=False
    # row 157  link  "UAT UAT"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    UAT UAT    partial_match=False
    # row 158  link  "Staging Staging"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Staging Staging    partial_match=False
    # row 159  link  "Production Production"  [unreviewed]  -- member of bucket b9
    GoTo    https://copado-se-demo.lightning.force.com/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration?objectApiName&context=RECORD_DETAIL&recordId=a1vJ7000000lhWGIAY&backgroundContext=%2Flightning%2Fr%2Fcopado__User_Story__c%2Fa1vJ7000000lhWGIAY%2Fview
    VerifyText    Search by Label    timeout=30
    ClickText    Production Production    partial_match=False

    # ===== 19 chrome controls (nav bar, search, global actions) reviewed once for this org; --include-chrome to export them =====

    # ===== not exported: containers / hidden / no keyword =====
    # row 0  table_cell  "Choose a Row Select 2 items"  [accepted]  -- no keyword
    # row 1  column_header  "Name"  [accepted]  -- 3 of 5 same-shape controls (bucket b10)  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 2  button  "Show Name column actions"  [accepted]  -- 3 of 5 same-shape controls (bucket b11)  -- no keyword
    # row 3  column_header  "API Name"  [accepted]  -- member of bucket b10  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 4  button  "Show API Name column actions"  [accepted]  -- member of bucket b11  -- no keyword
    # row 5  column_header  "Last Modified Date"  [accepted]  -- member of bucket b10  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 6  button  "Show Last Modified Date column actions"  [accepted]  -- member of bucket b11  -- no keyword
    # row 7  column_header  "Last Modified By"  [accepted]  -- member of bucket b10  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 8  button  "Show Last Modified By column actions"  [accepted]  -- member of bucket b11  -- no keyword
    # row 9  column_header  "Status"  [accepted]  -- member of bucket b10  -- a column header is an ARGUMENT to the table rungs (the `col` of Get Table Cell Where / Set Table Cell), not a…
    # row 10  button  "Show Status column actions"  [accepted]  -- member of bucket b11  -- no keyword
    # row 11  table_cell  "Select Item 1"  [accepted]  -- 2 of 2 same-shape controls (bucket b19)  -- no keyword
    # row 12  table_cell  "Name"  [accepted]  -- 2 of 2 same-shape controls (bucket b20)  -- no keyword
    # row 13  table_cell  "API Name"  [accepted]  -- 3 of 8 same-shape controls (bucket b4)  -- no keyword
    # row 14  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b4  -- no keyword
    # row 15  table_cell  "Last Modified By"  [unreviewed]  -- member of bucket b4  -- no keyword
    # row 16  table_cell  "Status"  [accepted]  -- member of bucket b4  -- no keyword
    # row 17  table_cell  "Select Item 2"  [accepted]  -- member of bucket b19  -- no keyword
    # row 18  table_cell  "Name"  [accepted]  -- member of bucket b20  -- no keyword
    # row 19  table_cell  "API Name"  [accepted]  -- member of bucket b4  -- no keyword
    # row 20  table_cell  "Last Modified Date"  [accepted]  -- member of bucket b4  -- no keyword
    # row 21  table_cell  "Last Modified By"  [unreviewed]  -- member of bucket b4  -- no keyword
    # row 22  table_cell  "Status"  [accepted]  -- member of bucket b4  -- no keyword
    # row 23  native_table  "Select 2 items"  [accepted]  -- no keyword
    # row 53  link  "None"  [accepted]  -- 3 of 8 same-shape controls (bucket b5)  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 61  button  "None"  [accepted]  -- a button is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it hol…
    # row 72  link  "None"  [unreviewed]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 79  link  "None"  [unreviewed]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 85  link  "None"  [accepted]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 92  link  "None"  [accepted]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 109  link  "None"  [accepted]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 112  link  "None"  [accepted]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 115  link  "None"  [accepted]  -- member of bucket b5  -- a link is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it holds…
    # row 128  button  "None"  [accepted]  -- 3 of 3 same-shape controls (bucket b17)  -- a button is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it hol…
    # row 129  button  "None"  [accepted]  -- member of bucket b17  -- a button is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it hol…
    # row 131  button  "None"  [accepted]  -- member of bucket b17  -- a button is actuated by a click rung (ClickText / ClickItem, both already offered as locator options); it hol…
    # row 143  custom_component  "None"  [accepted]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 144  custom_component  "None"  [accepted]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 145  custom_component  "None"  [accepted]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 146  custom_component  "None"  [accepted]  -- 3 of 6 same-shape controls (bucket b8)  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 147  custom_component  "None"  [accepted]  -- member of bucket b8  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 148  custom_component  "None"  [accepted]  -- member of bucket b8  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 149  custom_component  "None"  [accepted]  -- member of bucket b8  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 150  custom_component  "None"  [accepted]  -- member of bucket b8  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 151  custom_component  "None"  [accepted]  -- member of bucket b8  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 152  custom_component  "Search by Label"  [accepted]  -- an unrecognised custom element has no proven keyword. Check SHAPES-GUIDE.md for a newer match, or add its tag…
    # row 153  datatable  "Select 2 items"  [accepted]  -- no keyword
