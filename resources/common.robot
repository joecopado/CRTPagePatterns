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
# TWO VARIABLES, TWO MEANINGS, NOT INTERCHANGEABLE. Both are kept; neither is legacy.
#
#   ${login_url}   the JWT TOKEN ENDPOINT -- what `JwtAuthenticate` authenticates AGAINST, never a
#                  page to visit. The standard template gives it this real default:
#                  https://login.salesforce.com for production and Developer Edition,
#                  https://test.salesforce.com for a sandbox. (The lint flags this literal as a
#                  hard-coded instance URL; here it is the template's own documented default, so
#                  that finding is a false positive on this line and is left visible rather than
#                  silenced.)
#   ${loginUrl}    the already-authenticated FRONTDOOR URL Copado CI/CD injects for the target org.
#                  Empty today and UNUSED -- the user, 2026-09-20: "always include the cicd option
#                  in common.robot. but, we're not using it. We don't have a need for it right now.
#                  Just if we take it in pipelines we will."
#
# `${home_url}` is GONE with the legacy `Home` / `Home Url` keywords it existed for (see the
# removal note below). It was derived in this table from `${login_url}`, which a JWT suite never
# defines, so EVERY run of the fsc7f suite printed `Setting variable '${home_url}' failed:
# Variable '${login_url}' not found` on its line 19 (F188, 2026-09-20). Nothing derives a home URL
# in a Variables table any more: `Open Lightning Path    /lightning/page/home` takes its base from
# `GetInstanceUrl` at call time, after JwtLogin.
${login_url}              https://login.salesforce.com
${loginUrl}               ${EMPTY}


*** Keywords ***
Setup Browser
    # Setting search order is not really needed here, but given as an example 
    # if you need to use multiple libraries containing keywords with duplicate names
    Set Library Search Order                          QForce    QWeb
    # options=: Chrome 142+ asks 'wants to access other apps and services on this device' when a page
    # calls a device-local address (the GarzAI composer on 127.0.0.1:18077); this flag turns that
    # check off for the session. The F188 container session (Chrome 152) served 86 composer calls
    # to 127.0.0.1 with no prompt -- but that is NOT a controlled proof and F219 said so: the
    # Local Network Access grant is per ORIGIN per PROFILE, so 86 completed calls are equally
    # consistent with this flag working, with the profile already holding a grant, or with a
    # person clicking Allow. Errors entry 905cef44e8 records the prompt's literal text observed
    # on this same org BEFORE the flag, which is most of a before/after pair, not a controlled
    # one. Keep the flag; a negative control is owed. The F188 session
    # (2026-09-20) is the evidence above. Every entry resource that
    # opens a browser carries this now, not only the recorder's (F214).
    Open Browser          about:blank                 ${BROWSER}    options=--disable-features=LocalNetworkAccessChecks
    SetConfig             LineBreak                   ${EMPTY}               #\ue000
    Evaluate              random.seed()               random                 # initialize random generator
    SetConfig             DefaultTimeout              5s                    #sometimes salesforce is slow
    # adds a delay of 0.3 between keywords. This is helpful in cloud with limited resources.
    SetConfig             Delay                       0.3
    Gz Log Override Status


Gz Log Override Status
    [Documentation]       WHICH RECORDER IS THIS SESSION ACTUALLY RUNNING? (F259, validator V-A
    ...                   sec 4.) `_patch_bundle` can REFUSE -- a stock bundle whose `enable`,
    ...                   `disable` or `pushStep` site has moved is left alone rather than written
    ...                   half-patched -- and until this build that refusal reached nobody: the
    ...                   library imported normally, the composer started, the keywords
    ...                   registered, and the editor session recorded with the plain Copado
    ...                   recorder looking entirely normal. `Gz Override Status` carried the
    ...                   answer and NO .robot file in this repo called it (grep: zero hits,
    ...                   this file included).
    ...
    ...                   So the suite setup logs `patched` and `anchor_counts` once. It is a
    ...                   REPORT, never a gate: a suite that does not import the override library
    ...                   is not broken by it, and says COULD-NOT-CHECK rather than passing
    ...                   quietly.
    ${ok}    ${raw}=      Run Keyword And Ignore Error                      Gz Override Status
    IF                    '${ok}' != 'PASS'
        Log               GZ OVERRIDE: COULD-NOT-CHECK -- the override library is not imported in this suite, so which recorder is running cannot be read from here    level=WARN
        RETURN
    ${st}=                Evaluate                    json.loads(r'''${raw}''')    json
    Log                   GZ OVERRIDE: patched=${st}[patched] anchors=${st}[anchor_counts] build=${st}[version]
    IF                    'REFUSED' in str($st.get('patched'))
        Log               GZ OVERRIDE REFUSED: ${st}[patched] -- anchors ${st}[anchor_counts]; this session is recording with the STOCK recorder    level=WARN
    END

End suite
    Close All Browsers


JwtImpersonate
    # A LOCAL DRY-RUN OF THIS FILE IS COULD-NOT-CHECK, and it is our tooling, not this resource.
    # `robot --dryrun` here reports `Multiple keywords with name 'GoTo' found -- QForce.Go To /
    # QWeb.Go To`. That is an artefact of `tools/qforce-lite/QForce/`, OUR OWN license-free shim
    # standing in for the real QForce (the licensed library is permanently out of local scope, user
    # 2026-08-30). The shim deliberately re-exports the common ~20-keyword set under QWeb's own
    # names, so locally 19 keywords exist twice and every bare call collides. Whether the REAL
    # QForce collides with QWeb cannot be checked from here.
    # A first pass on 2026-09-20 qualified three calls to `QWeb.GoTo` and reported 29 more as a
    # defect in this resource. That was WRONG -- it would have changed a shipped file to suit a
    # local stand-in. Reverted. Bare `GoTo` is what this file, the proven copado-trial resource and
    # CRT's own samples all use.
    [Documentation]       Native Salesforce "Login As" via JWT -- verbatim from
    ...                   crt-samples/standard.robot (user, 2026-08-31), the same body the
    ...                   copado-trial suite and the exported-project fixture already carry.
    ...                   Resolves `${user}` (an Id, a Username or a Name) by query, then lands as
    ...                   that user in ONE navigation.
    ...
    ...                   WHY IT IS HERE (Loop 5 item E.16, lint rule L9): this resource shipped
    ...                   without it, so the only run-as path it offered was the password `Login`
    ...                   keyword below. CLAUDE.md is explicit -- to act as another user, use
    ...                   `JwtImpersonate`, never a password or passkey login form. The JWT trio
    ...                   (`JWTAuthenticate` / `JWTLogin` / `JwtImpersonate`) is org-agnostic by
    ...                   construction: nothing here names an instance, and the target org comes
    ...                   from the session the trio established.
    [Arguments]           ${user}                     ${logged_in}=${False}    ${landing}=%2Flightning%2Fpage%2Fhome
    IF                    '${user}'.startswith('005')
        ${userId}=        Set Variable                ${user}
    ELSE
        ${q}=             QueryRecords                SELECT Id FROM User WHERE (Username='${user}' OR Name='${user}') AND IsActive=true LIMIT 1
        IF                ${q}[totalSize] == 0
            Fail          JwtImpersonate: no active user matching '${user}'
        END
        ${userId}=        Set Variable                ${q}[records][0][Id]
    END
    ${o}=                 QueryRecords                SELECT Id FROM Organization LIMIT 1
    ${orgId}=             Set Variable                ${o}[records][0][Id]
    ${su}=                Set Variable                /servlet/servlet.su?oid=${orgId}&suorgadminid=${userId}&retURL=${landing}&targetURL=${landing}
    IF                    ${logged_in}
        ${inst}=          GetInstanceUrl
        GoTo              ${inst}${su}
    ELSE
        JWTLogin          ${su}
    END


# ---------------------------------------------------------------------------------------------
# REMOVED 2026-09-20 (Loop 5 item E.16, the user: "Home, Login, Login As are all legacy and do not
# use JWT at all. Those are garbage."): `Login`, `Login As`, `Fill MFA`, `Home`, `Home Url`.
#
# They were the stock CRT sample's password-login path: a username/password form, an MFA OTP, a
# "Login" button click, and a home URL derived from a login host. CLAUDE.md is explicit that to act
# as another user you use `JwtImpersonate`, never a password or passkey login form, and the lint's
# L10 rule flagged six of these lines for exactly that.
#
# NOTHING IS LOST -- every one has a JWT-native replacement that is already proven in 35 suites:
#
#   Login / Login As / Fill MFA  ->  the JWT trio: `JWTAuthenticate`, `JWTLogin`, and
#                                    `JwtImpersonate` (defined above). Org-agnostic by
#                                    construction: nothing names an instance, and the target org
#                                    comes from the session the trio established.
#   Home / Home Url              ->  `Open Lightning Path    /lightning/page/home`
#                                    (crt/resources/garzai_navigation.robot), which takes its base
#                                    from `GetInstanceUrl` after JwtLogin. That file also carries
#                                    `Open Record Page`, `Open Object Page` and `Open Nav Tab`.
#
# Callers checked before removal: ZERO in any suite of ours. The only two `Login` callers are
# `crt-parity/tests/cpq_test.robot` and `docs/crt-train/crt-samples/cpq_test.robot` -- CRT's own
# stock SAMPLE, kept verbatim as a reference copy of what the platform ships, and deliberately
# untouched.
#
# `${loginUrl}` (camelCase) STAYS DECLARED and is now unused (the user, 2026-09-20: "always include
# the cicd option in common.robot. but, we're not using it. We don't have a need for it right now.
# Just if we take it in pipelines we will."). It is the already-authenticated frontdoor Copado
# CI/CD injects for a target org -- the option is kept for the day a pipeline supplies it.
# ---------------------------------------------------------------------------------------------
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

