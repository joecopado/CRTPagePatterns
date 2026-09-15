*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- shared variables and narration keywords for the
...                              Copado CI/CD walkthroughs on the SECICD org (copado-se-demo). Read-only UI
...                              narration for an SE to press play and talk over: no step commits, promotes,
...                              deploys or saves anything. Browser setup/teardown and the library imports come
...                              from ../../resources/common.robot (this project's own resource).
Resource                        ../../resources/common.robot
Library                         QWeb

*** Variables ***
# The Commit Experience is a separate Angular app on a different host (na.devops.copado.com), not a
# Lightning page. GoTo it directly: the same browser session carries the Salesforce auth.
${COMMIT_URL_BASE}              https://na.devops.copado.com/en/commit/

# Demo from the Copado app (its story layout carries Revenue Cloud Settings and Run CRT Test Suite;
# other apps' layouts do not). AppDefinition DurableId of app "Copado" (Copado_SE) in this org.
${COPADO_APP_ID}                06m7Q0000001l7SQAQ

# User Story ids (copado__User_Story__c), captured live 2026-09-15.
${US_0000071}                   a1v7Q000001LJnRQAW
# US-0000071 Account Automations (Source Format Pipeline)
${US_0001088}                   a1vJ6000001FtL2IAK
# US-0001088 Build Product Catalog Assistant Employee Agent (Agentforce)
${US_0000968}                   a1vJ7000000lC89IAE
# US-0000968 Data Cloud Deployment - DK03 (Data 360)
${US_0001043}                   a1vJ7000000lhWGIAY
# US-0001043 Revenue Management - RCA - New product configuration (Labs Pipeline)

# Data Template record (copado__Data_Template__c): Pricing-P-3-PriceAdjustmentSchedule
${DATA_TEMPLATE_ID}             a0UJ70000020zMSMAY

# How long the AI panels (Explain Changes, AI Select Changes) get before their content is looked for.
# Talking points are "# SAY:" comments above the step they belong to; run the suite step by step in
# Live Testing and read the comment before pressing the next step.
${AI_PANEL_TIMEOUT}             30s

*** Keywords ***
Login To Demo Org
    [Documentation]             JWT login to SECICD with this project's own variable triple
    ...                         (values live in CRT's variables section, never in this repo).
    ${token}=                   JwtAuthenticate             ${client_idCICD}            ${usernameCICD}            ${private_keyCICD}
    JwtLogin
    ${INSTANCE}=                GetInstanceUrl
    Set Suite Variable          ${INSTANCE}

Open User Story
    [Documentation]             Direct-URL navigation to a User Story record inside the Copado app
    ...                         (URL-first: never click through nav).
    [Arguments]                 ${id}
    GoTo                        ${INSTANCE}/lightning/app/${COPADO_APP_ID}/r/copado__User_Story__c/${id}/view
    VerifyText                  User Story                  timeout=20                  # the record page chrome rendered

Open Commit Experience For
    [Documentation]             Opens the Commit Experience for the given User Story id. GoTo direct
    ...                         (same session); falls back to the story's "Commit Changes" button if
    ...                         the direct GoTo lands on a login page instead.
    [Arguments]                 ${id}
    GoTo                        ${COMMIT_URL_BASE}${id}
    ${on_login}=                IsText                      Log in                      2
    IF                          ${on_login}
        Open User Story         ${id}
        ClickText               Commit Changes               partial_match=False
    END
    VerifyText                  Commit Changes: US-              timeout=30              # header reads "Commit Changes: US-000####"

Open Deployment Steps
    [Documentation]             The Deployment Steps related list sits on the story's Build tab, below
    ...                         the Information section (confirmed live 2026-09-15 on US-0000071).
    ClickText                   Build                       partial_match=False
    VerifyText                  Deployment Steps            timeout=15


Close Side Panel
    [Documentation]             Closes a slide-out panel by its heading text: the close button is the
    ...                         first button after the heading. CONFIRMED live for "Orchestrate Agent",
    ...                         "Flow: Opportunity_Creation_Automation" and "Dependency Analysis".
    [Arguments]                 ${heading}=Orchestrate Agent
    ClickElement                //*[normalize-space()\="${heading}"]/following::button[1]                     timeout=10
