import re

from bs4 import BeautifulSoup, Comment, NavigableString

# F226 (corrected 2026-09-20). A capture serialises every open shadow root as
# `<template shadowrootmode="open">`, and bs4 >= 4.10 types every string inside a <template> as
# TemplateString, which `get_text()` drops by default -- correctly, for a real template, whose
# content is inert and never rendered. A declarative shadow root is NOT inert: the browser renders
# it, and it is where most of a Lightning page's text lives. So text extraction must ask for those
# strings back.
#
# `capture_orchestration._pierced_text` has done exactly this since 2026-09-11 with
# `types=(NavigableString, TemplateString)` -- the mechanism was already right and already here.
# It was wired into ONE call site (the datatable grid-cell rule) because the measurement taken
# that day, over 17 industry captures, read "the compiler's own label rungs are NOT affected".
# That conclusion did not hold: a radio labelled through `aria-labelledby` resolves through THIS
# function, and its label sits inside a shadow root. One mechanism, not two -- this is the same
# call, not a second implementation of it.
try:                                     # bs4 >= 4.10
    from bs4.element import TemplateString as _TemplateString
    _TEXT_TYPES = (NavigableString, _TemplateString)
except ImportError:                      # older bs4: template strings are plain NavigableStrings
    _TEXT_TYPES = (NavigableString,)

class DomTextEngine:
    CSS_POISON_PATTERNS = ['--sds-', '--slds-', '--SBQQ-', '@layer', '{--']

    def _get_safe_text(self, tag, max_len=300) -> str:
        if not tag:
            return ''
        try:
            cloned = BeautifulSoup(str(tag), 'html.parser').find(tag.name)
            if cloned:
                for noise in cloned.find_all(['style', 'script', 'svg', 'canvas', 'iframe', 'noscript']):
                    noise.decompose()
                # bs4's Comment class is itself a NavigableString subclass,
                # so plain get_text() includes HTML comment contents (e.g.
                # Aura's own "<!--render facet: N:M;a-->" scaffolding) as if
                # it were real text -- confirmed live 2026-07-29 leaking
                # into a Files table cell's extracted value. Must be
                # decomposed explicitly, same as style/script above.
                for comment in cloned.find_all(string=lambda s: isinstance(s, Comment)):
                    comment.extract()
                raw = cloned.get_text(separator=' ', strip=True, types=_TEXT_TYPES)
            else:
                raw = tag.get_text(separator=' ', strip=True, types=_TEXT_TYPES)
        except Exception:
            raw = tag.get_text(separator=' ', strip=True)

        raw = re.sub(r'\s+', ' ', raw).strip()
        if len(raw) > max_len:
            return ''
        for poison in self.CSS_POISON_PATTERNS:
            if poison in raw:
                return ''
        return raw

    def _get_direct_text(self, tag, max_len=150) -> str:
        if not tag:
            return ''
        parts = []
        for node in tag.children:
            if isinstance(node, NavigableString) and not isinstance(node, Comment):
                text = node.strip()
                if text:
                    parts.append(text)
        raw = ' '.join(parts).strip()
        raw = re.sub(r'\s+', ' ', raw)
        if len(raw) > max_len:
            return ''
        for poison in self.CSS_POISON_PATTERNS:
            if poison in raw:
                return ''
        return raw