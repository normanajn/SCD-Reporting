from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import markdown as md_lib


ALLOWED_TAGS = {
    'a', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'hr',
    'li', 'ol', 'p', 'pre', 'strong', 'table', 'tbody', 'td', 'th',
    'thead', 'tr', 'ul',
}
ALLOWED_ATTRS = {
    'a': {'href', 'title'},
    'td': {'align'},
    'th': {'align'},
}
ALLOWED_PROTOCOLS = {'', 'http', 'https', 'mailto'}


class _MarkdownSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self._append_starttag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self.parts.append('<br>')
        elif tag == 'hr':
            self.parts.append('<hr>')
        else:
            self._append_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in {'br', 'hr'}:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def get_html(self):
        return ''.join(self.parts)

    def _append_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        clean_attrs = []
        for name, value in attrs:
            if name not in ALLOWED_ATTRS.get(tag, set()):
                continue
            value = value or ''
            if name == 'href' and urlparse(value).scheme not in ALLOWED_PROTOCOLS:
                continue
            clean_attrs.append(f' {name}="{escape(value, quote=True)}"')
        self.parts.append(f'<{tag}{"".join(clean_attrs)}>')


def render_markdown(text: str) -> str:
    html = md_lib.markdown(text or '', extensions=['fenced_code', 'tables'])
    sanitizer = _MarkdownSanitizer()
    sanitizer.feed(html)
    sanitizer.close()
    return sanitizer.get_html()
