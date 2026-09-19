*** Settings ***
Documentation                   Dreamforce 2026 booth demo -- Agentforce employee agent story.
...                              Read-only UI narration on the shared cicd-demo org: opens the story,
...                              shows the manual post-deploy activation steps an Agentforce agent
...                              needs, then in the Commit Experience re-picks up everything already
...                              committed once before and runs Dependency Analysis on the whole set.
...                              No step commits, promotes, deploys or saves anything.
Resource                        df26_common.robot
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Agentforce Employee Agent Walkthrough - US-0001088
    Login To Demo Org
    Open User Story              ${US_0001088}
    # SAY: This is US-0001088 -- Build Product Catalog Assistant Employee Agent. Agentforce components ride the same pipeline as any other metadata.
    # BRIEF: an agent is a graph, not a component -- GenAiPlannerBundle, Bot + BotVersion, the Apex actions, the permission set that
    # lets people reach it. Miss one and the agent arrives and silently does nothing.
    # WHY THEY CARE: Agentforce deploys are the new 'it worked in dev'. Copado moves the graph as a unit.
    VerifyText                   Build Product Catalog Assistant Employee Agent    timeout=20

    # SAY: Agentforce agents always deploy inactive, so this story carries manual activation steps that run after the metadata lands.
    Open Deployment Steps
    VerifyText                   Activate the Agent             timeout=10
    VerifyText                   Assign Agent Access Permission Set    timeout=10
    # SAY: Both are marked Manual, After -- a person confirms the agent is right before it goes live for anyone.

    # SAY: This story was already committed once before, so let's pick that same set back up instead of re-scanning everything.
    Open Commit Experience For   ${US_0001088}
    VerifyText                   Quick Find                     timeout=20
    ClickText                    Get Previously Commited        timeout=15                # button text includes a live count, live today "Get Previously Commited (9)" -- default substring match, do not use partial_match=False here
    VerifyText                   Selected metadata               timeout=15

    # SAY: Selecting everything at once lets us check the whole agent bundle for missing dependencies together.
    ClickElement                 (//div[@role\="rowgroup"]/preceding::input[@type\="checkbox"])[last()]    timeout=15    # UNVERIFIED: header "select all" checkbox locator, not confirmed live

    # SAY: Dependency Analysis on the full set -- this is how we catch a missing permission set or a missing prompt template before it ships.
    ClickText                    Dependency Analysis    # count-suffixed label ("Dependency Analysis (n)"): exact match fails, partial is right -- aligned with 01_standard_user_story 2026-09-18
    VerifyText                   Dependencies                    timeout=20
    # SAY: Whatever shows up here, we review it, we don't add it -- that decision belongs to the story's owner, not to this demo.
    Close Side Panel              heading=Dependency Analysis
