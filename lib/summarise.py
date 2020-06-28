import markdown
from xml.etree import ElementTree as etree


class SummariseTreeprocessor(markdown.treeprocessors.Treeprocessor):
    min_blocks = 1
    max_blocks = 3

    def _lower_heading_levels(self, root):
        for n in [5, 4, 3, 2]:
            old, new = f'h{n}', f'h{n+1}'
            for element in root.iter(old):
                element.tag = new

    def _summarise(self, root):
        blocks = ['p', 'ol', 'ul', 'blockquote']
        limiters = [f'h{n}' for n in range(1, 7)] + ['hr']
        seen_blocks = 0
        out = etree.Element(root.tag, root.attrib.copy())
        for child in root:
            if ((child.tag in limiters and seen_blocks >= self.min_blocks)
                    or (seen_blocks >= self.max_blocks)):
                break
            if child.tag in blocks:
                seen_blocks += 1
            out.append(child)
        return out

    def run(self, root):
        self._lower_heading_levels(root)
        return self._summarise(root)


class Extension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        summariser = SummariseTreeprocessor(md)
        md.treeprocessors.register(summariser, 'summarise', 900)
        md.registerExtension(self)
