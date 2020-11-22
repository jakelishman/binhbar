import os
import pathlib
import re
import subprocess
from xml.etree import ElementTree as etree

import markdown


_NODEBIN = pathlib.Path('node_modules/.bin')
_KATEX = (pathlib.Path(__file__).parents[1] / _NODEBIN / 'katex').absolute()
if not (_KATEX.is_file() and os.access(_KATEX, os.X_OK)):
    raise ImportError("Could not locate KaTeX binary.")


def tohtml(latex, inline):
    args = (_KATEX,) + (() if inline else ('-d',))
    result = subprocess.run(args, input=latex, text=True, capture_output=True,
                            check=False)
    if result.returncode != 0:
        raise OSError(f"KaTeX failed on input:\n\n{latex}\n\n{result.stderr}")
    return result.stdout.strip()


def stash_mathml(stash, element):
    """
    Stash the MathML component of KaTeX output in pymarkdown's HTML stash,
    replacing the stashed element with a temporary tag that is reinserted at
    the XML-to-string conversion step.
    """
    subspan = list(element)[0]
    if subspan.get('class') == 'katex-mathml':
        mathml = subspan
        parent = element
    else:
        parent = subspan
        for mathml in parent:
            if mathml.get('class') == 'katex-mathml':
                break
        else:
            estr = etree.tostring(element, encoding="unicode")
            raise ValueError("could not find the MathML span in: " + estr)
    placeholder = stash.store(etree.tostring(mathml, encoding="unicode"))
    parent.remove(mathml)
    parent.text = placeholder + (parent.text or "")


class KaTeXInline(markdown.inlinepatterns.InlineProcessor):
    def __init__(self, md):
        pattern = r'\$`(.*?)`\$'
        super().__init__(pattern, md)

    def handleMatch(self, m, data):
        el = etree.fromstring(tohtml(m.group(1), inline=True))
        stash_mathml(self.md.htmlStash, el)
        return el, m.start(0), m.end(0)


class KaTeXBlock(markdown.blockprocessors.BlockProcessor):
    def __init__(self, md, *args, **kwargs):
        self._start = re.compile(r'^\s*\\\[')
        self._end = re.compile(r'\\\]\s*$')
        self.md = md
        super().__init__(md.parser, *args, **kwargs)

    def test(self, parent, block):
        return self._start.match(block)

    def run(self, parent, blocks):
        original_first = blocks[0]
        n_blocks = 0
        blocks[0] = self._start.sub('', blocks[0])
        out = []
        for block in blocks:
            n_blocks += 1
            if self._end.search(block):
                out.append(self._end.sub('', block))
                break
            out.append(block)
        else:
            # Failed to find end pattern.
            blocks[0] = original_first
            return False
        del blocks[:n_blocks]
        el = etree.fromstring(tohtml("\n".join(out), inline=False))
        stash_mathml(self.md.htmlStash, el)
        parent.append(el)
        return True


class Extension(markdown.extensions.Extension):
    config = {}

    def extendMarkdown(self, md):
        # Backtick processor is priority 190, and we need to be higher.
        md.inlinePatterns.register(KaTeXInline(md), 'katex-inline', 200)
        # This priority is pretty much entirely arbitrary, so long as it's
        # higher than paragraph (10).
        md.parser.blockprocessors.register(KaTeXBlock(md), 'katex-block', 200)
        md.registerExtension(self)
