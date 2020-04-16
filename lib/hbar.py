import ast
import codecs
import collections
import datetime
import glob
import itertools
import os
import pathlib
import shutil
import string
import zlib

from xml.etree import ElementTree as ET

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
import unidecode

__all__ = ['add_all_articles', 'add_article', 'tidy_up', 'deploy_site']

ARTICLES_DIRECTORY = pathlib.Path('articles')
INFO_FILE = pathlib.Path('__article__.py')
CONTENT_FILE = pathlib.Path('article.md')
STORE_FILE = pathlib.Path('.hbar-store')
TEMPLATE_DIRECTORY = pathlib.Path('template')
TEMPLATE_HTML = pathlib.Path('index.html')
TEMPLATE_ABOUT_MD = pathlib.Path('about/index.md')
DEPLOY_DIRECTORY = pathlib.Path('deploy')
POSTS_DIRECTORY = pathlib.Path('posts')

IGNORED_ARTICLE_FILES = [str(INFO_FILE), str(CONTENT_FILE), str(STORE_FILE)]
IGNORED_TEMPLATE_FILES = [str(TEMPLATE_HTML), str(TEMPLATE_ABOUT_MD.name)]


class _CodeHiliteExtension(CodeHiliteExtension):
    def __init__(self, **kwargs):
        # Overriding the value of 'linenums' to be 'inline'.  The extension
        # __init__ method only allows True and False values unless the default
        # is not None, True or False.
        self.config = {
            'linenums': ['inline', ""],
            'guess_lang': [False, ""],
            'css_class': ["chl", ""],
            'pygments_style': ['solarized-dark', ''],
            'noclasses': [False, ''],
            'use_pygments': [True, '']
        }
        super(CodeHiliteExtension, self).__init__(**kwargs)


class SummariseTreeprocessor(markdown.treeprocessors.Treeprocessor):
    min_blocks = 1
    max_blocks = 3

    def _lower_heading_levels(self, root):
        for n in [5, 4, 3, 2]:
            old, new = f'h{n}', f'h{n+1}'
            for element in root.iter(old):
                element.tag = new

    def _summarise(self, root):
        blocks = ['p', 'ol', 'li']
        headings = [f'h{n}' for n in range(1, 7)]
        seen_blocks = 0
        out = ET.Element(root.tag, root.attrib.copy())
        for child in root:
            if (child.tag in headings and seen_blocks >= self.min_blocks
                    or seen_blocks >= self.max_blocks):
                break
            if child.tag in blocks:
                seen_blocks += 1
            out.append(child)
        return out

    def run(self, root):
        self._lower_heading_levels(root)
        return self._summarise(root)


class SummariseExtension(markdown.extensions.Extension):
    config = {}

    def extendMarkdown(self, md):
        summariser = SummariseTreeprocessor(md)
        md.treeprocessors.register(summariser, 'summarise', 900)
        md.registerExtension(self)


def _markdown_extensions(summarise):
    out = ['fenced_code', 'smarty', _CodeHiliteExtension()]
    if summarise:
        out.append(SummariseExtension())
    return out


_markdown = markdown.Markdown(output_format='html',
                              extensions=_markdown_extensions(False))
_summarise = markdown.Markdown(output_format='html',
                               extensions=_markdown_extensions(True))


def cast_list(type_):
    def cast(in_):
        return list(map(type_, in_))
    return cast


INFO_NECESSARY = {
    "title": str,
    "date": lambda x: datetime.datetime.fromisoformat(x).isoformat(),
    "tags": cast_list(str),
    "id": str,
}
INFO_OPTIONAL = {
    "short title": str,
    "edits": cast_list(str),
    "related": cast_list(str),
}
INFO_COMPUTED = {
    "checksum", "markdown", "summary", "output path", "input path"
}
INFO_ALL = set(INFO_NECESSARY) | set(INFO_OPTIONAL) | INFO_COMPUTED


def _validate_info_file(info):
    out = {}
    missing, bad_type = [], []
    for key, type_cast in INFO_NECESSARY.items():
        try:
            out[key] = type_cast(info[key])
        except KeyError:
            missing.append(key)
        except TypeError:
            bad_type.append(key)
    for key, type_cast in INFO_OPTIONAL.items():
        if key in info:
            try:
                out[key] = type_cast(info[key])
            except TypeError:
                bad_type.append(key)
    if missing or bad_type:
        message = "".join(["Missing keys: ", repr(missing),
                           ", bad types: ", repr(bad_type)])
        raise ValueError(message)
    return out


def _parse_info_file(path):
    with open(path, "r") as file:
        contents = file.read()
    info = ast.literal_eval(contents)
    return _validate_info_file(info)


def _checksum_directory(directory, exclude=None):
    exclude = set(exclude or [])
    previous_directory = os.getcwd()
    all_paths = []
    try:
        os.chdir(directory)
        for root, _, files in os.walk('.'):
            root_path = pathlib.Path(root)
            all_paths.extend([root_path/file for file in files
                              if file not in exclude])
        hash_ = 0
        for path in all_paths:
            with open(path, "rb") as f:
                hash_ = zlib.crc32(f.read(), hash_)
    finally:
        os.chdir(previous_directory)
    return hash_


def _url_sanitise_title(info):
    title = info['short title'] if 'short title' in info else info['title']
    return "".join(
        char for char in unidecode.unidecode(title.lower()).replace(" ", "-")
        if char.isalnum() or char == "-"
    )


def add_article(path):
    path = pathlib.Path(path)
    if not (path.exists() and path.is_dir()):
        raise ValueError("Could not access directory " + path.name + ".")
    store = path / STORE_FILE
    checksum = _checksum_directory(path, exclude=[STORE_FILE.name])
    store_info = None
    if store.exists():
        try:
            with open(store, "r") as f:
                store_info = ast.literal_eval(f.read())
            if store_info['checksum'] == checksum:
                return 0
        except (SyntaxError, OSError):
            pass
    info = _parse_info_file(path / INFO_FILE)
    if store_info:
        store_info.update(info)
        info = store_info
    info["checksum"] = checksum
    with codecs.open(path / CONTENT_FILE, mode="r", encoding="utf-8") as file:
        article = file.read()
    _markdown.reset()
    _summarise.reset()
    info["markdown"] = _markdown.convert(article)
    info["summary"] = _summarise.convert(article)
    info["input path"] = str(path)
    date = datetime.datetime.fromisoformat(info["date"])
    if "output path" not in info:
        info["output path"] = str(POSTS_DIRECTORY
                                  / date.strftime("%Y/%m")
                                  / _url_sanitise_title(info))
    with open(store, "w") as f:
        print(str(info), file=f)
    return 0


def add_all_articles():
    base = ARTICLES_DIRECTORY
    exit_code = 0
    for article in glob.glob(str(base/'**'/INFO_FILE), recursive=True):
        try:
            add_article(pathlib.Path(article).parent)
        except ValueError:
            exit_code += 1
    return exit_code


def tidy_up():
    pass


def _canonical_abs(path):
    path = str(path).strip("/")
    if not path:
        return "/"
    return "/" + path + "/"


def _html_byline(date):
    ordinal = 'th'
    if date.day in (1, 21, 31):
        ordinal = 'st'
    elif date.day in (2, 22):
        ordinal = 'nd'
    elif date.day in (3, 23):
        ordinal = 'rd'
    day_string = str(date.day) + ordinal
    return ''.join([
        '<span class="byline">',
        'by <span class="author" itemprop="author">Jake Lishman</span>',
        ' on the ',
        '<time datetime="', date.isoformat(), '">',
        day_string, ' of ', date.strftime('%B, %Y'),
        '</time>.</span>',
    ])


def _html_summary(info):
    title = ''.join([
        '<h2 class="article-title">',
        '<a href="/', info['output path'], '/">',
        info['title'],
        '</a></h2>',
    ])
    if info['summary'] == info['markdown']:
        read_more = ''
    else:
        read_more = ''.join([
            '<footer><p class="read-more">',
            '<a href="', _canonical_abs(info['output path']), '">',
            'Read more&#8230;</a></p></footer>',
        ])
    return ''.join([
        '<article class="summary" itemscope>',
        '<header>', title, _html_byline(info['date']), '</header>',
        '<div class="article-summary-text">', info['summary'], '</div>',
        read_more,
        '</article>',
    ])


def _html_tag_list(tags):
    tags = sorted(((len(ids), tag) for tag, ids in tags.items()), reverse=True)
    return ''.join(
        ''.join([
            '<li><a href="', _canonical_abs('/tags/' + tag), '">',
            tag, ' <span class="tag-count">(', str(count), ')</span>',
            '</a></li>'
        ])
        for count, tag in tags
    )


def _html_recent_posts(articles, count):
    def item(info):
        return ''.join([
            '<li>',
            '<a href="', _canonical_abs(info['output path']), '">',
            info['title'],
            '</a>', '</li>',
        ])
    recent = sorted(articles.values(), key=lambda x: x['date'], reverse=True)
    return ''.join(item(info) for info in recent[:count])


def _html_article(article_id, articles):
    info = articles[article_id]
    header = ''.join([
        '<header>',
        '<h1>', '<a href="', _canonical_abs(info['output path']), '">',
        info['title'],
        '</a>', '</h1>',
        _html_byline(info['date']),
        '</header>',
    ])
    return ''.join([
        '<article itemscope>',
        header,
        '<div id="article-text">', info['markdown'], '</div>',
        '<footer></footer>',
        '</article>',
    ])


def _html_list_footer(path, page, n_pages):
    older = younger = ''
    if page > 1:
        previous_link = path
        if page > 2:
            previous_link += "/page/" + str(page - 1)
        younger = ''.join([
            '<a href="', _canonical_abs(previous_link), '">',
            '&#8230;more recent posts',
            '</a>',
        ])
    if page < n_pages:
        next_link = path + "/page/" + str(page + 1)
        older = ''.join([
            '<a href="', _canonical_abs(next_link), '">',
            'older posts&#8230;',
            '</a>',
        ])
    links = younger
    if links and older:
        links += '<span class="page-link-separator"> | </span>'
    links += older
    return ''.join(['<span id="list-page-navigation">', links, '</span>'])


def _deploy_article(article_id, articles, template):
    info = articles[article_id]
    output_path = pathlib.Path(info["output path"])
    os.makedirs(output_path.parent, exist_ok=True)
    shutil.copytree(info["input path"], DEPLOY_DIRECTORY / output_path,
                    ignore=lambda *_: IGNORED_ARTICLE_FILES)
    output = template.substitute({
        'head_title': info["title"],
        'content': _html_article(article_id, articles),
    })
    with open(DEPLOY_DIRECTORY / output_path / "index.html", "w") as file:
        file.write(output)


def _chunk(sequence, n):
    sequence = tuple(sequence)
    n_chunks = (len(sequence) + (n-1)) // n
    iterator = iter(sequence)
    for _ in [None]*n_chunks:
        yield tuple(itertools.islice(iterator, n))


def _deploy_list(article_infos, template, title, path, head_title=None):
    path = path.strip("/")
    head_title = head_title or title
    chronological = sorted(article_infos,
                           key=lambda x: x['date'], reverse=True)
    chunks = list(_chunk(chronological, 5))
    n_chunks = len(chunks)
    for n, articles in enumerate(chunks):
        output_directory = pathlib.Path(path)
        if n > 0:
            output_directory = output_directory / "page" / str(n+1)
        header = ''.join([
            '<header>',
            '<h1>', '<a href="/', str(output_directory), '/">',
            title,
            '</a></h1></header>',
        ])
        content = ''.join(_html_summary(article) for article in articles)
        footer = _html_list_footer(path, n+1, n_chunks)
        content = ''.join([header, content, footer])
        output = template.substitute({
            'head_title': head_title,
            'content': content,
        })
        deploy_directory = DEPLOY_DIRECTORY / output_directory
        os.makedirs(deploy_directory, exist_ok=True)
        with open(deploy_directory / "index.html", "w") as file:
            file.write(output)


def _deploy_main_page(articles, template):
    _deploy_list(articles.values(), template, "Recent posts", "/",
                 head_title="Jake Lishman")


def _deploy_articles(articles, template):
    for article_id in articles:
        _deploy_article(article_id, articles, template)


def _deploy_tags(tags, articles, template):
    for tag, article_ids in tags.items():
        _deploy_list((articles[article_id] for article_id in article_ids),
                     template,
                     "Posts tagged '" + tag + "'",
                     "/tags/" + tag + "/")


def _deploy_about(template):
    with open(TEMPLATE_DIRECTORY / TEMPLATE_ABOUT_MD, "r") as file:
        about = file.read().strip()
    _markdown.reset()
    output = template.substitute({
        'head_title': 'Jake Lishman',
        'content': _markdown.convert(about),
    })
    output_directory = DEPLOY_DIRECTORY / "about"
    os.makedirs(output_directory, exist_ok=True)
    with open(output_directory / "index.html", "w") as file:
        file.write(output)


def deploy_site():
    tags = collections.defaultdict(list)
    articles = {}
    summaries = {}

    with open(STORE_FILE, "r") as global_store:
        article_locations = ast.literal_eval(global_store.read().strip())
    for article_id, location in article_locations.items():
        with open(location / STORE_FILE, "r") as file:
            info = ast.literal_eval(file.read().strip())
        info['date'] = datetime.datetime.fromisoformat(info['date'])
        articles[article_id] = info

    for article_id, info in articles.items():
        for tag in info["tags"]:
            tags[tag].append(article_id)
        summaries[article_id] = _html_summary(info)

    with open(TEMPLATE_DIRECTORY / TEMPLATE_HTML, "r") as file:
        template = string.Template(file.read().strip())
    template = string.Template(template.safe_substitute({
        'tags': _html_tag_list(tags),
        'recent_posts': _html_recent_posts(articles, count=5),
    }))

    shutil.rmtree(DEPLOY_DIRECTORY)
    shutil.copytree(TEMPLATE_DIRECTORY, DEPLOY_DIRECTORY,
                    ignore=lambda *_: IGNORED_TEMPLATE_FILES)
    _deploy_main_page(articles, template)
    _deploy_articles(articles, template)
    _deploy_tags(tags, articles, template)
    _deploy_about(template)
    return 0
