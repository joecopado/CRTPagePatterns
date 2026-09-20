*** Settings ***
Documentation             Example resource file with custom keywords. NOTE: Some keywords below may need
...                       minor changes to work in different instances.
# The CANONICAL CRT set is five libraries and the standard template says to keep all five even
# when a suite uses only some (`tools/qforce-lite/templates/crt/resources/common.robot`).
# QWeb was MISSING here (F211): `Set Library Search Order    QForce    QWeb` below names it,
# and it resolved only because CRT resolves it natively -- locally the order line was naming a
# library this file never imported.
Library                   QWeb
Library                   QForce
Library                   Collections
Library                   String
Library                   DateTime
# The generator library. It is declared HERE, not only in garzai_data.robot, because the
# template's rule is that the canonical set travels whole -- and because a common.robot that
# declares no generator is exactly how this recorder came to invent run-stamped strings
# instead of using Faker (the user, 2026-09-20).
Library                   FakerLibrary

*** Variables ***
# IMPORTANT: Please read the readme.txt to understand needed variables and how to handle them!!
${BROWSER}                chrome
# `${login_url}` is a CRT PROJECT variable (the UI-login path). A suite that authenticates by JWT
# (`Gz Login`: JwtAuthenticate + JwtLogin) never defines it, and this table used to derive
# `${home_url}` from it -- so EVERY run of the fsc7f suite printed
# `Setting variable '${home_url}' failed: Variable '${login_url}' not found` on its line 19
# (F188, 2026-09-20). The empty defaults below are what a Variables table may hold; a CRT /
# `--variable` value overrides them whenever one is given. The home page URL is derived AT CALL
# TIME by `Home Url` (below): `${login_url}` when it is set, else the live instance's own URL
# (`GetInstanceUrl`, QForce) -- the JWT path has no login URL at all and needs none.
# The standard template gives this a real default and a specific meaning: it is the JWT TOKEN
# ENDPOINT, not a page to visit -- https://login.salesforce.com for production and Developer
# Edition, https://test.salesforce.com for a sandbox. The separate ${loginUrl} (camelCase) is
# the already-authenticated frontdoor URL Copado CI/CD injects for the TARGET org. Keeping
# this empty, as this file used to, is what made `${home_url}` fail on every run.
${login_url}              https://login.salesforce.com
${loginUrl}               ${EMPTY}
${home_url}               ${EMPTY}


*** Keywords ***
Setup Browser
    # Setting search order is not really needed here, but given as an example 
    # if you need to use multiple libraries containing keywords with duplicate names
    Set Library Search Order                          QForce    QWeb
    # options=: Chrome 142+ asks 'wants to access other apps and services on this device' when a page
    # calls a device-local address (the GarzAI composer on 127.0.0.1:18077); this flag turns that
    # check off for the session. COULD-NOT-CHECK on Chrome 152 until one session runs with it.
    Open Browser          about:blank                 ${BROWSER}    options=--disable-features=LocalNetworkAccessChecks
    SetConfig             LineBreak                   ${EMPTY}               #\ue000
    Evaluate              random.seed()               random                 # initialize random generator
    SetConfig             DefaultTimeout              5s                    #sometimes salesforce is slow
    # adds a delay of 0.3 between keywords. This is helpful in cloud with limited resources.
    SetConfig             Delay                       0.3

End suite
    Close All Browsers


Login
    [Documentation]       Login to Salesforce instance. Takes instance_url, username and password as
    ...                   arguments. Uses values given in Copado Robotic Testing's variables section by default.
    [Arguments]           ${sf_instance_url}=${login_url}    ${sf_username}=${username}   ${sf_password}=${password}
    IF    not $sf_instance_url
        Fail              Login: no login URL -- the project variable `login_url` is not set (a JWT suite authenticates with `Gz Login` / `JwtLogin` instead and never calls this keyword).
    END
    GoTo                  ${sf_instance_url}
    TypeText              Username                    ${sf_username}             delay=1
    
    # Some envs will not show password field directly
    ${password_field}=   Run Keyword And Return Status    Verify Input Element   Password   partial_match=False   timeout=1                     
    # Added this to handle different types logins in different environments.
    IF  not ${password_field}
        Log    Password field not found, trying to click Log In button first.    console=True
        ClickText            Log In
    END                  
    
    TypeSecret           Password                    ${sf_password}
    ClickText            Log In
    # We'll check if variable ${secret} is given. If yes, fill the MFA dialog.
    # If not, MFA is not expected.
    # ${secret} is ${None} unless specifically given.
    ${MFA_needed}=       Run Keyword And Return Status          Should Not Be Equal    ${None}       ${secret}
    Run Keyword If       ${MFA_needed}               Fill MFA   ${sf_username}         ${secret}    ${sf_instance_url}                                            


Login As
    [Documentation]       Login As different persona. User needs to be logged into Salesforce with Admin rights
    ...                   before calling this keyword to change persona.
    ...                   Example:
    ...                   LoginAs    Chatter Expert
    [Arguments]           ${persona}
    ClickText             Setup
    ClickItem             Setup      delay=1
    SwitchWindow          NEW
    TypeText              Search Setup                ${persona}             delay=2
    ClickElement          //*[@title\="${persona}"]   delay=2    # wait for list to populate, then click
    VerifyText            Freeze                      timeout=45                        # this is slow, needs longer timeout          
    ClickText             Login                       anchor=Freeze          partial_match=False    delay=1 


Fill MFA
    [Documentation]      Gets the MFA OTP code and fills the verification dialog (if needed)
    [Arguments]          ${sf_username}=${username}    ${mfa_secret}=${secret}  ${sf_instance_url}=${login_url}
    ${mfa_code}=         GetOTP    ${sf_username}   ${mfa_secret}   ${login_url}  
    TypeSecret           Verification Code       ${mfa_code}      
    ClickText            Verify 


Home
    [Documentation]       Example appstate: Navigate to homepage, login if needed
    # private key given -> Use JWT Authentication to login, otherwise use UI login
    ${jwt_enabled}=    Get Variable Value    $private_key    ${NONE}
    IF    $jwt_enabled
          JWT Authenticate            ${jwt_client_id}                ${username}    ${private_key}   sandbox=True
          JWT Login
    ELSE
        ${home}=             Home Url
        GoTo                 ${home}
        ${login_status} =    IsText                      To access this page, you have to log in to Salesforce.    5
        Run Keyword If       ${login_status}             Login
    END
    ClickText            Home
    VerifyTitle          Home | Salesforce


Home Url
    [Documentation]       The Lightning home page URL, derived when it is asked for (F192): `${login_url}/lightning/page/home`
    ...                   when the project gives a login URL, else the live instance's own URL from `GetInstanceUrl`
    ...                   (QForce; valid once `Gz Login` / `JwtLogin` has established the session). Never a
    ...                   Variables-table derivation: `${login_url}` is undefined on the JWT path and the table
    ...                   line errored on every run (F188).
    ${base}=              Set Variable    ${login_url}
    IF    not $base
        ${base}=          GetInstanceUrl
    END
    ${base}=              Evaluate    str($base).rstrip('/')
    RETURN                ${base}/lightning/page/home


# Example of custom keyword with robot fw syntax. NOTE: These keywords may need to be adjusted
# to work in your environment
VerifyStage
    [Documentation]       Verifies that stage given in ${text} is at ${selected} state; either selected (true) or not selected (false)
    [Arguments]           ${text}                     ${selected}=true
    VerifyElement        //a[@title\="${text}" and (@aria-checked\="${selected}" or @aria-selected\="${selected}")]


VerifyStageColor
    [Documentation]           Example keyword on how to verify background color of element.
    ...                       Note that this keyword might need adjusting in your instance (colors and locators can be different)
    [Arguments]               ${stage_text}    ${color}=navy
    &{COLORS}=                Create Dictionary    navy=rgba(3, 45, 96, 1)    green=rgba(172, 243, 228, 1)

    ${elem}=                  GetWebElement              ${stage_text}    element_type=item
    ${background_color}=      Evaluate                   $elem.value_of_css_property("background-color")
    Should Be Equal           ${COLORS.${color}}          ${background_color}     msg=Error: Background color ( ${background_color}) differs from ${color} (${COLORS.${color}})
    

NoData
    VerifyNoItem         ${data}       tag=a            timeout=3                      delay=2


DeleteAccounts
    [Documentation]       RunBlock to remove all data until it doesn't exist anymore
    ClickText             ${data}
    ClickText             Delete
    VerifyText            Are you sure you want to delete this account?
    ClickText             Delete                      2
    VerifyText            Undo
    VerifyNoText          Undo
    ClickText             Accounts                    partial_match=False


DeleteLeads
    [Documentation]       RunBlock to remove all data until it doesn't exist anymore
    ClickText             ${data}
    ClickText             Delete
    VerifyText            Are you sure you want to delete this lead?
    ClickText             Delete                      2
    VerifyText            Undo
    VerifyNoText          Undo
    ClickText             Leads                    partial_match=False

