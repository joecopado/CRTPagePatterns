*** Settings ***
Documentation     Pre- and post-deployment steps as CRT tests: the UI shows the BEFORE, one keyword does
...               the work through the API, the UI refreshes and shows the AFTER. Every id is looked up by
...               API name at run time, so the same file runs unchanged in every environment of a pipeline.
...               Each test puts the org back the way it found it, inline, so it runs on repeat.
Resource          ../../resources/common.robot
Library           ${CURDIR}/GzDeploySteps.py
Suite Setup       Open Org
Suite Teardown    CloseAllBrowsers

*** Variables ***
${FLOW}           Action_Callback_Flow
${FLOW_LABEL}     Action Callback Flow
${PERMSET}        Access_Restricted_UI
${PACKAGE}        Copado Deployer
${MIN_VERSION}    19.0

*** Keywords ***
Open Org
    Set Library Search Order    QForce    QWeb
    OpenBrowser        about:blank    ${BROWSER}
    SetConfig          DefaultTimeout    10s
    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${INSTANCE}=       Salesforce Api Session    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    Set Suite Variable    ${INSTANCE}

*** Test Cases ***
Pre-deployment gate: the dependent package is at the required version
    GoTo              ${INSTANCE}/lightning/setup/ImportedPackage/home
    VerifyText        ${PACKAGE}    timeout=30
    ${version}=       Installed Package Version    ${PACKAGE}
    Log To Console    ${PACKAGE} installed version: ${version}
    Should Be True    ${version} >= ${MIN_VERSION}    ${PACKAGE} is ${version}, below the required ${MIN_VERSION}

Post-deployment: activate the flow the deployment left inactive, then set it back
    GoTo              ${INSTANCE}/lightning/setup/Flows/home
    VerifyText        ${FLOW_LABEL}    timeout=30
    ${before}=        Flow Status    ${FLOW}
    Log To Console    ${FLOW_LABEL} before: ${before}
    Activate Flow     ${FLOW}
    RefreshPage
    VerifyText        ${FLOW_LABEL}    timeout=30
    ${after}=         Flow Status    ${FLOW}
    Log To Console    ${FLOW_LABEL} after: ${after}
    Should Be Equal   ${after}    Active
    # back to how we found it, so the demo runs on repeat
    Deactivate Flow   ${FLOW}
    ${reset}=         Flow Status    ${FLOW}
    Should Be Equal   ${reset}    Inactive

Post-deployment: grant the access the deployment did not, then remove it
    # the Misc tab (LWC Recipes) renders a card from this very permission set: it says
    # "The permission set is not assigned" until the assignment exists, then "is assigned"
    Remove Permission Set    ${PERMSET}    ${usernameSlock}
    GoTo              ${INSTANCE}/lightning/n/Misc_Techniques
    VerifyText        The permission set is not assigned    timeout=30
    Assign Permission Set    ${PERMSET}    ${usernameSlock}
    RefreshPage
    VerifyText        The permission set is assigned    timeout=30
    Log To Console    ${PERMSET} now assigned to ${usernameSlock}
    # back to how we found it, so the demo runs on repeat
    Remove Permission Set    ${PERMSET}    ${usernameSlock}
    RefreshPage
    VerifyText        The permission set is not assigned    timeout=30
