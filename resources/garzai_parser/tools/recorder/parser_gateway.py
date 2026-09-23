"""The ONE late-bound way to reach `capture_orchestration.parse_elements_from_html`.

    from parser_gateway import parse_elements_from_html      # instead of from capture_orchestration

Library only -- no CLI, nothing to run.

WHY (2026-09-23, F250; error-ledger entry `155c8ab4c5`). `from capture_orchestration import
parse_elements_from_html` at module level binds ONE function object for the life of the process.
This repo's own test harness deliberately throws that object away, in two places:

  * `tools/recorder/tests/templates/test_parser_families_2026_09_07.py::_reload_python_dom` pops
    `capture_orchestration` / `component_classifier` / `dom_config` / `element_compiler` /
    `text_engine` out of `sys.modules` and reimports them so each of its cases parses with a clean
    template. A clean reimport per case is exactly what that file MEASURES, so it is not the thing
    to change.
  * `tools/recorder/tests/conftest.py::_one_bs4_per_test` purges the same five modules plus `bs4`
    and `soupsieve` at the START OF EVERY TEST once the vendored parser has been imported -- the
    2026-09-07 fix for the two-live-bs4 bug ("Expected a BeautifulSoup 'Tag', but instead received
    type <class 'bs4.BeautifulSoup'>", 9 reds in random order only).

Either purge STRANDS every by-value holder: the holder keeps calling a function whose module,
classes and bs4 are no longer the ones anything else is using, so the same capture parses into
different rows depending on which test ran first, and the red names a COUNT rather than a cause.
Measured 2026-09-23: 5 reds in `test_compose_live.py` and 2 in
`templates/test_label_policy_visible_text_wins_p1_2026_09_07.py` that each passed when their own
file ran alone, plus a wider cluster under a different random seed once more consumers were in the
order. The ledger names two candidate fixes; this is the second ("import the module rather than the
function"), chosen because the first would have to change what the polluting test measures, and
because this fixes every consumer at once instead of the handful that happened to be noticed.

`importlib.import_module` consults `sys.modules` first, so the cost is a dict lookup per call and
the answer is always the module the rest of the process is using. A function-LOCAL
`from capture_orchestration import ...` inside the caller is already equivalent and needs nothing;
a MODULE-LEVEL one is the bug.
"""
from __future__ import annotations

import importlib

__all__ = ["parse_elements_from_html"]


def parse_elements_from_html(*args, **kwargs):
    """`capture_orchestration.parse_elements_from_html`, resolved at CALL time. See this module's
    docstring for why a module-level by-value import of it is a bug under this test harness."""
    return importlib.import_module("capture_orchestration").parse_elements_from_html(*args, **kwargs)
