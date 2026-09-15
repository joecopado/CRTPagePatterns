*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- Data Template record. Read-only UI
...                              narration on the shared cicd-demo org: opens the Pricing-P-3
...                              price adjustment schedule data template directly by URL and shows
...                              its identity. No step commits, promotes, deploys or saves anything.
Resource                        df26_common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Data Template Walkthrough - Pricing-P-3-PriceAdjustmentSchedule
    Login To Demo Org
    # SAY: This is a Data Template -- Copado's way of moving reference/config data, like Revenue Cloud pricing, alongside metadata.
    GoTo                         ${INSTANCE}/lightning/r/copado__Data_Template__c/${DATA_TEMPLATE_ID}/view
    VerifyText                   Pricing-P-3-PriceAdjustmentSchedule    timeout=20
    VerifyText                   PriceAdjustmentSchedule                 timeout=10

    # SAY: This template targets one object -- Price Adjustment Schedule -- and can carry child/related templates and external Id fields for matching records across orgs.
    # BRIEF: one template, a whole object graph. Parents deploy first so the Ids exist, the main object next, children last. It is an
    # upsert, so re-running updates instead of duplicating. Objects with no external Id field get a VIRTUAL external Id: a record
    # matching formula over a combination of fields.
    # IF ASKED 'is the new experience GA?': the Agentia Data Deploy flavour is beta (Deployer 26.33+, via success@copado.com);
    # classic data templates are the GA path.
    VerifyText                   PriceAdjustmentSchedule                 timeout=15    # UNVERIFIED: relationship/child-template and External Virtual Id fields not confirmed live -- eyeball this section before Tuesday
    # SAY: That's the last piece -- data templates ride the same pipeline, reviewed and promoted the same way as any other change.
