*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- Data Cloud / Data 360 deployment story.
...                              Read-only UI narration on the shared cicd-demo org: opens the story,
...                              then in the Commit Experience filters to Data Package Kit
...                              Definitions and expands one kit's contents. No step commits,
...                              promotes, deploys or saves anything.
Resource                        df26_common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Data Cloud Deployment Walkthrough - US-0000968 DK03
    Login To Demo Org
    Open User Story              ${US_0000968}
    # SAY: This is US-0000968, Data Cloud Deployment - DK03 -- Data 360 has its own metadata type, and Copado commits it the same way as any other component.
    VerifyText                   Data Cloud Deployment              timeout=20

    # SAY: In the Commit Experience, we filter down to just this metadata type instead of scanning everything.
    # BRIEF: by hand, data kits mean many manual steps, no partial moves, and a manual activation click in Setup after every deploy.
    # Here: filter on DataPackageKitDefinition, expand the kit, untick what you are not ready to move (it becomes Add (Selective)),
    # and after deployment Copado activates the kit for you.
    # IF ASKED 'does it move records?': no -- configuration only (streams, DLOs, insights, identity resolution, segments, graphs).
    Open Commit Experience For   ${US_0000968}
    VerifyText                   Quick Find                          timeout=20
    TypeText                     All metadata types                   DataPackageKit            # the filter is a typeable combobox (confirmed live); the option below is from its suggestion list
    ClickText                    DataPackageKitDefinition             partial_match=False    # UNVERIFIED: picking the suggestion was not clicked live
    ClickText                    Get Changes                          partial_match=False
    VerifyText                   Quick Find                           timeout=20             # left panel re-renders once the filtered scan completes

    # SAY: Data package kits bundle several data objects together -- let's open one and see what's inside.
    ClickText                    DK02                                  timeout=15             # UNVERIFIED: expand-chevron interaction not confirmed live
    VerifyText                   DK02                                  timeout=15
    # SAY: That's a Data 360 deployment picked up exactly like a Salesforce one -- same commit screen, same review, nothing saved today.
