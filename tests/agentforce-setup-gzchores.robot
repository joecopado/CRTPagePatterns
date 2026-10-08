*** Settings ***
Documentation                 AGENTFORCE SETUP (gzchores sandbox, 2026-10-08) -- the two switches, in order: Einstein, then Agentforce.
...
...                           Recorded live through Claude-CRT v2 (story agentforce-setup, visible browser) and adapted so it can run
...                           again: each switch is SET to on (ClickCheckbox <switch> on does nothing when it is already on) and then
...                           verified. The recorder's own line was a plain click (ClickItem checkbox tag=input anchor=Agentforce),
...                           which a second run would use to turn Agentforce back OFF.
...
...                           PROVEN live 2026-10-08 on gzchores:
...                             - Einstein Setup: v2 read "Turn on Einstein" = On (it was already on).
...                             - Agentforce Agents: the switch read off before the click and on after (PASS-GUARDED), then on again
...                               from the page itself.
...                             - Both locators below matched exactly ONE element on the live page, each reading checked = true.
...                           NOT-YET-RUN: this file in a CRT build, and the ClickCheckbox / VerifyCheckboxValue lines on these two
...                           switches (they were already on when the locators were checked).
...                           Needs the project variables usernameGzChores / client_idGzChores / private_keyGzChores (added
...                           2026-10-08). Data Cloud provisioning, the long part of a full Agentforce setup, is not in this test.
Resource                      ../resources/common.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite


*** Variables ***
# Both switches carry no visible label of their own, so each is found by an xpath kept in a variable (an `=` inside an
# xpath written inline in a step makes Robot read it as a named argument). Each matched exactly one element on 2026-10-08.
${EINSTEIN_SWITCH}            (//*[normalize-space(text())='Turn on Einstein']/following::input[@type='checkbox'])[1]
${AGENTFORCE_SWITCH}          //input[@type='checkbox' and @aria-label='Agentforce']


*** Test Cases ***
Turn on Einstein, then Agentforce
    [Documentation]           Einstein must be on before Agentforce. Each switch is set to on, never toggled, then verified.
    ${token}=                 JwtAuthenticate    ${client_idGzChores}    ${usernameGzChores}    ${private_keyGzChores}    sandbox=true
    JwtLogin
    ${inst}=                  GetInstanceUrl
    # 1. Einstein
    GoTo                      ${inst}/lightning/setup/EinsteinGPTSetup/home
    VerifyText                Turn on Einstein    timeout=30
    ClickCheckbox             ${EINSTEIN_SWITCH}      on
    VerifyCheckboxValue       ${EINSTEIN_SWITCH}      on
    # 2. Agentforce
    GoTo                      ${inst}/lightning/setup/EinsteinCopilot/home
    VerifyText                Agentforce    timeout=30
    ClickCheckbox             ${AGENTFORCE_SWITCH}    on
    VerifyCheckboxValue       ${AGENTFORCE_SWITCH}    on
