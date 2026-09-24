*** Settings ***
Documentation     Community login: a JWT session lands a Partner Community member INSIDE an
...               Experience Cloud site with no password, no login form and no passkey.
...               Runbook: docs/EXPERIENCE-CLOUD-JWT-LOGIN.md in the orchestrator repo
...               (proven live 2026-09-21 on SDO - Partner Central, user Paul Partner).
...               Values for the PC variables live in CRT, never in this file
...               (~/crt-jwt-credentials/jwt-jgarzaaf-copado-com-/credentials.txt).
Resource          ../../resources/common.robot
Library           ${CURDIR}/../../resources/GzCommunity.py
Suite Setup       Setup Browser
Suite Teardown    End suite

*** Variables ***
# PC = Partner Central on jwt-jgarzaaf-copado-com-. The username is the PARTNER user, not the admin.
${sitePC}         https://co1735825376471.my.site.com/partnercentral

*** Test Cases ***
Community login lands the partner inside the site
    # 1. the site as a guest
    GoTo              ${sitePC}/s/
    # 2. the guest header offers a login (top right); either spelling the template renders
    VerifyAny         Login, Log In    timeout=30
    # 3.
    Sleep             3s
    # 4. the JWT community login: mint the one-time frontdoor on the SITE domain and go there
    #    at once (a frontdoor_uri is single-use; a reused one lands as a GUEST, silently)
    ${fd}=            Jwt Community Frontdoor    ${client_idPC}    ${usernamePC}    ${private_keyPC}    ${sitePC}
    GoTo              ${fd}
    # 5. signed in: the member nav is the only reliable difference between the guest page and the
    #    member page (same URL, same heading); the login link is gone
    VerifyText        Notifications    timeout=30
    VerifyNoText      Login    timeout=10
