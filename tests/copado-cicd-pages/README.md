# Copado CI/CD page objects -- every interaction per page, and the transitions between them

Generated from the GarzAI page-object loop on 2026-09-15 (capture -> review table -> live probe on SECICD ->
accepted rows written to the AI POM store -> exported). Read `00_transitions.robot` first: it is the recorded flow in
the order it was driven, with `# PAGE:` where the page key changes, `# TRANSITION:` on every navigation, modal or
panel, and `# STATE:` where the page's state changed (a row ticked, a panel open, the agent streaming). The three
page files list every control that resolved live on that page, in keyword form and xpath form, and each starts with
the TRANSITION that reaches the page and the STATE precondition its controls need.

    00_transitions.robot                 the chronological flow: User Story record -> Commit Changes -> Commit Experience
                                         (Get Changes, search, Compare panel, Explain Changes, row tick, Dependency Analysis,
                                         AI Select Changes) -> US-0001043 -> Revenue Cloud Settings modal -> close
    01_user-story-record.robot           cicd-demo|/lightning/r/copado__User_Story__c/{id}/view  (Build tab state), 89 steps
    02_commit-experience.robot           na.devops.copado.com|/en/commit/{id}  (after Get Changes + search), 21 steps
    03_revenue-cloud-settings-modal.robot  cicd-demo|/lightning/action/quick/copado__User_Story__c.copado_labs__Revenue_Cloud_Deployment_Configuration, 94 steps

Failed live forms are COMMENTS carrying the reason (a locator lesson, never executed). Every step is read-only:
nothing commits, promotes, adds selections or saves. Authentication is the project's `${client_idCICD}` triple.

Page states observed on the Commit Experience: loading -> changes-listed (Dependency Analysis disabled) -> row-selected
(the analysis auto-runs: 'Analyzing dependencies', then enabled) -> dependency-panel -> dependencies-analysed (label
'Dependency Analysis (2)') ; compare-panel (spinner, then diagram) ; agent-thinking (Stop) -> agent-done (Copy; a
green 'Smart Changes analysis completed!' toast for Select Changes). The AI panel headings are CSS-uppercased: the DOM
says 'What Changed' / 'Recommended Components', and that is what VerifyText matches.

Regenerate: `python3 tools/recorder/pom/export_flow.py docs/recorder/sessions/cicd-demo/df26-copado-cicd-flow-2026-09-15.json --out 00_transitions.robot`
and `python3 tools/recorder/review_table.py robot --review docs/recorder/review/<page>/review.json --all --out <file>` in the GarzAI repo.
