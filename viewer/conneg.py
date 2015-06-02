"""
Negotiator is a container of mime-type, suffix and function mappings which
selects a function by HTTP content negotiation, using the Flask (Werkzeug)
Request.accept_mimetypes utility.

Examples::

    >>> from werkzeug.test import create_environ
    >>> from werkzeug.wrappers import Request

    >>> negotiator = Negotiator()

    >>> @negotiator.add('text/html', 'html')
    ... def render_html():
    ...     pass

    >>> @negotiator.add('application/json', 'json')
    ... def render_json():
    ...     pass

    >>> def check(mime_type, suffix=None):
    ...    request = Request(create_environ('/', headers={'Accept': mime_type}))
    ...    mtype, f = negotiator.negotiate(request, suffix)
    ...    print mtype, f.__name__ if f else None

    >>> check("text/html")
    text/html render_html

    >>> check("application/json")
    application/json render_json

    >>> check("*/*")
    text/html render_html

    >>> check("application/x-octet-stream")
    None None

    >>> check("*/*", 'json')
    application/json render_json

    >>> check("application/x-octet-stream", 'html')
    text/html render_html

    >>> check("text/html;q=0.8")
    text/html render_html

    >>> check("text/html, application/json;q=0.8")
    text/html render_html

    >>> check("text/html;q=0.1, application/json;q=0.8")
    application/json render_json

    >>> check("*/*,text/html;q=0.1, application/json;q=0.8")
    text/html render_html

"""
from __future__ import unicode_literals
__metaclass__ = type


class Negotiator:

    def __init__(self):
        self.mimetype_renderer_map = {}
        self.suffix_mimetype_map = {}
        self.preferred = None
        self.default = None

    def add(self, mediatype, *suffixes):
        def decorate(f):
            self.mimetype_renderer_map[mediatype] = f
            for suffix in suffixes:
                self.suffix_mimetype_map[suffix] = mediatype
            if not self.preferred:
                self.preferred = mediatype
                self.default = f
            return f
        return decorate

    def negotiate(self, request, suffix=None):
        if suffix:
            mimetype = self.suffix_mimetype_map.get(suffix)
            return mimetype, self.mimetype_renderer_map.get(mimetype)
        else:
            accepts = request.accept_mimetypes
            mimetype = accepts.best_match(self.mimetype_renderer_map)
            pref_quality = accepts[self.preferred]
            if mimetype:
                if accepts[mimetype] > pref_quality:
                    return mimetype, self.mimetype_renderer_map.get(mimetype)
                elif pref_quality:
                    return self.preferred, self.default
        return None, None


if __name__ == '__main__':
    import doctest
    doctest.testmod()
