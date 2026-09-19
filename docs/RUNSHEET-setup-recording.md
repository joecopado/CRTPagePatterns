# Run sheet: recording Salesforce Setup pages, stock vs GarzAI composer (2026-09-18)

Why: the corpus prediction (`docs/audit/crt-recorder-prediction-2026-09-18.md` in the orchestrator)
says Setup's content area is Visualforce inside an iframe the parser never sees, and that the stock
recorder's lines inside that frame carry a path rooted at the frame with nothing naming the frame.
That is a prediction. Two recordings of the same steps make it a measurement.

Read-only throughout: never click Save on a Setup page. Every step ends in Cancel or a close.

## Session 1: stock
1. Live Testing on `tests/setup-pages/setup-recorder-stock.robot`, run the test case through the
   `VerifyText Permission Sets` step.
2. Recorder ON. Record:
   - Quick Find: type `Object` into the Setup search box, click **Object Manager**.
   - Object Manager: click **Account**, click **Fields & Relationships**, click the **Phone** field,
     click **Cancel** (or the browser back if there is no Cancel).
   - Setup left nav: click **Permission Sets** (under Users). In the list (the iframe page): click the
     first permission set's name, click **Object Settings**, click **Account**, click **Edit**, tick
     one checkbox, click **Cancel**.
   - Flows: Quick Find `Flows`, click **Flows**, open the row-action menu (the small arrow on the
     first row), then click anywhere neutral to close it.
3. Recorder OFF. Stop the session.

## Session 2: override
1. NEW Live Testing session on `tests/setup-pages/setup-recorder-override.robot`. Run through the
   status step: the console must print `"patched": "ok"`, version `2026-09-18h parser-fallback`,
   and `parser: loaded` (if it says `parser: error`, paste the line: that is the lxml question).
2. Click **Allow** on the Chrome prompt when the Setup page opens.
3. Recorder ON. Record exactly the same steps as session 1.
4. Run `Status After Recording`. Recorder OFF. Paste both panes.

What I read from the harvest: their keyword frames per step in session 1; the composer's decisions,
proposals and backups in session 2; the didChange edits that reached the pane in both.
