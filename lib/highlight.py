import re
import warnings

import markdown
import pygments.lexers
from pygments.formatters.html import _get_ttype_class, escape_html

CLASS = 'chl'
_TOKEN_CLASS_MAP = {}


def _token_to_class(token):
    try:
        return _TOKEN_CLASS_MAP[token]
    except KeyError:
        pass
    out = _get_ttype_class(token)
    _TOKEN_CLASS_MAP[token] = out
    return out


def _span(class_, code):
    if not code:
        return []
    if not class_:
        return [code]
    return ['<span class="{}">'.format(class_), code, '</span>']


def _format_lines(tokens):
    line = []
    for token, text in tokens:
        class_ = _token_to_class(token)
        escaped = escape_html(text).split('\n')
        if len(escaped) == 1:
            line += _span(class_, escaped[0])
            continue
        first, *middle, last = escaped
        yield "".join(line + _span(class_, first))
        yield from ("".join(_span(class_, mid)) for mid in middle)
        line = _span(class_, last)
    if line:
        yield "".join(line)


def tohtml(code, language, start_line=1):
    try:
        lexer = pygments.lexers.get_lexer_by_name(language)
    except pygments.util.ClassNotFound:
        warnings.warn("unknown language: " + language)
        lexer = pygments.lexers.get_lexer_by_name('text')
    lines = list(_format_lines(lexer.get_tokens(code)))
    numbers = (
        '<code class="line-numbers">'
        + "\n".join(str(n) for n in range(start_line, start_line + len(lines)))
        + '</code>'
    )
    highlighted = "".join([
        '<code class="highlighted-code">', '\n'.join(lines), '</code>',
    ])
    return "".join([
        f'<pre class="{CLASS}">', numbers, highlighted, '</pre>',
    ])


class CodeBlock(markdown.preprocessors.Preprocessor):
    def __init__(self, md):
        super().__init__(md)
        self._start = re.compile(r'^\s*```')
        self._end = re.compile(r'```\s*$')
        self._config = re.compile(r'(?P<language>\w*)\s*')

    def run(self, lines):
        out, lines = [], list(reversed(lines))
        while lines:
            line = lines.pop()
            start_match = self._start.match(line)
            if not start_match:
                out.append(line)
                continue
            first_line = line
            config = self._config.match(self._start.sub('', line))
            language = config.group('language') or 'text'
            code = []
            while True:
                if not lines:
                    # Failed to find closing code block.
                    out.append(first_line)
                    lines = list(reversed(code))
                    break
                line = lines.pop()
                if self._end.search(line):
                    code.append(self._end.sub('', line))
                    html = tohtml('\n'.join(code), language)
                    out.append(self.md.htmlStash.store(html))
                    break
                code.append(line)
        return out


class Extension(markdown.extensions.Extension):
    config = {}

    def extendMarkdown(self, md):
        # Priority matches "fenced_code" extension, since this is essentially a
        # replacement of that one.
        md.preprocessors.register(CodeBlock(md), 'code-block', 25)
        md.registerExtension(self)
