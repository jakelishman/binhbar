import ast
import codecs
import collections
import datetime
import enum
import glob
import html
import os
import pathlib
import re
import shutil
import string
import zlib

import markdown
import unidecode
from css_html_js_minify import (
    html_minify as _minify_html,
    css_minify as _minify_css,
)

from . import katex, highlight, summarise

__all__ = ['update_all_articles', 'update_article', 'tidy_up', 'deploy_site']

ARTICLES_DIRECTORY = pathlib.Path('articles')
INFO_FILE = pathlib.Path('__article__.py')
CONTENT_FILE = pathlib.Path('article.md')
STORE_FILE = pathlib.Path('.hbar-store')
TEMPLATE_DIRECTORY = pathlib.Path('template')
TEMPLATE_HTML = pathlib.Path('index.html')
TEMPLATE_ABOUT_MD = pathlib.Path('about/index.md')
DEPLOY_DIRECTORY = pathlib.Path('deploy')
POSTS_DIRECTORY = pathlib.Path('posts')
ABOUT_DIRECTORY = pathlib.Path('about')

SITE = "https://binhbar.com"
FEED_LOCATION = "atom.xml"

IGNORED_ARTICLE_FILES = [str(INFO_FILE), str(CONTENT_FILE), str(STORE_FILE)]
IGNORED_TEMPLATE_FILES = [str(TEMPLATE_HTML), str(TEMPLATE_ABOUT_MD.name)]


def _canonical_abs(path, site=False, file=False):
    suffix = "" if file else "/"
    base = f"{SITE if site else ''}/"
    path = str(path).strip("/")
    if not path or path == ".":
        return base
    return f"{base}{path}{suffix}"


class Tabs(enum.Enum):
    Blog = enum.auto()
    About = enum.auto()


TAB_LIST = {
    Tabs.Blog: ("Blog", _canonical_abs("/")),
    Tabs.About: ("About me", _canonical_abs(str(ABOUT_DIRECTORY))),
}


def _markdown_extensions(summary):
    out = [
        'smarty',
        highlight.Extension(),
        katex.Extension(),
    ]
    if summary:
        out.append(summarise.Extension())
    return out


_markdown = markdown.Markdown(output_format='html',
                              extensions=_markdown_extensions(summary=False))
_summarise = markdown.Markdown(output_format='html',
                               extensions=_markdown_extensions(summary=True))

_url_tidyup_href = re.compile(r'href\s*=\s*(['"'"r'"])(.*?)\1')
_url_tidyup_slash = re.compile(r'([^:])/+')


class SiteState:
    def __init__(self, store_file, template_file):
        self.environment = {
            'about': _canonical_abs(str(ABOUT_DIRECTORY)),
        }
        self._summaries = {}
        self._tags = collections.defaultdict(list)
        self._tag_indices = {}

        articles = {}
        with open(STORE_FILE, "r") as global_store:
            lines = [line.strip() for line in global_store.readlines()]
            lines = [line for line in lines if line and line[0] != '#']
            article_locations = ast.literal_eval("".join(lines))
        for article_id, location in article_locations.items():
            with open(location / STORE_FILE, "r") as file:
                info = ast.literal_eval(file.read().strip())
            info['date'] = datetime.datetime.fromisoformat(info['date'])
            articles[article_id] = info
            self.environment['article_' + article_id] =\
                _canonical_abs(info['output path'])
        # Guaranteed to remain sorted by age now, so will remain so in future
        # iterations, like making the tags.
        self._articles = {
            id: articles[id]
            for id in sorted(articles, key=lambda id: articles[id]["date"])
        }

        for article_id, info in articles.items():
            for tag in info["tags"]:
                self._tags[tag].append(article_id)
        for tag, articles in self._tags.items():
            safe_tag = _sanitise_tag(tag)
            self.environment['tag_' + safe_tag] = "/tags/" + safe_tag + "/"
            self._tag_indices[tag] = {id: i for i, id in enumerate(articles)}

        for article_id, info in self._articles.items():
            self._summaries[article_id] = _html_summary(info, self.environment)

        with open(TEMPLATE_DIRECTORY / TEMPLATE_HTML, "r") as file:
            template = string.Template(file.read().strip())
        self._template = string.Template(template.safe_substitute({
            'tags': _html_tag_list(self._tags),
            'recent_posts': _html_recent_posts(self._articles.values(), count=10),
        }))

    def articles_by_tag(self, tag: str):
        """A sorted iterable from oldest to newest articles in a tag."""
        return tuple(self._tags[tag])

    def seek_in_tag(self, tag: str, base_article: str, offset: int):
        base = self._tag_indices[tag][base_article]
        index = base + offset
        if 0 <= index < len(self._tags[tag]):
            return self._tags[tag][index]
        return None

    def summary(self, article):
        return self._summaries[article]

    def apply_template(self, replacements):
        return self._template.substitute(replacements)

    def tags(self):
        return self._tags.keys()

    def article_ids(self):
        return self._articles.keys()

    def article_info(self, article_id):
        return self._articles[article_id]


def _url_tidyup(text):
    return _url_tidyup_href.sub(lambda m: _url_tidyup_slash.sub(r'\1/', m[0]), text)


def _postprocess_html(text):
    return _minify_html(_url_tidyup(text))


def cast_list(type_):
    def cast(in_):
        return list(map(type_, in_))
    return cast


def _normalise_date(x):
    iso = datetime.datetime.fromisoformat(x)
    if iso.tzinfo is None:
        iso = iso.astimezone(datetime.timezone.utc)
    return iso.isoformat()


INFO_NECESSARY = {
    "title": str,
    "date": _normalise_date,
    "tags": cast_list(str),
    "id": str,
}
INFO_OPTIONAL = {
    "short title": str,
    "edits": cast_list(str),
    "related": cast_list(str),
    "image": str,
    "image_alt": str,
    "description": str,
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


def update_article(path, *, vars):
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
            if store_info['checksum'] == checksum and not vars['force']:
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


def update_all_articles(*, vars):
    base = ARTICLES_DIRECTORY
    exit_code = 0
    for article in glob.glob(str(base/'**'/INFO_FILE), recursive=True):
        try:
            update_article(pathlib.Path(article).parent, vars=vars)
        except ValueError:
            exit_code += 1
    return exit_code


def tidy_up(*, vars):
    pass


def _copy_minified_html(src, dest):
    with open(src, "r") as input, open(dest, "w") as output:
        output.write(_postprocess_html(input.read()))


def _copy_minified_css(src, dest):
    with open(src, "r") as input, open(dest, "w") as output:
        output.write(_minify_css(input.read()))


_FILE_COPY_FILTERS = {
    '.html': _copy_minified_html,
    '.css': _copy_minified_css,
}


def _copy_with_filter(src, dest):
    extension = pathlib.Path(src).suffix.lower()
    return _FILE_COPY_FILTERS.get(extension, shutil.copy2)(src, dest)


def _sanitise_tag(tag):
    return "".join(
        char for char in unidecode.unidecode(tag.lower()).replace(" ", "-")
        if char.isalnum() or char == "-"
    )


def _meta_tag(name, content, attribute='name'):
    return rf'<meta {attribute}="{name}" content="{content}">'


def _html_meta_opengraph(article, title, path, description, image):
    image_path, image_alt = image
    image_path = _canonical_abs(image_path, site=True).rstrip('/')
    parts = [
        _meta_tag('og:title', title, 'property'),
        _meta_tag('og:url',  path, 'property'),
        _meta_tag('og:type', 'article' if article else 'website', 'property'),
        _meta_tag('og:locale', 'en_GB', 'property'),
        _meta_tag('og:image', image_path, 'property'),
        _meta_tag('og:image:alt', image_alt, 'property'),
        _meta_tag('twitter:card', 'summary_large_image', 'name'),
        _meta_tag('twitter:site', '@binhbar', 'name'),
        _meta_tag('twitter:creator', '@binhbar', 'name'),
    ]
    if description:
        parts.append(_meta_tag('og:description', description, 'property'))
    return parts


def _html_tabs(current_tab):
    return "".join(
        f'<li class="tab{" tab-current" if tab is current_tab else ""}">'
        f'<a href="{TAB_LIST[tab][1]}">{TAB_LIST[tab][0]}</a></li>'
        for tab in Tabs
    )


def _html_meta(info, article, title=None, path=None, description=None):
    path = _canonical_abs(path if path is not None else info["output path"],
                          site=True)
    title = title or info.get("short title", info["title"])
    description = description or info.get('description', None)
    if 'image' in info:
        image = path + info['image']
        alt = info.get('image_alt', description)
    else:
        image = '/images/preview.png'
        alt = "Title card for /bin/&#x127; and photograph of Jake Lishman"
    parts = _html_meta_opengraph(article, title, path, description, (image, alt))
    parts.append(_meta_tag('title', title))
    if description:
        parts.append(_meta_tag('description', description))
    return "".join(parts)


def _html_tagsline(tags):
    html_tags = ', '.join([
        ''.join([
            '<a href="', _canonical_abs('/tags/'+_sanitise_tag(tag)), '">',
            tag,
            '</a>',
        ])
        for tag in tags
    ])
    return ''.join([
        '<span class="tagsline">',
        'Tags: ',
        html_tags,
        '.</span>',
    ])


def _html_byline(date, tags):
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
        '</time>. ',
        _html_tagsline(tags),
        '</span>',
    ])


def _html_summary(info, environment):
    title = ''.join([
        '<h2 class="article-title">',
        '<a href="', _canonical_abs(info['output path']), '">',
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
    text = string.Template(info['summary']).safe_substitute({
        'article': _canonical_abs(info['output path']).rstrip('/'),
        **environment,
    })
    return ''.join([
        '<article class="summary" itemscope>',
        '<header>',
        title,
        _html_byline(info['date'], info['tags']),
        '</header>',
        '<div class="article-summary-text">', text, '</div>',
        read_more,
        '</article>',
    ])


def _html_tag_list(tags):
    tags = sorted(((len(ids), tag) for tag, ids in tags.items()), reverse=True)
    return ''.join(
        ''.join([
            '<li><a href="', _canonical_abs('/tags/'+_sanitise_tag(tag)), '">',
            tag, ' <span class="tag-count">(', str(count), ')</span>',
            '</a></li>'
        ])
        for count, tag in tags
    )


def _html_recent_posts(article_infos, count):
    def item(info):
        return ''.join([
            '<li>',
            '<a href="', _canonical_abs(info['output path']), '">',
            info['title'],
            '</a>', '</li>',
        ])
    recent = sorted(article_infos, key=lambda x: x['date'], reverse=True)
    return ''.join(item(info) for info in recent[:count])


def _html_article(article_id, state):
    info = state.article_info(article_id)
    header = ''.join([
        '<header id="main-header">',
        '<h1>', '<a href="', _canonical_abs(info['output path']), '">',
        info['title'],
        '</a>', '</h1>',
        _html_byline(info['date'], info['tags']),
        '</header>',
    ])

    def link(article_id):
        info = state.article_info(article_id)
        return ''.join([
            f'<a href="{_canonical_abs(info["output path"])}">',
            info.get("short title", info["title"]),
            '</a>',
        ])

    def tag_item(tag):
        older = state.seek_in_tag(tag, article_id, -1)
        newer = state.seek_in_tag(tag, article_id, 1)
        if older is None and newer is None:
            return ''
        return ''.join([
            '<section class="tag-nav">',
            '<h3>',
            f'<a href="{_canonical_abs("/tags/" + _sanitise_tag(tag))}">',
            tag,
            '</a>',
            '</h3>',
            '<div class="tag-nav-float">',
            '<section class="tag-nav-older">',
            '' if older is None else link(older),
            '</section>',
            '<section class="tag-nav-newer">',
            '' if newer is None else link(newer),
            '</section>',
            '</div>',
            '</section>',
        ])

    related = ''.join(tag_item(tag) for tag in info["tags"])
    if related:
        footer = ''.join([
            '<footer id="main-footer">',
            '<h2>Related posts</h2>',
            related,
            '</footer>',
        ])
    else:
        footer = ''
    text = string.Template(info['markdown']).safe_substitute({
        'article': state.environment['article_' + article_id],
        **state.environment,
    })
    return ''.join([
        '<article itemscope>',
        header,
        '<div id="article-text">', text, '</div>',
        footer,
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


def _deploy_article(article_id, state, description=None):
    info = state.article_info(article_id)
    output_path = pathlib.Path(info["output path"])
    shutil.copytree(info["input path"], DEPLOY_DIRECTORY / output_path,
                    ignore=lambda *_: IGNORED_ARTICLE_FILES)
    output = state.apply_template({
        'head_title': info["title"],
        'tabs': _html_tabs(Tabs.Blog),
        'meta': _html_meta(info, article=True, description=description),
        'content': _html_article(article_id, state),
    })
    with open(DEPLOY_DIRECTORY / output_path / "index.html", "w") as file:
        file.write(_postprocess_html(output))


def _chunk(sequence, n):
    sequence = tuple(sequence)
    return [sequence[ptr : ptr + n] for ptr in range(0, len(sequence), n)]


def _deploy_list(article_ids, state, title, path,
                 head_title=None, meta_title=None, description=None):
    path = path.strip("/")
    head_title = head_title or title
    chronological = sorted(
        article_ids, key=lambda x: state.article_info(x)['date'], reverse=True
    )
    chunks = list(_chunk(chronological, 10))
    n_chunks = len(chunks)
    for n, articles in enumerate(chunks):
        output_directory = pathlib.Path(path)
        if n > 0:
            output_directory = output_directory / "page" / str(n+1)
        header = ''.join([
            '<header id="main-header">',
            '<h1>', '<a href="', _canonical_abs(output_directory), '">',
            title,
            '</a></h1></header>',
        ])
        content = ''.join(state.summary(article) for article in articles)
        footer = _html_list_footer(path, n+1, n_chunks)
        content = ''.join([header, content, footer])
        output = state.apply_template({
            'head_title': head_title,
            'tabs': _html_tabs(Tabs.Blog),
            'meta': _html_meta(
                {}, article=False, title=meta_title or title,
                path=path, description=description,
            ),
            'content': content,
        })
        deploy_directory = DEPLOY_DIRECTORY / output_directory
        os.makedirs(deploy_directory, exist_ok=True)
        with open(deploy_directory / "index.html", "w") as file:
            file.write(_postprocess_html(output))


def _deploy_main_page(state):
    description = " ".join([
        "Research software developer at IBM Quantum.",
        "Posts about quantum software development and trapped-ion quantum computing.",
    ])
    _deploy_list(state.article_ids(), state, "Recent posts", "/",
                 head_title="Jake Lishman", meta_title="Blog of Jake Lishman",
                 description=description)


def _deploy_articles(state):
    for article_id in state.article_ids():
        _deploy_article(article_id, state)


def _deploy_tags(state):
    for tag in state.tags():
        _deploy_list(state.articles_by_tag(tag),
                     state,
                     f"Posts tagged ‘{tag}’",
                     state.environment['tag_' + _sanitise_tag(tag)])


def _deploy_about(state):
    with open(TEMPLATE_DIRECTORY / TEMPLATE_ABOUT_MD, "r") as file:
        about = file.read().strip()
    _markdown.reset()
    content = _markdown.convert(about)
    path = _canonical_abs(str(ABOUT_DIRECTORY))
    output = state.apply_template({
        'head_title': 'Jake Lishman',
        'tabs': _html_tabs(Tabs.About),
        'meta': _html_meta({}, article=False, title="Jake Lishman", path=path),
        'content': string.Template(content).safe_substitute(state.environment),
    })
    output_directory = DEPLOY_DIRECTORY / ABOUT_DIRECTORY
    os.makedirs(output_directory, exist_ok=True)
    with open(output_directory / "index.html", "w") as file:
        file.write(_postprocess_html(output))


def _make_feed_entry(state, article_id):
    info = state.article_info(article_id)
    path = _canonical_abs(info["output path"], site=True)
    return "\n".join([
        "<entry>",
        f'<title>{info["title"]}</title>',
        f'<link rel="alternate" href="{path}"/>',
        f'<id>{path}</id>',
        f'<updated>{info["date"].isoformat()}</updated>',
        '<summary type="html">',
        html.escape(info["summary"]),
        '</summary>',
        ''.join(f'<category term="{tag}"/>' for tag in info["tags"]),
        '</entry>',
    ])

def _deploy_feed(state):
    site_root = _canonical_abs("/", site=True)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    recent = sorted(
        state.article_ids(), key=lambda x: state.article_info(x)['date'], reverse=True
    )[:25]
    header = "\n".join([
        '<?xml version="1.0" encoding="utf-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>/bin/hbar</title>'
        '<subtitle>Blog of Jake Lishman</subtitle>'
        f'<link href="{site_root}"/>'
        f'<link rel="self" href="{SITE}/{FEED_LOCATION}"/>'
        f'<id>{site_root}</id>'
        f'<updated>{now.isoformat()}</updated>'
        f'<author><name>Jake Lishman</name><uri>{site_root}</uri></author>'
        '<category term="programming"/>'
        '<category term="quantum computing"/>'
        f'<icon>{_canonical_abs("images/favicon-128.png", file=True)}</icon>'
    ])
    with open(DEPLOY_DIRECTORY / FEED_LOCATION, "w") as file:
        file.write(header)
        for article_id in recent:
            file.write(_make_feed_entry(state, article_id))
        file.write("</feed>\n")

def deploy_site(*, vars):
    state = SiteState(STORE_FILE, TEMPLATE_DIRECTORY / TEMPLATE_HTML)

    try:
        shutil.rmtree(DEPLOY_DIRECTORY)
    except FileNotFoundError:
        pass
    shutil.copytree(TEMPLATE_DIRECTORY, DEPLOY_DIRECTORY,
                    ignore=lambda *_: IGNORED_TEMPLATE_FILES,
                    copy_function=_copy_with_filter)
    _deploy_main_page(state)
    _deploy_articles(state)
    _deploy_tags(state)
    _deploy_about(state)
    _deploy_feed(state)
    return 0
