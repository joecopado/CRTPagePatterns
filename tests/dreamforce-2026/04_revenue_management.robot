*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- Revenue Cloud / Labs Pipeline story.
...                              Read-only UI narration on the shared cicd-demo org: opens the story,
...                              shows its Revenue Cloud-specific deployment steps, then in the
...                              Commit Experience looks at the Selected Data tab (data templates
...                              travel alongside metadata for Revenue Cloud configuration). No step
...                              commits, promotes, deploys or saves anything.
Resource                        df26_common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Revenue Management Walkthrough - US-0001043
    Login To Demo Org
    Open User Story              ${US_0001043}
    # SAY: This is US-0001043, Revenue Management - RCA - New product configuration, on the Labs Pipeline.
    VerifyText                   Revenue Management                  timeout=20

    # SAY: Revenue Cloud has its own settings surface right on the story.
    # BRIEF: Revenue Cloud is half metadata (decision tables, expression sets, context definitions) and half records (products, price
    # books, adjustment schedules) plus configuration rules and automations that only exist as data. This modal reads those rules
    # straight out of the org so you pick the ones that travel with the story.
    # BASELINE TEMPLATES LINE: 22 Pricing-* data templates ship in this org, Product2/Pricebook2 down to PriceAdjustmentSchedule and
    # tiers, that partners and SMEs customise instead of starting blank.
    # IF ASKED RCA/RLM specifics: take the follow-up -- the docs corpus has nothing on Revenue Cloud.
    ClickText                    Revenue Cloud Settings              partial_match=False    # header button of the Copado app's story layout (confirmed live 2026-09-15)
    VerifyText                   Revenue Cloud Deployment Configuration    timeout=20
    # SAY: Copado reads the configuration rules and automations straight out of the org: Standard Rules, Advanced Rules and 57 Automations, targeted at Revenue QA. We pick, we never press Add Changes on this org.
    VerifyText                   Standard Rules                       timeout=10
    VerifyText                   Advanced Rules                       timeout=10
    VerifyText                   Automations                          timeout=10
    ClickText                    Cancel and close
    # SAY: Product configuration changes carry their own before/after deployment steps -- laptop products, configuration rules, and refreshed decision tables.
    Open Deployment Steps
    VerifyText                   Deploy Laptop product                timeout=10
    VerifyText                   Deploy Product Configuration Rules 3    timeout=10
    VerifyText                   Refresh Decision Tables 3             timeout=10

    # SAY: Revenue Cloud configuration isn't only metadata -- pricing and product data travels with it. That's the Selected Data tab in the Commit Experience.
    Open Commit Experience For   ${US_0001043}
    ClickText                    Selected Data                        partial_match=False
    VerifyText                   Selected Data                         timeout=15                # UNVERIFIED: contents of this tab for this story not confirmed live
    # SAY: That's Revenue Cloud on the same pipeline -- Apex, Flow, and pricing data, reviewed the same way.
