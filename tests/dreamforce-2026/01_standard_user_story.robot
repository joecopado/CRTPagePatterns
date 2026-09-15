*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- standard Source Format Pipeline story.
...                              Read-only UI narration on the shared cicd-demo org: opens the story,
...                              walks the pipeline, opens the Commit Experience, searches for one
...                              changed flow, compares it, asks AI to explain the change, runs
...                              Dependency Analysis, then asks AI to recommend the full commit.
...                              No step commits, promotes, deploys or saves anything.
Resource                        df26_common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Standard User Story Walkthrough - US-0000071 Account Automations
    Login To Demo Org
    Open User Story              ${US_0000071}
    # SAY: This is US-0000071, Account Automations -- a standard Source Format Pipeline story.
    # BRIEF: a user story is the unit of work. It owns the metadata, the tests, the quality gates and the deployment steps,
    # and the strip below it shows where it sits in the pipeline (Dev 2 -> Int -> UAT -> Production).
    # The red 'Environment is out of sync' banner is Copado noticing the dev org drifted from the branch -- say it, don't hide it.
    VerifyText                   Account Automations           timeout=20

    # SAY: Here's the pipeline this story flows through -- Dev, Integration, UAT, then Production.
    VerifyText                   Sales DX Dev 2                timeout=15
    VerifyText                   Sales DX Int                  timeout=10
    VerifyText                   MCDX-UAT                      timeout=10
    VerifyText                   MCDX Production                timeout=10

    # SAY: On the right, Overlap Awareness flags other stories touching the same metadata.
    VerifyText                   Overlap Awareness             timeout=10

    # SAY: This story also carries its own deployment steps -- automation that runs before and after the metadata deploys.
    # BRIEF: a manual task that warns users, an Apex script that seeds records, a data template deploy for CPQ config, and a Flow that
    # kicks off a Copado Robotic Testing run on the target org. They run every time the story deploys, in this order.
    # WHY THEY CARE: the release runbook stops being a Confluence page someone forgets.
    Open Deployment Steps
    VerifyText                   Notify Users of Lockout        timeout=10
    VerifyText                   Run Account Updater Record Creation Script    timeout=10
    VerifyText                   Update CPQ Config              timeout=10
    VerifyText                   Post Deploy Automation          timeout=10
    VerifyText                   Update Public Groups            timeout=10

    # SAY: Now let's commit -- this is where an engineer picks up the metadata that changed in this story's org.
    Open Commit Experience For   ${US_0000071}
    VerifyText                   Commit Changes: US-0000071    timeout=20

    # SAY: Get Changes pulls every changed component from the source org -- over a thousand candidates on a real project.
    ClickText                    Get Changes                    partial_match=False
    VerifyText                   Quick Find                     timeout=20                # left panel re-renders once the scan completes

    # SAY: Searching narrows that list down to exactly what we care about right now.
    TypeText                     Search                          Opportunity_Creation
    VerifyText                   Opportunity_Creation_Automation    timeout=15

    # SAY: Three components matched -- a Flow, its automation record, and its FlowDefinition. Let's compare the Flow.
    ClickElement                 //cds-table-row[.//cds-table-cell[.//span[normalize-space()\="Flow"]]][.//mark[contains(.,'Opportunity_Creation')]]//cds-table-cell[@role\="button"]    timeout=15

    # SAY: Compare renders the flow as a diagram with every node badged Added, Updated or Deleted -- and the XML toggle bottom-left shows the raw diff.
    VerifyText                   Flow: Opportunity_Creation_Automation    timeout=20
    VerifyText                   Additions                      timeout=10    # the count sits in its own node: 'Additions (4)' as one string measured NOT FOUND live 2026-09-15
    VerifyText                   Updates                        timeout=10
    VerifyText                   Deletions                      timeout=10

    # SAY: Explain Changes hands this diff to Copado AI and asks it to summarize what changed and why, in plain language.
    # BRIEF: today's answer -- API version 55 to 62, amendment/renewal branching collapsed into one assignment, a new bypass
    # gate reading Bypass_Auto_Naming__c, pricebook filter changed. Impact & Risk tells the tester what to test.
    # WHY THEY CARE: a real code review on a Flow, in plain English, before it leaves the dev org.
    ClickText                    Explain Changes                 partial_match=False
    VerifyText                   Orchestrate Agent                timeout=${AI_PANEL_TIMEOUT}
    VerifyText                   What Changed                     timeout=${AI_PANEL_TIMEOUT}    # DOM text is 'What Changed'; the caps are CSS text-transform (measured 2026-09-15)
    # SAY: It also checks this against the story's own description under User Story Alignment.
    VerifyText                   User Story Alignment              timeout=10    # same: DOM is title case, CSS uppercases it
    Close Side Panel

    # SAY: Let's close the compare view and select this Flow for the commit.
    Close Side Panel              heading=Flow: Opportunity_Creation_Automation
    ClickElement                 //cds-checkbox[@aria-label\="Select row Flow:Opportunity_Creation_Automation"]//input    timeout=15

    # SAY: With a row selected, Dependency Analysis checks what this flow touches that isn't part of this commit yet.
    # BRIEF: it runs off the Salesforce Dependency API plus Copado's own logic for profiles, permission sets and Agentforce.
    # Both fields come back 'Missing' in Sales DX Int: that is the 11 pm deploy failure, caught at commit time.
    # WHY THEY CARE: the 'field the flow needed wasn't there' failure moves from the deploy to the commit.
    # VOCAB: Overlap Awareness (right panel on the story) is a different thing -- two stories touching one component.
    ClickText                    Dependency Analysis              # label reads "Dependency Analysis (2)" once it has run, so partial match stays on
    VerifyText                   Dependencies                     timeout=20
    VerifyText                   Show All Dependencies             timeout=10
    VerifyText                   Opportunity.Extended_Opportunity_Name__c    timeout=10
    VerifyText                   Opportunity.Bypass_Auto_Naming__c    timeout=10
    # SAY: Both fields are missing on the destination -- worth knowing before this ships, and we are not adding them today.
    Close Side Panel              heading=Dependency Analysis

    # SAY: Last, AI Select Changes -- instead of searching ourselves, we ask Copado's AI to recommend the whole commit for this story.
    # BRIEF: it reasons from the story's OWN description (as a / I want / so that + acceptance criteria), not from what you clicked.
    # US-0000071's description is about 'tracking dev work by team', so today it recommended Mission Control components, not the flow.
    # Either tell that story or run this on a story whose description matches its metadata.
    # WHY THEY CARE: stops someone else's work, or half of yours, shipping out of a shared dev org.
    ClickText                    Changes                         partial_match=False    # exact match only hits the tab -- "Get Changes"/"Explain Changes"/"Refresh Changes"/"Select Changes" all contain this text but none equal it
    ClickItem                    btn-ai                            tag=button              # the AI Select Changes button carries class "btn btn-outline-primary btn-ai"
    VerifyText                   Orchestrate Agent                 timeout=${AI_PANEL_TIMEOUT}
    VerifyText                   Recommended Components           timeout=${AI_PANEL_TIMEOUT}    # the 'RECOMMENDED COMPONENTS FOR US-0000071' h5 is CSS-uppercased; this heading is plain DOM text (measured 2026-09-15)
    VerifyText                   Smart Changes analysis completed    timeout=10    partial_match=True    # the green toast that marks the AI done state
    # SAY: That's the full loop -- search, compare, explain, analyze dependencies, and let AI recommend the commit. Nothing here has been saved.
    Close Side Panel
