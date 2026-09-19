"""GarzAI Recorder -- the AI page object model store (docs/recorder/PLAN.md §Stream P).

Partitioned by org (Salesforce) or host (web); one JSON record per page key; every element
carries its VERIFIED locator ladder (primary + backups with history), the effect observed when it
was acted on, and the flows that pass through the page. Lookup before scan.
"""
