*** Settings ***
Documentation                   SETUP RECORDING PROBE, STOCK (2026-09-18): the CRT recorder as shipped, on
...                              Salesforce Setup pages in slockard. No GarzAI library is imported here on
...                              purpose: run this suite in its OWN Live Testing session, turn the recorder on,
...                              record the Setup steps in docs/RUNSHEET-setup-recording.md, stop. Then stop the
...                              session and run setup-recorder-override.robot for the same steps.
...                              READ-ONLY: never Save on a Setup page; every step ends in Cancel or a close.
Resource                        ../../resources/common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Setup Pages With The Stock Recorder
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    # Permission Sets: a classic Visualforce page inside Setup's iframe
    GoTo    ${instance}/lightning/setup/PermSets/home
    VerifyText    Permission Sets    timeout=30
    # -- turn the recorder ON here and follow the run sheet --
