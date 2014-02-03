# -*- coding: utf-8 -*-
"""
Functions for dealing with markup text
"""

import re
import six
from six import moves

from w3lib.util import str_to_unicode, unicode_to_str
from w3lib.url import safe_url_string

_ent_re = re.compile(r'&(#?(x?))([^&;\s]+);')
_tag_re = re.compile(r'<[a-zA-Z\/!].*?>', re.DOTALL)
_baseurl_re = re.compile(six.u(r'<base\s+href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']'), re.I)
_meta_refresh_re = re.compile(six.u(r'<meta[^>]*http-equiv[^>]*refresh[^>]*content\s*=\s*(?P<quote>["\'])(?P<int>(\d*\.)?\d+)\s*;\s*url=(?P<url>.*?)(?P=quote)'), re.DOTALL | re.IGNORECASE)
_cdata_re = re.compile(r'((?P<cdata_s><!\[CDATA\[)(?P<cdata_d>.*?)(?P<cdata_e>\]\]>))', re.DOTALL)

def remove_entities(text, keep=(), remove_illegal=True, encoding='utf-8'):
    u"""Remove entities from the given `text` by converting them to their
    corresponding unicode character.

    `text` can be a unicode string or a byte string encoded in the given
    `encoding` (which defaults to 'utf-8').

    If `keep` is passed (with a list of entity names) those entities will
    be kept (they won't be removed).

    It supports both numeric entities (``&#nnnn;`` and ``&#hhhh;``)
    and named entities (such as ``&nbsp;`` or ``&gt;``).

    If `remove_illegal` is ``True``, entities that can't be converted are removed.
    If `remove_illegal` is ``False``, entities that can't be converted are kept "as
    is". For more information see the tests.

    Always returns a unicode string (with the entities removed).

    >>> import w3lib.html
    >>> w3lib.html.remove_entities(b'Price: &pound;100')
    u'Price: \\xa3100'
    >>> print w3lib.html.remove_entities(b'Price: &pound;100')
    Price: £100
    >>>

    """

    def convert_entity(m):
        entity_body = m.group(3)
        if m.group(1):
            try:
                if m.group(2):
                    number = int(entity_body, 16)
                else:
                    number = int(entity_body, 10)
                # Numeric character references in the 80-9F range are typically
                # interpreted by browsers as representing the characters mapped
                # to bytes 80-9F in the Windows-1252 encoding. For more info
                # see: http://en.wikipedia.org/wiki/Character_encodings_in_HTML
                if 0x80 <= number <= 0x9f:
                    return six.int2byte(number).decode('cp1252')
            except ValueError:
                number = None
        else:
            if entity_body in keep:
                return m.group(0)
            else:
                number = moves.html_entities.name2codepoint.get(entity_body)
        if number is not None:
            try:
                return six.unichr(number)
            except ValueError:
                pass

        return u'' if remove_illegal else m.group(0)

    return _ent_re.sub(convert_entity, str_to_unicode(text, encoding))

def has_entities(text, encoding=None):
    return bool(_ent_re.search(str_to_unicode(text, encoding)))

def replace_tags(text, token='', encoding=None):
    """Replace all markup tags found in the given `text` by the given token.
    By default `token` is an empty string so it just removes all tags.

    `text` can be a unicode string or a regular string encoded as `encoding`
    (or ``'utf-8'`` if `encoding` is not given.)

    Always returns a unicode string.

    Examples:

    >>> import w3lib.html
    >>> w3lib.html.replace_tags(u'This text contains <a>some tag</a>')
    u'This text contains some tag'
    >>> w3lib.html.replace_tags('<p>Je ne parle pas <b>fran\\xe7ais</b></p>', ' -- ', 'latin-1')
    u' -- Je ne parle pas  -- fran\\xe7ais --  -- '
    >>>

    """

    return _tag_re.sub(token, str_to_unicode(text, encoding))


_REMOVECOMMENTS_RE = re.compile(u'<!--.*?-->', re.DOTALL)
def remove_comments(text, encoding=None):
    """ Remove HTML Comments.

    >>> import w3lib.html
    >>> w3lib.html.remove_comments(b"test <!--textcoment--> whatever")
    u'test  whatever'
    >>>

    """

    text = str_to_unicode(text, encoding)
    return _REMOVECOMMENTS_RE.sub(u'', text)

def remove_tags(text, which_ones=(), keep=(), encoding=None):
    """ Remove HTML Tags only.

    `which_ones` and `keep` are both tuples, there are four cases:

    ==============  ============= ==========================================
    ``which_ones``  ``keep``      what it does
    ==============  ============= ==========================================
    **not empty**   empty         remove all tags in ``which_ones``
    empty           **not empty** remove all tags except the ones in ``keep``
    empty           empty         remove all tags
    **not empty**   **not empty** not allowed
    ==============  ============= ==========================================


    Remove all tags:

    >>> import w3lib.html
    >>> doc = '<div><p><b>This is a link:</b> <a href="http://www.example.com">example</a></p></div>'
    >>> w3lib.html.remove_tags(doc)
    u'This is a link: example'
    >>>

    Keep only some tags:

    >>> w3lib.html.remove_tags(doc, keep=('div',))
    u'<div>This is a link: example</div>'
    >>>

    Remove only specific tags:

    >>> w3lib.html.remove_tags(doc, which_ones=('a','b'))
    u'<div><p>This is a link: example</p></div>'
    >>>

    You can't remove some and keep some:

    >>> w3lib.html.remove_tags(doc, which_ones=('a',), keep=('p',))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/usr/local/lib/python2.7/dist-packages/w3lib/html.py", line 101, in remove_tags
        assert not (which_ones and keep), 'which_ones and keep can not be given at the same time'
    AssertionError: which_ones and keep can not be given at the same time
    >>>

    """

    assert not (which_ones and keep), 'which_ones and keep can not be given at the same time'

    def will_remove(tag):
        if which_ones:
            return tag in which_ones
        else:
            return tag not in keep

    def remove_tag(m):
        tag = m.group(1)
        return u'' if will_remove(tag) else m.group(0)

    regex = '</?([^ >/]+).*?>'
    retags = re.compile(regex, re.DOTALL | re.IGNORECASE)

    return retags.sub(remove_tag, str_to_unicode(text, encoding))

def remove_tags_with_content(text, which_ones=(), encoding=None):
    """Remove tags and their content.

    `which_ones` is a tuple of which tags to remove including their content.
    If is empty, returns the string unmodified.

    >>> import w3lib.html
    >>> doc = '<div><p><b>This is a link:</b> <a href="http://www.example.com">example</a></p></div>'
    >>> w3lib.html.remove_tags_with_content(doc, which_ones=('b',))
    u'<div><p> <a href="http://www.example.com">example</a></p></div>'
    >>>

    """

    text = str_to_unicode(text, encoding)
    if which_ones:
        tags = '|'.join([r'<%s.*?</%s>|<%s\s*/>' % (tag, tag, tag) for tag in which_ones])
        retags = re.compile(tags, re.DOTALL | re.IGNORECASE)
        text = retags.sub(u'', text)
    return text


def replace_escape_chars(text, which_ones=('\n', '\t', '\r'), replace_by=u'', \
        encoding=None):
    """Remove escape characters.

    `which_ones` is a tuple of which escape characters we want to remove.
    By default removes ``\\n``, ``\\t``, ``\\r``.

    `replace_by` is the string to replace the escape characters by.
    It defaults to ``''``, meaning the escape characters are removed.

    """

    text = str_to_unicode(text, encoding)
    for ec in which_ones:
        text = text.replace(ec, str_to_unicode(replace_by, encoding))
    return text

def unquote_markup(text, keep=(), remove_illegal=True, encoding=None):
    """
    This function receives markup as a text (always a unicode string or
    a UTF-8 encoded string) and does the following:

    1. removes entities (except the ones in `keep`) from any part of it
        that is not inside a CDATA
    2. searches for CDATAs and extracts their text (if any) without modifying it.
    3. removes the found CDATAs

    """

    def _get_fragments(txt, pattern):
        offset = 0
        for match in pattern.finditer(txt):
            match_s, match_e = match.span(1)
            yield txt[offset:match_s]
            yield match
            offset = match_e
        yield txt[offset:]

    text = str_to_unicode(text, encoding)
    ret_text = u''
    for fragment in _get_fragments(text, _cdata_re):
        if isinstance(fragment, six.string_types):
            # it's not a CDATA (so we try to remove its entities)
            ret_text += remove_entities(fragment, keep=keep, remove_illegal=remove_illegal)
        else:
            # it's a CDATA (so we just extract its content)
            ret_text += fragment.group('cdata_d')
    return ret_text

def get_base_url(text, baseurl='', encoding='utf-8'):
    """Return the base url if declared in the given HTML `text`,
    relative to the given base url.

    If no base url is found, the given `baseurl` is returned.

    """

    text = str_to_unicode(text, encoding)
    baseurl = unicode_to_str(baseurl, encoding)
    m = _baseurl_re.search(text)
    if m:
        baseurl = moves.urllib.parse.urljoin(baseurl, m.group(1).encode(encoding))
    return safe_url_string(baseurl)

def get_meta_refresh(text, baseurl='', encoding='utf-8'):
    """Return  the http-equiv parameter of the HTML meta element from the given
    HTML text and return a tuple ``(interval, url)`` where interval is an integer
    containing the delay in seconds (or zero if not present) and url is a
    string with the absolute url to redirect.

    If no meta redirect is found, ``(None, None)`` is returned.

    """

    if six.PY2:
        baseurl = unicode_to_str(baseurl, encoding)
    try:
        text = str_to_unicode(text, encoding)
    except UnicodeDecodeError:
        print(text)
        raise
    text = remove_comments(remove_entities(text))
    m = _meta_refresh_re.search(text)
    if m:
        interval = float(m.group('int'))
        url = safe_url_string(m.group('url').strip(' "\''), encoding)
        url = moves.urllib.parse.urljoin(baseurl, url)
        return interval, url
    else:
        return None, None
