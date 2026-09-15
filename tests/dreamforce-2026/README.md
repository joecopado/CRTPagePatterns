# Dreamforce 2026 -- Copado CI/CD booth walkthroughs (SECICD org)

Five read-only demo walkthroughs the SE presses play on and talks over. Every step is a plain sentence;
the talking point for a step is the `# SAY:` comment above it and the longer brief is the `# BRIEF:` /
`# WHY THEY CARE:` lines under it. Run them step by step in Live Testing and read the comment before the
next step. **No step commits, promotes, deploys or saves anything** -- the org is shared with the whole
SE team and function credits are exhausted.

    df26_common.robot              variables (story ids, Copado app id, commit URL base) + Login To Demo Org,
                                   Open User Story, Open Commit Experience For, Open Deployment Steps, Close Side Panel
    01_standard_user_story.robot   US-0000071: pipeline, Overlap Awareness, deployment steps (Build tab), Commit Experience:
                                   Get Changes -> search -> Compare (flow diagram) -> Explain Changes -> Dependency Analysis -> AI Select Changes
    02_agentforce.robot            US-0001088: manual activation steps, Get Previously Commited (9), select all, Dependency Analysis
    03_data360.robot               US-0000968: metadata-type filter DataPackageKitDefinition, expand DK02
    04_revenue_management.robot    US-0001043: Revenue Cloud Settings modal, deployment steps, Selected Data tab
    05_data_template.robot         Pricing-P-3-PriceAdjustmentSchedule data template

Authentication: the project's `${client_idCICD}` / `${usernameCICD}` / `${private_keyCICD}` triple (values in CRT's
variables section, never here). Navigation starts from `GetInstanceUrl` after `JwtLogin`; the story opens inside the
**Copado** app (`06m7Q0000001l7SQAQ`) because only that app's story layout carries `Revenue Cloud Settings`.

The Commit Experience is a separate Angular app at `https://na.devops.copado.com/en/commit/<UserStoryId>`; the
suites `GoTo` it directly (same browser session) and fall back to the story's `Commit Changes` button.

## Verified live on 2026-09-15 vs UNVERIFIED

Confirmed by driving the org: the story page controls and tabs; Deployment Steps on the Build tab; Get Changes
(1,178 items on US-0000071); the Search box; the Compare cell and the flow diagram panel (Properties 2 / Additions 4 /
Updates 4 / Deletions 6); Explain Changes -> Orchestrate Agent (Changes / Impact & Risk / Recommendations); the Flow
row checkbox; Dependency Analysis and its two Missing fields; Select Changes (AI) and its recommendation table; the
panel close buttons; Get Previously Commited (9) on US-0001088; the typeable metadata-type filter on US-0000968;
Revenue Cloud Settings and its modal (Standard Rules 2 / Advanced Rules 1 / Automations 57) on US-0001043.

Marked `# UNVERIFIED:` in the files (eyeball before Tuesday):

| File | Line | What |
|---|---|---|
| 02_agentforce | select all | header checkbox xpath `(//div[@role="rowgroup"]/preceding::input[@type="checkbox"])[last()]` |
| 03_data360 | DataPackageKitDefinition | picking the suggestion from the typeable filter |
| 03_data360 | DK02 | the expand chevron on the kit row |
| 04_revenue_management | Close | the modal's top-right X (`//button[@title="Close"]`) |
| 04_revenue_management | Selected Data | that tab's contents for this story |
| 05_data_template | PriceAdjustmentSchedule | the relationship / External Virtual Id section of the template page |

Not run in a CRT build yet: these files were syntax-parsed with Robot Framework 7.4.2 only. Treat the first CRT
result as the proof. The full run sheet with screenshots lives in the GarzAI repo under `docs/dreamforce-2026/`.
