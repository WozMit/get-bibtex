#!/usr/bin/env python3

# MIT License

# Copyright (c) 2026 Jared León

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import gzip
import urllib
import urllib.request
import urllib.parse
import textwrap
import re
import unicodedata
import shutil
import subprocess
import json
import html
import pathlib
import difflib
import functools
import ssl

# ========================= Global variables =========================
exclude_doi = False
exclude_url = False
exclude_url_of_doi = False
exclude_journal_issue_number = False
exclude_language = False
abbreviate_first_names = False
include_url_for_arxiv = True
prefer_mathscinet_entries = True
unaltered_mathscinet_bibtex = False
avoid_mathscinet_for_arxiv = False
exclude_mathscinet_mrclass = False
exclude_mathscinet_mrnumber = False
exclude_mathscinet_mrreviewer = False
exclude_zbmath_field = False
exclude_zbl_field = False
exclude_keywords = False
custom_field_order = True
automatic_copy_to_clipboard = False
finish_execution_automatically = True
max_authors_in_citekey = 4
default_results = 7
max_results = 100
total_text_width = 105
text_threshold = 85
# ====================================================================


@functools.lru_cache(maxsize=1)
def make_ssl_context():
    context = ssl.create_default_context()

    with urllib.request.urlopen(
        "https://curl.se/ca/cacert.pem",
        context=context,
        timeout=30,
    ) as response:
        downloaded = response.read()

    certificates = re.findall(
        rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        downloaded,
        flags=re.DOTALL,
    )

    if not certificates:
        raise ValueError("The download contained no CA certificates.")

    context.load_verify_locations(
        cadata=b"\n".join(certificates).decode("ascii")
    )

    return context


def to_clipboard(text):
    """Sends 'text' to clipboard"""
    if shutil.which('xclip') is not None:
        # xclip is available in the system
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text, text=True)
        print("\nBibTeX entry copied to the clipboard")
    elif __import__("sys").platform == "win32":
        # We are living inside Windows
        import ctypes
        from ctypes import wintypes

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.CloseClipboard.restype = wintypes.BOOL

        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalFree.restype = wintypes.HGLOBAL

        data = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_mem:
            raise ctypes.WinError(ctypes.get_last_error())

        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            ctypes.memmove(ptr, data, len(data))
        finally:
            kernel32.GlobalUnlock(h_mem)

        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(h_mem)
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
                kernel32.GlobalFree(h_mem)
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            user32.CloseClipboard()
        print("\nBibTeX entry copied to the clipboard")
    else:
        print("\nCannot copy to the clipboard")


def safe_latex_accents(name: str) -> str:
    """Given a 'name' string, outputs a latex version of it"""
    accent_map: dict[str, str] = {
        # Lowercase vowels
        "á": r"\'{a}", "à": r"\`{a}", "â": r"\^{a}", "ä": r'\"{a}',
        "ã": r"\~{a}", "å": r"\r{a}", "ā": r"\={a}", "ă": r"\u{a}", "ą": r"\k{a}",
        "é": r"\'{e}", "è": r"\`{e}", "ê": r"\^{e}", "ë": r'\"{e}',
        "ē": r"\={e}", "ĕ": r"\u{e}", "ė": r"\.{e}", "ę": r"\k{e}", "ě": r"\v{e}",
        "í": r"\'{\i}", "ì": r"\`{\i}", "î": r"\^{\i}", "ï": r'\"{\i}',
        "ĩ": r"\~{\i}", "ī": r"\={\i}", "ĭ": r"\u{\i}", "į": r"\k{i}",
        "ó": r"\'{o}", "ò": r"\`{o}", "ô": r"\^{o}", "ö": r'\"{o}',
        "õ": r"\~{o}", "ō": r"\={o}", "ŏ": r"\u{o}", "ő": r"\H{o}", "ø": r"\o{}",
        "ú": r"\'{u}", "ù": r"\`{u}", "û": r"\^{u}", "ü": r'\"{u}',
        "ũ": r"\~{u}", "ū": r"\={u}", "ŭ": r"\u{u}", "ů": r"\r{u}", "ű": r"\H{u}", "ų": r"\k{u}",
        "ý": r"\'{y}", "ỳ": r"\`{y}", "ŷ": r"\^{y}", "ÿ": r'\"{y}',

        # Lowercase consonants
        "ç": r"\c{c}", "ć": r"\'{c}", "ĉ": r"\^{c}", "ċ": r"\.{c}", "č": r"\v{c}",
        "ď": r"\v{d}", "đ": r"\dj{}",
        "ğ": r"\u{g}", "ĝ": r"\^{g}", "ġ": r"\.{g}", "ģ": r"\c{g}",
        "ĥ": r"\^{h}",
        "ĵ": r"\^{\j}",
        "ķ": r"\c{k}",
        "ĺ": r"\'{l}", "ļ": r"\c{l}", "ľ": r"\v{l}", "ł": r"\l{}",
        "ň": r"\v{n}", "ń": r"\'{n}", "ņ": r"\c{n}", "ñ": r"\~{n}",
        "ŕ": r"\'{r}", "ř": r"\v{r}", "ŗ": r"\c{r}",
        "ś": r"\'{s}", "ŝ": r"\^{s}", "ş": r"\c{s}", "š": r"\v{s}",
        "ţ": r"\c{t}", "ť": r"\v{t}",
        "ŵ": r"\^{w}", "ẁ": r"\`{w}", "ẃ": r"\'{w}", "ẅ": r'\"{w}',
        "ź": r"\'{z}", "ż": r"\.{z}", "ž": r"\v{z}",

        # Uppercase vowels
        "Á": r"\'{A}", "À": r"\`{A}", "Â": r"\^{A}", "Ä": r'\"{A}',
        "Ã": r"\~{A}", "Å": r"\r{A}", "Ā": r"\={A}", "Ă": r"\u{A}", "Ą": r"\k{A}",
        "É": r"\'{E}", "È": r"\`{E}", "Ê": r"\^{E}", "Ë": r'\"{E}',
        "Ē": r"\={E}", "Ĕ": r"\u{E}", "Ė": r"\.{E}", "Ę": r"\k{E}", "Ě": r"\v{E}",
        "Í": r"\'{I}", "Ì": r"\`{I}", "Î": r"\^{I}", "Ï": r'\"{I}',
        "Ĩ": r"\~{I}", "Ī": r"\={I}", "Ĭ": r"\u{I}", "İ": r"\.{I}", "Į": r"\k{I}",
        "Ó": r"\'{O}", "Ò": r"\`{O}", "Ô": r"\^{O}", "Ö": r'\"{O}',
        "Õ": r"\~{O}", "Ō": r"\={O}", "Ŏ": r"\u{O}", "Ő": r"\H{O}", "Ø": r"\O{}",
        "Ú": r"\'{U}", "Ù": r"\`{U}", "Û": r"\^{U}", "Ü": r'\"{U}',
        "Ũ": r"\~{U}", "Ū": r"\={U}", "Ŭ": r"\u{U}", "Ů": r"\r{U}", "Ű": r"\H{U}", "Ų": r"\k{U}",
        "Ý": r"\'{Y}", "Ỳ": r"\`{Y}", "Ŷ": r"\^{Y}", "Ÿ": r'\"{Y}',

        # Uppercase consonants
        "Ç": r"\c{C}", "Ć": r"\'{C}", "Ĉ": r"\^{C}", "Ċ": r"\.{C}", "Č": r"\v{C}",
        "Ď": r"\v{D}", "Đ": r"\DJ{}",
        "Ğ": r"\u{G}", "Ĝ": r"\^{G}", "Ġ": r"\.{G}", "Ģ": r"\c{G}",
        "Ĥ": r"\^{H}",
        "Ĵ": r"\^{J}",
        "Ķ": r"\c{K}",
        "Ĺ": r"\'{L}", "Ļ": r"\c{L}", "Ľ": r"\v{L}", "Ł": r"\L{}",
        "Ň": r"\v{N}", "Ń": r"\'{N}", "Ņ": r"\c{N}", "Ñ": r"\~{N}",
        "Ŕ": r"\'{R}", "Ř": r"\v{R}", "Ŗ": r"\c{R}",
        "Ś": r"\'{S}", "Ŝ": r"\^{S}", "Ş": r"\c{S}", "Š": r"\v{S}",
        "Ţ": r"\c{T}", "Ť": r"\v{T}",
        "Ŵ": r"\^{W}", "Ẁ": r"\`{W}", "Ẃ": r"\'{W}", "Ẅ": r'\"{W}',
        "Ź": r"\'{Z}", "Ż": r"\.{Z}", "Ž": r"\v{Z}",

        # Ligatures and special letters
        "æ": r"\ae{}", "Æ": r"\AE{}",
        "œ": r"\oe{}", "Œ": r"\OE{}",
        "ß": r"\ss{}", "ẞ": r"\SS{}",
        "ð": r"\dh{}", "Ð": r"\DH{}",
        "þ": r"\th{}", "Þ": r"\TH{}",
        "ı": r"\i{}", "ȷ": r"\j{}",
    }

    translation_table = str.maketrans(
        {char: f"{{{latex}}}" for char, latex in accent_map.items()}
    )

    normalized = unicodedata.normalize("NFC", name)
    translated = normalized.translate(translation_table)
    return "".join(
        ch for ch in translated if not unicodedata.category(ch).startswith("M")
    )


def format_name_last_first(name):
    """Given 'name', outputs a pair (last name, first name)"""
    name = name.strip()
    if ',' in name:
        # Comma-separated: left = last, right = first(s)
        last_part, first_part = name.split(',', 1)
        last_name = last_part.strip()
        first_tokens = first_part.strip().split()
    else:
        # No comma: assume last word is last name, rest are first names
        tokens = name.split()
        if len(tokens) < 2:
            # Only one token – treat as last name with no first name
            return (tokens[0], "")
        last_name = tokens[-1]
        first_tokens = tokens[:-1]
    return [last_name, " ".join(first_tokens)]


def normalise_name(name):
    """Given a 'name' string, outputs an alphanumeric version of it"""
    # Decompose characters (e.g., é -> e + combining acute accent)
    nfkd = unicodedata.normalize('NFKD', name)
    # Encode to ASCII, ignoring diacritics and other non-ASCII chars
    ascii_str = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    # Remove everything except alphanumeric characters
    result = re.sub(r'[^a-zA-Z0-9]', '', ascii_str)
    return result


def gen_doc_zb_json(json_doc):
    """Given a json file by zbmath, outputs a dictionary containing
    the relevant information"""
    document = {}
    document['title'] = json_doc['title']['title']
    document['year'] = json_doc['year']
    document['author'] = [author['name'] for author in json_doc['contributors']['authors']]
    document['author'] = [format_name_last_first(a) for a in document['author']]
    document['citekey'] = ''.join([normalise_name(l) for l, f in document['author']][:max_authors_in_citekey])
    document['type'] = json_doc['database'].lower()
    document['zbmath'] = json_doc.get('id')
    document['zbl'] = json_doc.get('identifier')
    if json_doc['source'].get('pages'):
        document['pages'] = json_doc['source']['pages'].lower()
        document['pages'] = re.sub(r'^(\d+)-(\d+)$', r'\1--\2', document['pages'])
    if json_doc['language']['languages'] != []:
        document['language'] = json_doc['language']['languages'][0]
    if json_doc['links'] != [] and json_doc['links'][0]['type'] == 'doi':
        document['doi'] = json_doc['links'][0]['identifier']
    if json_doc['links'] != [] and json_doc['links'][0]['type'] != 'doi' and json_doc['links'][0]['url'] != '':
        document['url'] = json_doc['links'][0]['url']
    if json_doc['source']['series'] != []:
        document['fjournal'] = json_doc['source']['series'][0]['title']
        document['journal'] = json_doc['source']['series'][0]['short_title']
        document['number'] = json_doc['source']['series'][0]['issue']
        document['volume'] = json_doc['source']['series'][0]['volume']
        document['year'] = json_doc['source']['series'][0]['year']
        if json_doc['source']['series'][0]['issn'] != []:
            document['issn'] = json_doc['source']['series'][0]['issn'][0]['number']
    if json_doc['msc'] != []:
        document['keywords'] = ','.join([c['code'] for c in json_doc['msc']])
    if json_doc['source']['book'] != []:
        document['isbn'] = '; '.join([i['number'] for i in json_doc['source']['book'][0]['isbn']])
        document['publisher'] = json_doc['source']['book'][0]['publisher']
        document['year'] = json_doc['source']['book'][0]['year']
    if json_doc['database'] == 'arXiv' and document['type'] == 'arxiv':
        # Preprint and arxiv
        document['bib_type'] = 'misc'
        document['arxiv'] = json_doc['identifier']
        document['doi'] = "10.48550/" + json_doc['identifier'].replace(':','.')
        document['howpublished'] = re.sub(r'\s+\(\d+\)\.?$', '', json_doc['source']['source'])
    if json_doc['document_type']['code'] == 'j':
        # Journal article
        document['bib_type'] = 'article'
    if json_doc['document_type']['code'] == 'b':
        # Book
        document['bib_type'] = 'book'
        document['isbn'] = '; '.join([i['number'] for i in json_doc['source']['book'][0]['isbn']])
        document['publisher'] = json_doc['source']['book'][0]['publisher']
        document['year'] = json_doc['source']['book'][0]['year']
        if document.get('fjournal'):
            document['fseries'] = document['fjournal']
        if document.get('journal'):
            document['series'] = document['journal']
    if json_doc['document_type']['code'] == 'a':
        # Serial article
        if json_doc['source']['book'] != []:
            document['bib_type'] = 'incollection'
            document['booktitle'] = json_doc['source']['source']
        else:
            document['bib_type'] = 'misc'
            document['howpublished'] = re.sub(r'\s+\(\d+\)\.?$', '', json_doc['source']['source'])
    if not document.get('doi') and document.get('url', '').startswith('https://arxiv.org/abs/'):
        document['doi'] = "10.48550/arXiv." + document['url'][22:]
        document['citekey'] = document['citekey'] + document['year'][2:]
    return document


def gen_bib_doc(document, options=None):
    """Given the 'document' dictionary, outputs a bibtex entry with
    its information"""
    information = document.copy()
    bibtex = '@' + information['bib_type'] + '{' + information['citekey'] + ',\n'
    del information['bib_type'], information['citekey']
    if information.get('type'):
        del information['type']
    if exclude_doi and information.get('doi'):
        del information['doi']
    if exclude_url and information.get('url'):
        del information['url']
    if exclude_url_of_doi and ('doi.org' in information.get('url', '')):
        del information['url']
    if not include_url_for_arxiv and ('arxiv.org' in information.get('url', '')):
        del information['url']
    if exclude_journal_issue_number and information.get('number'):
        del information['number']
    if exclude_language and information.get('language'):
        del information['language']
    if abbreviate_first_names:
        information['author'] = [[l, f[0]+'.'] for (l, f) in information['author']]
    if exclude_mathscinet_mrclass and information.get('mrclass'):
        del information['mrclass']
    if exclude_mathscinet_mrnumber and information.get('mrnumber'):
        del information['mrnumber']
    if exclude_mathscinet_mrreviewer and information.get('mrreviewer'):
        del information['mrreviewer']
    if exclude_zbmath_field and information.get('zbmath'):
        del information['zbmath']
    if exclude_zbl_field and information.get('zbl'):
        del information['zbl']
    if exclude_keywords and information.get('keywords'):
        del information['keywords']
    information['author'] = ' and '.join([f'{l}, {f}' for (l, f) in information['author']])
    sorted_keys = information.keys()
    if custom_field_order:
        # Attempt to print the keys in the following order
        order = ['title',
                 'author',
                 'year',
                 'booktitle',
                 'chapter',
                 'series',
                 'edition',
                 'editor'
                 'journal',
                 'key',
                 'month',
                 'fjournal',
                 'volume',
                 'number',
                 'pages',
                 'publisher',
                 'school',
                 'isbn',
                 'issn',
                 'doi',
                 'howpublished',
                 'note',
                 'institution',
                 'address',
                 'organization',
                 'url',
                 'arxiv',
                 'language',
                 'keywords',
                 'type',
                 'eprint',
                 'mrclass',
                 'mrnumber',
                 'mrreviewer',
                 'zbmath',
                 'zbl']
        sorted_keys = sorted(
            sorted_keys,
            key=lambda x: (
                order.index(m[0])
                if (m := difflib.get_close_matches(x, order, n=1, cutoff=0.9))
                else len(order)
            ),
        )
    for key in sorted_keys:
        if not information[key]:
            continue
        information[key] = safe_latex_accents(str(information[key]))
        bibtex += ' ' * 2 + f"{key:12} = {{{information[key]}}},\n"
    bibtex = bibtex[:-2] + '\n}'
    return bibtex


def gen_doc_bib(bibtex):
    """Given a 'bibtex' string, outputs a dictionary with its
    information"""
    document = {}
    document['bib_type'] = re.search(r"@(\w+)\s*\{", bibtex).group(1)
    for match in re.finditer(r'([a-zA-Z0-9_]+)\s*=\s*\{', bibtex):
        key = match.group(1)
        start_idx = match.end()
        depth = 1
        end_idx = start_idx
        while depth > 0 and end_idx < len(bibtex):
            if bibtex[end_idx] == '{':
                depth += 1
            elif bibtex[end_idx] == '}':
                depth -= 1
            end_idx += 1
        value = " ".join(bibtex[start_idx:end_idx-1].split())
        document[key.lower()] = value
    return document


def gen_msn_bib_bib(bibtex):
    """Given a 'bibtex' string, outputs the mathscinet query result on
    it"""
    def msnet_prepare(entry):
        """Input module: validate one BibTeX entry."""
        INPUT_RE = re.compile(r"^\s*@\S+\s*{\s*[^,\s]+\s*,", re.I)
        if not INPUT_RE.search(entry):
            raise ValueError("Expected one BibTeX entry")
        return {"entry": entry}

    def msnet_query(data):
        """Request module: ask the public MRef interface for BibTeX output."""
        MREF_URL = "https://mathscinet.ams.org/mathscinet-mref"
        url = MREF_URL + "?" + urllib.parse.urlencode({"ref": data["entry"], "dataType": "bibtex"})
        request = urllib.request.Request(url, headers={"User-Agent": "GetMRef"})
        with urllib.request.urlopen(
            request, context=make_ssl_context(), timeout=30
        ) as response:
            result = dict(data)
            result["response"] = response.read().decode("utf-8", errors="replace")
            return result

    def msnet_extract(data):
        """Output module: extract AMS BibTeX."""
        PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.I | re.S)
        OUTPUT_RE = re.compile(r"^\s*(@\S+)(?<!@preamble)\s*{\s*[^,\s]+\s*,", re.M)

        match = PRE_RE.search(data["response"])
        if not match:
            return None

        bibtex = html.unescape(match.group(1)).strip()
        if not OUTPUT_RE.search(bibtex):
            return None

        return bibtex + "\n"
    # Return mathscinet's bibtex entry for `entry`, or None if not found
    return msnet_extract(msnet_query(msnet_prepare(bibtex)))


def combine_msn_bib_zbl_doc(bibtex_msn, document_zbl):
    """Given a bibtex entry from mathscinet and a dictionary from
    zbmath, outputs a dictionary with some merged information, taking
    priority on mathscinet"""
    document = gen_doc_bib(bibtex_msn)
    document['author'] = [format_name_last_first(author) for author in document['author'].split(' and ')]
    document['citekey'] = ''.join([normalise_name(l) for l, f in document['author']][:max_authors_in_citekey]) + document['year'][2:]
    # Incorporate fields from zbmath if they are not already present
    for key in ['zbl', 'zbmath', 'doi', 'url', 'language', 'keywords']:
        if not document.get(key) and document_zbl.get(key):
            document[key] = document_zbl[key]
    return document


def get_request_url(params):
    """Given search parameters, outputs a zbmath search url with the
    parameters"""
    term = urllib.parse.quote(params['search_term'])
    url = f"https://api.zbmath.org/v1/document/_structured_search?page=0&results_per_page={max_results}&Anywhere={term}"
    if params.get('year'):
        url += f"&Year={params['year']}"
    return url


def fetch_json_from_url(url):
    """Outputs a json from a url query"""
    # Create a request object with a standard User-Agent header
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        # Pass the req object to urlopen instead of the raw url string
        context = make_ssl_context()
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            raw_data = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw_data = gzip.decompress(raw_data)
            charset = response.headers.get_content_charset()
            if charset:
                return json.loads(raw_data.decode(charset))
            return json.loads(raw_data)
    except Exception as e:
        print(f"HTTP Error: {e}")
        return {}


def get_from_zb(url):
    """Given a 'url' query to zbmath, outputs a json response"""
    data = fetch_json_from_url(url)
    return data


def show_query_results(data, params):
    """Given a list of search results, shows them to the user"""
    output_params = {'options': [{"key": "n", "label": "New search"},
                                 {"key": "y", "label": "Add/change year"}],
                     'n_available': len(data['result'])}
    INDENT = 4
    idx = 1
    print()
    for entry in data['result']:
        doc = gen_doc_zb_json(entry)
        prefix = f"({idx}) "
        indent_str = " " * INDENT
        name_prefix = doc['howpublished'][-9:] + ' ' if doc.get('arxiv') else ''
        full_title = name_prefix + doc['title']
        year = doc['year']
        title_lines = textwrap.wrap(full_title, width=text_threshold)
        if title_lines:
            first_line_text = prefix + title_lines[0]
            first_line = first_line_text.ljust(total_text_width - len(str(year))) + str(year)
            print(first_line)
            for line in title_lines[1:]:
                print((indent_str + line).ljust(total_text_width))
        authors_str = "; ".join([f'{f} {l}' for (l, f) in doc['author']])
        author_lines = textwrap.wrap(authors_str, width=text_threshold)
        for line in author_lines:
            print((indent_str + line).ljust(total_text_width))
        how_published = doc.get('journal', doc.get('howpublished', doc.get('booktitle', ''))) if not name_prefix else ''
        if how_published:
            pub_lines = textwrap.wrap(how_published, width=text_threshold)
            for line in pub_lines:
                print((indent_str + line).ljust(total_text_width))
        print(" " * total_text_width)
        if params.get('max_results_limit') and idx == params['max_results_limit']:
            output_params['options'] = [{'key': 'a', 'label': f"Show all results ({len(data['result'])})"}] + output_params['options']
            output_params['n_available'] = idx
            break
        idx += 1
        if len(str(idx)) > len(str(idx - 1)):
            INDENT += 1
    return output_params


def ask_input(params):
    """Shows the user a menu with options and outputs the selected
    choice"""
    OPTIONS = params['options']
    n_results = params['n_available']
    # Build menu
    parts = [f"Numeric (1-{n_results})"]
    parts += [f"[{opt['key']}] {opt['label']}" for opt in OPTIONS]
    menu = textwrap.fill(
        "  ".join(parts),
        width=total_text_width,
        break_long_words=False,
        break_on_hyphens=False
    )
    option_map = {opt["key"]: opt["label"] for opt in OPTIONS}
    while True:
        print(menu)
        choice = input("\nYour choice: ").strip().lower()
        if choice in option_map:
            # print(f"Option: {option_map[choice]}")
            print()
            return {'type': 'from_options', 'content': choice}
        elif choice.isnumeric():
            num = int(choice)
            if 1 <= num <= n_results:
                return {'type': 'index', 'content': num - 1}
            else:
                print(f"Number out of range (must be 1-{n_results}).")
        else:
            print(f"Invalid choice. Use a letter or a number 1-{n_results}.")
        # If we reach here, input was invalid, so loop again
        print()  # blank line for clarity


def process_choice(choice, params, data):
    """Given a user choice, makes sure to return selected entry or
    perform a new search"""
    if choice['content'] == 'n':
        # New search. Start again
        print('_'*total_text_width + '\n')
        params['search_term'] = None
        params['year'] = None
        return interactive_search_zb(params)
    elif choice['content'] == 'y':
        # Add year to the search
        params['year'] = input("Year (integer or range): ")
        print('_'*total_text_width + '\n')
        return interactive_search_zb(params)
    elif choice['content'] == 'a':
        # Show all the entries
        output_params = show_query_results(data, {'max_results_limit': None})
        choice = ask_input(output_params)
        return process_choice(choice, params, data)
    elif choice['type'] == 'index':
        # Item from the list selected
        document_data = data['result'][choice['content']]
        return document_data


def citation_matching_zb(params):
    """Given a citation string, returns the closest document to it
    inside zbmath"""
    try:
        encoded_citation = urllib.parse.urlencode({'q': params['search_term']})
        url = f"https://zbmath.org/citationmatching/match?{encoded_citation}"
        result = fetch_json_from_url(url)
        zbl_id = result['results'][0]['zbl_id']
        print(f"\nFound in zbMATH: https://zbmath.org/{zbl_id}")
        data = get_from_zb(f"https://api.zbmath.org/v1/document/_search?results_per_page=1&search_string=an:{zbl_id}")
        return data['result'][0]
    except:
        print("Error in second connection")
        raise SystemExit(0)


def interactive_search_zb(params):
    """Looks for a search term or asks for it term and outputs a
    zbmath entry"""
    if params.get('search_term') is None:
        try:
            params['search_term'] = input("Search term: ")
        except:
            print()
            raise SystemExit(0)
    if len(params['search_term']) > 100:
        return citation_matching_zb(params)
    url = get_request_url(params)
    data = get_from_zb(url)
    if data.get('result') is None:
        print("\nNo results to show\n" + '_'*total_text_width + '\n')
        params['search_term'] = None
        params['year'] = None
        return interactive_search_zb(params)
    else:
        output_params = show_query_results(data, {'max_results_limit': default_results})
        choice = ask_input(output_params)
        return process_choice(choice, params, data)


def manual_search(params = None):
    """Outputs the zbmath dictionary specified by the user"""
    json_doc = interactive_search_zb(params)
    document = gen_doc_zb_json(json_doc)
    return document


def new_query(params = None):
    """Asks for information and prints a bibtex entry"""
    document = manual_search(params)
    bibtex = gen_bib_doc(document)
    if prefer_mathscinet_entries and not (avoid_mathscinet_for_arxiv and document.get('type') == 'arxiv'):
        print("\nSearching MathSciNet...", end=" ", flush=True)
        bibtex_msn = gen_msn_bib_bib(bibtex)
        if bibtex_msn:
            document_msn = combine_msn_bib_zbl_doc(bibtex_msn, document)
            if document_msn.get('mrnumber'):
                print("https://mathscinet.ams.org/mathscinet/article?mr=" + document_msn['mrnumber'])
            bibtex = bibtex_msn if unaltered_mathscinet_bibtex else gen_bib_doc(document_msn)
        else:
            print("NOT FOUND")
    print('\n' + bibtex)
    if automatic_copy_to_clipboard:
        to_clipboard(bibtex)
    if not finish_execution_automatically:
        input("")


def parse_arguments():
    """Extracts and outputs arguments from the program call"""
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="""Search for a document in zbMATH and then MathSciNet using an open-ended query.

The script:
1. Uses zbMATH Open REST API to make a document search query and shows the candidates.
2. Allows to perform a new search, or refine the search by adding a year.
3. When a document is selected, it captures common relevant bibtex entries and generates a bibtex entry.
4. Prints this entry, or uses it to search for another one in MathScinet
5. Combines information from both entries to generate another one
6. Copies the generated bibtex entry to the clipboard""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
examples:
$ get-bibtex
  > Search term: szemeredi 1978
$ get-bibtex "1978 regular partitions"
$ get-bibtex -s "regular partitions szemeredi"
$ get-bibtex -s "E. Szemerédi, Regular partitions of graphs, Problèmes combinatoires et théorie des graphes, Colloq. Internat. CNRS, vol. 260, CNRS, Paris, 1978, pp. 399–401"
$ get-bibtex szemeredi -y 1970-1980
$ get-bibtex "regular partitions" -y 1978
    """)
    parser.add_argument("search", nargs='?', default=None, help="search term (optional)")
    parser.add_argument("bibfile", nargs='?', type=str, default=None, help='path of the .bib file (optional)')
    parser.add_argument("-s", "--search", dest="search_term", default=None, help="search term")
    parser.add_argument("-y", "--year", default=None, help="year (integer or range)")

    args = parser.parse_args()
    search_term = args.search if args.search is not None else args.search_term
    year = args.year
    bibfile = pathlib.Path(args.bibfile).resolve() if args.bibfile else None
    return {'search_term': search_term, 'year': year, 'file': bibfile}


params = parse_arguments()
if params.get('file'):
    file = params.get('file')
    # entries = read_bib(file)
    # new_text = replace_entries(entries)
    # file = file.parent / (file.stem + '-prime' + file.suffix)
    # file.write_text(new_text, encoding="utf-8")
else:
    try:
        make_ssl_context()
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"Could not download or load CA certificates: {exc}"
        )
    new_query(params)
