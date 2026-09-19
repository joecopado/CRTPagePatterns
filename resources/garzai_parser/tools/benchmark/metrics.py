#!/usr/bin/env python3
"""CANONICAL metric definitions for the GarzAI test-automation benchmark.

This module is the definition of record. Producers (locator-survival emitters,
flake harnesses, authoring-cost loggers) should IMPORT from here rather than
re-typing a schema, so a definition change cannot silently diverge between the
tool that emits and the tool that reports.

Design rule running through all of it, from docs/ERRORS.md's most-repeated
failure family: **a success signal that was never corroborated is not a success.**
Every enum below therefore has an explicit "resolved but unverified" and an
explicit "resolved the wrong thing" state, and neither is ever folded into a
success rate.

--------------------------------------------------------------------------
LOCATOR SURVIVAL  (canonical; supersedes any provisional definition)
--------------------------------------------------------------------------

Atom = ONE (element x locator-chain x scenario) evaluation. Emit atoms as JSONL;
aggregate in analysis. Per-page and per-suite numbers are DERIVED, never emitted
directly -- otherwise the denominators cannot be recombined later.

Outcome enum, mutually exclusive, precedence top to bottom:

  primary_ok        primary locator resolved AND node identity matched baseline
  healed            primary failed; a backup resolved AND identity matched
  wrong_node        something resolved but identity did NOT match  -> FAILURE
  ambiguous         the locator matched >1 node -> FAILURE (QWeb silently takes
                    the first match; a passing test proves nothing about which)
  dead              nothing in the chain resolved
  unverified        resolved, but there was no evidence available to confirm it
                    is the same node -> NOT a success, reported on its own
  absent_by_design   the scenario deliberately removed this element; EXCLUDED
                    from the denominator, count reported separately

RULING on the trap ("a fallback can resolve the WRONG element"):
  A backup locator resolving is NOT evidence that it healed. `healed` requires a
  positive identity match against the baseline fingerprint. If identity cannot
  be established, the outcome is `unverified` -- never `healed`. A harness that
  cannot capture identity at all must emit every non-primary resolution as
  `unverified` and say so in its provenance block. It may not report a survival
  rate; it may only report a resolution rate, under that name.

RULING on what survival is measured against:
  Locator survival is measured against a **CHANGED** page. Every atom carries a
  named `scenario` describing the change that was applied. Running the same
  chains against an UNCHANGED page measures chain redundancy, not survival; it
  is reported as `chain_redundancy_rate` under `scenario="none"` and may never
  be quoted as locator survival. Only the changed-page number answers the
  question a customer is actually asking.

RULING on quoting:
  `effective_survival_rate` may only ever be quoted alongside `wrong_node_rate`
  and `unverified_rate`. `rates()` returns them together for that reason; do not
  destructure one out of it for a headline.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Optional

SCHEMA_VERSION = "locator-survival/1.0.0"

# ---------------------------------------------------------------- outcomes ---
PRIMARY_OK = "primary_ok"
HEALED = "healed"
WRONG_NODE = "wrong_node"
AMBIGUOUS = "ambiguous"
DEAD = "dead"
UNVERIFIED = "unverified"
ABSENT_BY_DESIGN = "absent_by_design"

OUTCOMES = (PRIMARY_OK, HEALED, WRONG_NODE, AMBIGUOUS, DEAD, UNVERIFIED,
            ABSENT_BY_DESIGN)
SUCCESS_OUTCOMES = (PRIMARY_OK, HEALED)          # nothing else, ever
FAILURE_OUTCOMES = (WRONG_NODE, AMBIGUOUS, DEAD)
NOT_A_SUCCESS = (WRONG_NODE, AMBIGUOUS, DEAD, UNVERIFIED)


# ------------------------------------------------------------- fingerprint ---
_WS = re.compile(r"\s+")

# Attributes trusted as identity, in priority order. A baseline element that
# carries none of these and has no text is UNVERIFIABLE by construction.
IDENTITY_ATTRS = ("data-testid", "data-qa", "id", "name", "aria-label",
                  "for", "href", "value")


def normalize_text(s: Optional[str], limit: int = 120) -> str:
    return _WS.sub(" ", (s or "")).strip().lower()[:limit]


@dataclass
class Fingerprint:
    """Identity evidence for one node, captured on the BASELINE page.

    `dom_path` is recorded for diagnosis and is deliberately NOT used for
    matching: a legitimate UI change moves nodes, and matching on position would
    report real survivals as wrong_node. `bbox` is a tie-breaker for human
    review only.
    """
    tag: str = ""
    text: str = ""                       # already normalized
    attrs: dict = field(default_factory=dict)
    dom_path: str = ""
    shadow_depth: int = 0
    bbox: Optional[list] = None          # [x, y, w, h] at a fixed viewport

    @property
    def identity_attr(self):
        for a in IDENTITY_ATTRS:
            v = self.attrs.get(a)
            if v:
                return a, str(v)
        return None

    @property
    def verifiable(self) -> bool:
        return bool(self.identity_attr) or bool(self.text)


def identity_match(baseline: Fingerprint, found: Optional[Fingerprint]) -> str:
    """Return 'match' | 'mismatch' | 'unverifiable'.

    Rules, in order:
      1. If the baseline carried a trusted identity attribute, that attribute
         decides. Present-and-equal -> match. Present-and-different -> mismatch.
         Missing on the found node -> fall through to the text rule (an
         attribute can legitimately be dropped by a refactor).
      2. Else if the baseline had text: same tag AND same normalized text ->
         match; same tag, different text -> mismatch.
      3. Else -> unverifiable. Never guess.
    """
    if found is None:
        return "unverifiable"
    ident = baseline.identity_attr
    if ident:
        attr, val = ident
        other = found.attrs.get(attr)
        if other is not None:
            return "match" if str(other) == val else "mismatch"
    if baseline.text:
        if found.tag and baseline.tag and found.tag != baseline.tag:
            return "mismatch"
        return "match" if found.text == baseline.text else "mismatch"
    return "unverifiable"


def classify(primary_resolved: bool,
             backup_resolved: bool,
             match_count: int,
             baseline: Fingerprint,
             found: Optional[Fingerprint],
             absent_by_design: bool = False) -> str:
    """The single place an outcome is decided. Do not re-implement this."""
    if absent_by_design:
        return ABSENT_BY_DESIGN
    if not primary_resolved and not backup_resolved:
        return DEAD
    if match_count is not None and match_count > 1:
        return AMBIGUOUS
    verdict = identity_match(baseline, found)
    if verdict == "unverifiable":
        return UNVERIFIED
    if verdict == "mismatch":
        return WRONG_NODE
    return PRIMARY_OK if primary_resolved else HEALED


# ------------------------------------------------------------------- atom ---
@dataclass
class LocatorAtom:
    """One row of the locator-survival JSONL. Emit these; aggregate later."""
    schema: str = SCHEMA_VERSION
    run_id: str = ""                 # groups atoms from one harness invocation
    collected_at: str = ""
    page: str = ""                   # POM / page name -- the rollup key
    element_id: str = ""             # stable name of the element within the POM
    scenario: str = "none"           # "none" = redundancy, NOT survival
    scenario_kind: str = "none"      # see SCENARIOS below
    chain: list = field(default_factory=list)   # locators tried, in order
    chain_index_used: Optional[int] = None      # which one resolved (0=primary)
    outcome: str = DEAD
    match_count: Optional[int] = None
    resolve_ms: Optional[float] = None
    baseline_fingerprint: Optional[dict] = None
    found_fingerprint: Optional[dict] = None
    identity_verdict: str = "unverifiable"
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# Named UI-drift scenarios. Only these count as locator SURVIVAL; `none` does
# not. Keep the vocabulary closed so results from different sessions combine.
SCENARIOS = {
    "none": "unchanged page -- measures chain redundancy, NOT survival",
    "css_class_rename": "class attributes renamed, structure and text unchanged",
    "id_churn": "generated ids change (the Lightning/Aura default)",
    "dom_reparent": "element wrapped in / moved between containers",
    "sibling_reorder": "order of sibling elements changed",
    "label_reword": "visible label text reworded, semantics unchanged",
    "duplicate_text": "a second element with the same visible text is added",
    "element_removed": "element deleted -- expect absent_by_design",
    "attr_stripped": "data-testid / id removed from the element",
    "shadow_wrap": "element moved inside a new shadow root",
    "i18n": "page rendered in another locale",
}


def rates(atoms) -> dict:
    """Derive every published rate from a list of atoms (or dicts).

    Denominator is `evaluated` = atoms minus absent_by_design. All rates over
    `evaluated` sum to 1.0; the returned dict asserts it.
    """
    counts = {o: 0 for o in OUTCOMES}
    for a in atoms:
        o = a["outcome"] if isinstance(a, dict) else a.outcome
        counts[o] = counts.get(o, 0) + 1
    evaluated = sum(counts[o] for o in OUTCOMES if o != ABSENT_BY_DESIGN)

    def r(n):
        return None if not evaluated else round(n / evaluated, 4)

    out = {
        "schema": SCHEMA_VERSION,
        "n_atoms": sum(counts.values()),
        "n_evaluated": evaluated,
        "n_absent_by_design": counts[ABSENT_BY_DESIGN],
        "counts": counts,
        "survival_rate": r(counts[PRIMARY_OK]),
        "healed_rate": r(counts[HEALED]),
        "effective_survival_rate": r(counts[PRIMARY_OK] + counts[HEALED]),
        "wrong_node_rate": r(counts[WRONG_NODE]),
        "ambiguous_rate": r(counts[AMBIGUOUS]),
        "dead_rate": r(counts[DEAD]),
        "unverified_rate": r(counts[UNVERIFIED]),
    }
    if evaluated:
        s = sum(out[k] for k in ("survival_rate", "healed_rate", "wrong_node_rate",
                                 "ambiguous_rate", "dead_rate", "unverified_rate"))
        out["_rates_sum_to_one"] = abs(s - 1.0) < 0.01
    # A number that must never be quoted alone travels with its caveats.
    out["_quote_with"] = ["wrong_node_rate", "unverified_rate"]
    return out


def rollup(atoms, level="page") -> dict:
    """Aggregate atoms. level = 'page' | 'scenario' | 'suite'.

    Survival is only defined for scenario != 'none'; anything measured against
    an unchanged page comes back under `chain_redundancy` and is kept apart.
    """
    changed = [a for a in atoms if (a["scenario"] if isinstance(a, dict) else a.scenario) != "none"]
    stable = [a for a in atoms if (a["scenario"] if isinstance(a, dict) else a.scenario) == "none"]

    def key(a):
        d = a if isinstance(a, dict) else asdict(a)
        return d.get("page") if level == "page" else d.get("scenario") if level == "scenario" else "ALL"

    groups = {}
    for a in changed:
        groups.setdefault(key(a), []).append(a)

    out = {
        "level": level,
        "locator_survival": {k: rates(v) for k, v in sorted(groups.items())},
        "locator_survival_overall": rates(changed) if changed else None,
    }
    if stable:
        red = rates(stable)
        out["chain_redundancy"] = {
            "n": red["n_evaluated"],
            "chain_redundancy_rate": red["effective_survival_rate"],
            "_warning": "measured on an UNCHANGED page -- this is NOT locator survival",
        }
    return out


# =============================================================================
# FLAKE  (canonical; supersedes any provisional definition)
# =============================================================================
"""
Atom = ONE (repeat_set, run_index, test_case) outcome. Emit atoms; derive rates.
A run-level atom (test_name=None, is_run_atom=True) carries the build's own
status, wall clock and queue time so speed data is captured at the same moment
-- it cannot be reconstructed afterwards.

RULING 1 -- flaky is NOT the same as red.
  A test that fails in every one of N identical runs is BROKEN, not flaky.
  A test that passes in every run is STABLE. Only a test with BOTH outcomes in
  the repeat set is FLAKY. Folding consistently-red tests into a flake number
  inflates it and hides a real defect behind a word that means "ignore me".
  `classify_test_series` returns stable | flaky | broken | insufficient.

RULING 2 -- the run-level number and the test-level number are different claims.
  `run_failure_rate` (runs with >=1 failing test / eligible runs) is what a
  pipeline feels: the probability a green pipeline turns red for nothing.
  `flaky_test_share` is what an engineer feels. Publish both; neither substitutes.

RULING 3 -- exclusions must be PRE-REGISTERED, EVIDENCED, and DOUBLE-REPORTED.
  Excluding infrastructure failures is correct -- otherwise the metric measures
  Copado's backend, not the suite. But an unexplained exclusion is how a metric
  gets accused of being massaged. Therefore, all three of:
    (a) the exclusion signature list is written BEFORE the runs are fired and
        stored with the results (EXCLUSION_SIGNATURES + provenance.pre_registered);
    (b) every excluded atom carries `exclusion_reason` AND `exclusion_evidence`
        (a literal error string or build status -- never a bare judgement call);
    (c) the report ALWAYS publishes `flake_rate_raw` (nothing excluded) beside
        `run_failure_rate` (exclusions applied). The gap between them IS the
        infrastructure cost and is quoted as such, not hidden.
  And: if exclusions exceed 20% of runs, the result is reported INCONCLUSIVE.

RULING 4 -- no rate is published below N=10, and every rate carries a 95% CI.
  At N=5, one failure is "20%" with a confidence interval from 1% to 62%. A bare
  point estimate at small N is the easiest thing in this benchmark for a skeptic
  to break, so `rates_flake` marks a result unpublishable below MIN_N and
  attaches a Wilson interval to every rate it emits.

RULING 5 -- unchanged-inputs attestation is part of the record.
  A repeat set MUST carry the suite git SHA, the target env identifier, and an
  explicit statement that no deploy/config change happened between runs. Without
  it, "identical runs" is an assumption and the number measures drift.
"""

MIN_N = 10
MAX_EXCLUSION_SHARE = 0.20

STABLE, FLAKY, BROKEN, INSUFFICIENT = "stable", "flaky", "broken", "insufficient"

# Pre-registered exclusion signatures. Anything NOT matching these is a real
# result, however inconvenient. Extend deliberately and date the change.
EXCLUSION_SIGNATURES = {
    "infra_crt_no_tests": {
        "match": "build reached a terminal status but executed 0 test cases",
        "why": "the suite never ran; this measures CRT, not the tests",
    },
    "infra_crt_aborted": {
        "match": "build status == 'aborted'",
        "why": "operator/platform abort, not a test outcome",
    },
    "infra_auth": {
        "match": ["invalid_client_id", "invalid_grant", "INVALID_SESSION_ID",
                  "expired access/refresh token", "INSUFFICIENT_ACCESS"],
        "why": "credential/JWT failure -- an environment fact, not suite flake",
    },
    "infra_target_env": {
        "match": ["UNABLE_TO_LOCK_ROW", "Server Unavailable", "503", "502",
                  "ECONNREFUSED", "REQUEST_LIMIT_EXCEEDED"],
        "why": "target org/app unavailable or rate-limited",
    },
    "concurrent_contention": {
        "match": "run overlapped a known contended shared resource "
                 "(e.g. this wave's shared Chrome on :9333)",
        "why": "a second agent was driving the same browser; the run is not "
               "independent and its wall clock is not comparable",
    },
}


def wilson(successes: int, n: int, z: float = 1.96):
    """95% Wilson score interval. Correct at small n, unlike the normal approx."""
    if not n:
        return (None, None)
    p = successes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round(max(0.0, (c - m) / d), 4), round(min(1.0, (c + m) / d), 4))


def classify_test_series(outcomes):
    """outcomes: list of 'pass'/'fail'/'skip' for ONE test across a repeat set."""
    real = [o for o in outcomes if o in ("pass", "fail")]
    if len(real) < 2:
        return INSUFFICIENT
    s = set(real)
    if s == {"pass"}:
        return STABLE
    if s == {"fail"}:
        return BROKEN
    return FLAKY


def _tally(rows, key, top=8):
    c = {}
    for r in rows:
        v = r.get(key)
        if v:
            c[str(v)[:160]] = c.get(str(v)[:160], 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])[:top]


def rates_flake(atoms, provenance=None):
    """Derive every published flake number from atoms.

    atoms: dicts with at least
      repeat_set, run_index, is_run_atom, test_name, outcome ('pass'|'fail'|'skip'),
      duration_s, queue_s, excluded (bool), exclusion_reason, exclusion_evidence,
      failing_step, failure_signature
    """
    runs = [a for a in atoms if a.get("is_run_atom")]
    tests = [a for a in atoms if not a.get("is_run_atom")]

    n_runs_raw = len(runs)
    excluded_runs = [a for a in runs if a.get("excluded")]
    eligible = [a for a in runs if not a.get("excluded")]
    n = len(eligible)

    def run_failed(run_idx):
        return any(t.get("outcome") == "fail" for t in tests
                   if t.get("run_index") == run_idx)

    raw_fail = sum(1 for r in runs
                   if run_failed(r.get("run_index")) or r.get("outcome") == "fail")
    elig_fail = sum(1 for r in eligible
                    if run_failed(r.get("run_index")) or r.get("outcome") == "fail")

    series = {}
    for t in tests:
        if t.get("excluded"):
            continue
        series.setdefault(t.get("test_name"), []).append(t.get("outcome"))
    classes = {k: classify_test_series(v) for k, v in series.items()}
    counted = {k: v for k, v in classes.items() if v != INSUFFICIENT}
    n_flaky = sum(1 for v in counted.values() if v == FLAKY)
    n_broken = sum(1 for v in counted.values() if v == BROKEN)

    # A test that is red in EVERY run is a defect, not flake. A run that is red
    # only because of such a test is not a flaky run -- it is a correctly red
    # run. Reporting only `run_failure_rate` would let one genuinely broken test
    # pin the flake number at 100% and hide the real variance underneath it.
    broken_names = {k for k, v in classes.items() if v == BROKEN}
    flaky_only_fail = sum(
        1 for r in eligible
        if any(t.get("outcome") == "fail" and t.get("test_name") not in broken_names
               for t in tests if t.get("run_index") == r.get("run_index"))
    )

    durs = sorted(a["duration_s"] for a in eligible if a.get("duration_s"))
    queues = sorted(a["queue_s"] for a in eligible if a.get("queue_s") is not None)

    def med(v):
        return None if not v else round(v[len(v) // 2], 1)

    excl_share = round(len(excluded_runs) / n_runs_raw, 4) if n_runs_raw else None
    out = {
        "schema": "flake/1.0.0",
        "n_runs_raw": n_runs_raw,
        "n_runs_eligible": n,
        "n_runs_excluded": len(excluded_runs),
        "exclusion_share": excl_share,
        "exclusions_by_reason": _tally(excluded_runs, "exclusion_reason"),
        # RULING 3(c): both numbers, always, side by side
        "run_failure_rate": round(elig_fail / n, 4) if n else None,
        "run_failure_rate_ci95": wilson(elig_fail, n) if n else None,
        # the honest flake headline: red runs NOT explained by a consistently
        # broken test. Quote this as "flake"; quote run_failure_rate as "red rate".
        "run_flake_rate": round(flaky_only_fail / n, 4) if n else None,
        "run_flake_rate_ci95": wilson(flaky_only_fail, n) if n else None,
        "flake_rate_raw": round(raw_fail / n_runs_raw, 4) if n_runs_raw else None,
        "infrastructure_cost": (round(raw_fail / n_runs_raw - elig_fail / n, 4)
                                if n and n_runs_raw else None),
        "expected_runs_per_green": (round(1 / (1 - elig_fail / n), 2)
                                    if n and elig_fail < n else None),
        "tests_observed": len(classes),
        "tests_classified": len(counted),
        "tests_stable": sum(1 for v in counted.values() if v == STABLE),
        "tests_flaky": n_flaky,
        "tests_broken": n_broken,
        "flaky_test_share": round(n_flaky / len(counted), 4) if counted else None,
        "flaky_test_share_ci95": wilson(n_flaky, len(counted)) if counted else None,
        "flaky_tests": sorted(k for k, v in classes.items() if v == FLAKY),
        "broken_tests": sorted(k for k, v in classes.items() if v == BROKEN),
        "top_failure_signatures": _tally(
            [t for t in tests if t.get("outcome") == "fail"], "failure_signature"),
        "top_failing_steps": _tally(
            [t for t in tests if t.get("outcome") == "fail"], "failing_step"),
        "duration_s_median": med(durs),
        "duration_s_min": durs[0] if durs else None,
        "duration_s_max": durs[-1] if durs else None,
        "duration_s_spread": (round(durs[-1] - durs[0], 1) if durs else None),
        "queue_s_median": med(queues),
        "provenance": provenance or {},
    }
    verdict = []
    if n < MIN_N:
        verdict.append(f"UNDERPOWERED: n={n} eligible runs, minimum is {MIN_N}. "
                       "Rates shown for information only; do not quote them.")
    if excl_share is not None and excl_share > MAX_EXCLUSION_SHARE:
        verdict.append(f"INCONCLUSIVE: {excl_share:.0%} of runs excluded as "
                       "infrastructure, above the 20% ceiling. This measures the "
                       "platform's availability more than the suite's flake.")
    prov = provenance or {}
    for req in ("suite_git_sha", "target_env", "no_changes_between_runs",
                "pre_registered"):
        if req not in prov:
            verdict.append(f"UNATTESTED: provenance.{req} missing (RULING 5).")
    out["publishable"] = not verdict
    out["verdict_notes"] = verdict
    return out
