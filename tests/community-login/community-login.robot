*** Settings ***
Documentation     Community login: the JWT session lands Paul Partner INSIDE SDO - Partner Central
...               with no password, no login form and no passkey. Same connected app and private
...               key as every other JWT login in this job (${client_id} / ${private_key}); the
...               user is the partner, named inline. Runbook: docs/EXPERIENCE-CLOUD-JWT-LOGIN.md
...               in the orchestrator repo (proven live 2026-09-21).
Resource          ../../resources/common.robot
Library           ${CURDIR}/../../resources/GzCommunity.py
Suite Setup       Setup Browser
Suite Teardown    End suite

*** Test Cases ***
Community login lands the partner inside the site
    # 1. the site as a guest
    GoTo              https://co1735825376471.my.site.com/partnercentral/s/
    # 2. the guest header offers a login (top right); either spelling the template renders
    VerifyAny         Login, Log In    timeout=30
    # 3.
    Sleep             3s
    # 4. the JWT community login: mint the one-time frontdoor on the SITE domain and go there at
    #    once (a frontdoor_uri is single-use; a reused one lands as a GUEST, silently)
    ${fd}=            Jwt Community Frontdoor    ${client_id}    paulpartner112024142803356718.kj25ktxp6y4j@copado.com2025/01/2_19-12-43.demo    ${private_key}    https://co1735825376471.my.site.com/partnercentral
    GoTo              ${fd}
    # 5. signed in: the member nav is the only reliable difference between the guest page and the
    #    member page (same URL, same heading); the login link is gone
    VerifyText        Notifications    timeout=30
    VerifyNoText      Login    timeout=10
