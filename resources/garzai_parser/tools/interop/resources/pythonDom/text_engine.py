import re
from bs4 import BeautifulSoup, Comment, NavigableString

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
                raw = cloned.get_text(separator=' ', strip=True)
            else:
                raw = tag.get_text(separator=' ', strip=True)
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