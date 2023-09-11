import argparse
import contextlib
import dataclasses
import html.parser
import os
import sys
import textwrap
from typing import Any, Dict, Iterator, List, Self, Tuple

import mastodon
import requests
from urllib3.util import Url
from whoosh.fields import SchemaClass, ID, TEXT
import whoosh.index
from whoosh.index import Index
import whoosh.qparser

DISPLAY_WIDTH: int = 70


class BasicHTMLRenderer(html.parser.HTMLParser):
    _parts: List[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parts = []

    def get_output(self) -> str:
        result = ''.join(self._parts)
        self._parts = [result]
        return result

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        if tag == 'p' and self.get_output():
            self._parts.append('\n\n')

    def handle_data(self, data: str):
        self._parts.append(data)

    @classmethod
    def render(cls, src: str) -> str:
        r = cls()
        r.feed(src)
        return r.get_output()


@dataclasses.dataclass
class Status:
    id: str
    url: str
    account: str
    content: str
    spoiler_text: str


def show_status(status: Status) -> str:
    lines = [
        f'Account: {status.account}',
        f'URL: {status.url}',
    ]
    if status.spoiler_text:
        text = f'Spoiler: {BasicHTMLRenderer.render(status.spoiler_text)}'
        lines.extend(textwrap.wrap(text, width=DISPLAY_WIDTH))
    lines.append('')
    text = BasicHTMLRenderer.render(status.content)
    lines.extend(textwrap.wrap(text, width=DISPLAY_WIDTH))
    return '\n'.join(lines)


@dataclasses.dataclass
class Client:
    site: Url
    api: mastodon.Mastodon

    @classmethod
    @contextlib.contextmanager
    def open(cls, host: str, *, verify_ssl: bool = True) -> Iterator[Self]:
        site = Url(scheme='https', host=host)
        with requests.Session() as session:
            session.verify = verify_ssl
            client_id, client_secret = mastodon.Mastodon.create_app(
                client_name='toot_search',
                scopes=['read'],
                api_base_url=site.url,
                session=session)
            api = mastodon.Mastodon(
                client_id=client_id,
                client_secret=client_secret,
                api_base_url=site.url,
                session=session)
            yield cls(site, api)

    def get_statuses(self, user: str) -> Iterator[Status]:
        account = self.api.account_lookup(user)

        def chunks() -> Iterator[List[Dict[str, Any]]]:
            chunk = self.api.account_statuses(account['id'])
            yield chunk
            while p_next := getattr(chunk, '_pagination_next', None):
                chunk = self.api.account_statuses(
                    account['id'],
                    max_id=p_next['max_id'])
                yield chunk

        for chunk in chunks():
            for raw in chunk:
                yield Status(
                    id=str(raw['id']),
                    url=raw['url'],
                    account=raw['account']['acct'],
                    content=raw['content'],
                    spoiler_text=raw['spoiler_text'])


class Schema(SchemaClass):
    id = ID(unique=True, stored=True)
    url = ID(stored=True)
    account = ID(stored=True)
    content = TEXT(stored=True)
    spoiler_text = TEXT(stored=True)


@contextlib.contextmanager
def open_index(path: str) -> Iterator[Index]:
    if os.path.exists(path):
        index = whoosh.index.open_dir(path)
    else:
        os.mkdir(path)
        index = whoosh.index.create_in(path, Schema)
    try:
        yield index
    finally:
        index.close()


def cmd_index(ns: argparse.Namespace):
    """Connect to a mastodon instance and locally index toots."""
    verify_ssl: bool = ns.verify_ssl
    host: str = ns.host
    user: str = ns.user

    with contextlib.ExitStack() as stack:
        index = stack.enter_context(open_index('index'))
        writer = index.writer()
        stack.callback(writer.commit)

        client = stack.enter_context(Client.open(host, verify_ssl=verify_ssl))
        for status in client.get_statuses(user):
            writer.add_document(**dataclasses.asdict(status))


def cmd_search(ns: argparse.Namespace):
    """Search locally indexed toots."""
    query_str: str = ns.query

    with contextlib.ExitStack() as stack:
        index = stack.enter_context(open_index('index'))
        searcher = stack.enter_context(index.searcher())
        parser = whoosh.qparser.QueryParser('content', Schema())
        query = parser.parse(query_str)
        results = searcher.search(query)

        for result in results:
            status = Status(**result)
            print(DISPLAY_WIDTH * '-')
            print(show_status(status))
            print('')


def main() -> int:
    parser = argparse.ArgumentParser(prog='toot_search.py')
    parser.add_argument('--database', default='toot_search.db')
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_index = subparsers.add_parser('index', help=cmd_index.__doc__)
    p_index.set_defaults(command=cmd_index)
    p_index.add_argument(
        '--verify-ssl', action=argparse.BooleanOptionalAction, default=True)
    p_index.add_argument('host')
    p_index.add_argument('user')

    p_search = subparsers.add_parser('search', help=cmd_search.__doc__)
    p_search.set_defaults(command=cmd_search)
    p_search.add_argument('query')

    ns = parser.parse_args()
    ns.command(ns)
    return 0


if __name__ == '__main__':
    sys.exit(main())
