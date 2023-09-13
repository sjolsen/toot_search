import argparse
from collections.abc import Iterator
import contextlib
import dataclasses
import os
import sys
from typing import cast, Any, Optional, Self

import mastodon
import requests
from urllib3.util import Url
from whoosh.fields import SchemaClass, ID, TEXT
import whoosh.index
from whoosh.index import Index
import whoosh.qparser

import render
from database import Database, Status

STATUS_DB = 'status.db'
INDEX_DIR = 'index'

DISPLAY_WIDTH: int = 70


def show_status(status: Status) -> str:
    lines = [
        f'Account: {status.account}',
        f'URL: {status.url}',
    ]
    if status.spoiler_text:
        lines.append(f'Spoiler: {status.spoiler_text}')
    lines.append('')
    lines.extend(render.BasicHTML.render(status.content,
                                         display_width=DISPLAY_WIDTH))
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

    def get_statuses(self, user: str,
                     *, min_id: Optional[str] = None) -> Iterator[Status]:
        account = self.api.account_lookup(user)

        def chunks() -> Iterator[list[dict[str, Any]]]:
            chunk = self.api.account_statuses(account['id'], min_id=min_id)
            yield chunk
            while p_next := getattr(chunk, '_pagination_next', None):
                chunk = self.api.account_statuses(
                    account['id'],
                    min_id=min_id,
                    max_id=p_next['max_id'])
                yield chunk

        for chunk in chunks():
            for raw in chunk:
                yield Status(raw)


class Schema(SchemaClass):
    id = ID(unique=True, stored=True)
    url = ID()
    account = ID()
    content = TEXT()
    spoiler_text = TEXT()


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
        db = Database(STATUS_DB)
        db.create()
        max_id = db.max_id()

        client = stack.enter_context(Client.open(host, verify_ssl=verify_ssl))
        for status in client.get_statuses(user, min_id=max_id):
            db.insert(status)

        index = stack.enter_context(open_index(INDEX_DIR))
        writer = index.writer()
        stack.callback(writer.commit)

        for _, status in db.items():
            fields = cast(list[str], Schema().names())
            document = {field: getattr(status, field) for field in fields}
            writer.update_document(**document)


def cmd_search(ns: argparse.Namespace):
    """Search locally indexed toots."""
    query_str: str = ns.query

    with contextlib.ExitStack() as stack:
        db = Database(STATUS_DB)
        index = stack.enter_context(open_index(INDEX_DIR))
        searcher = stack.enter_context(index.searcher())
        parser = whoosh.qparser.QueryParser('content', Schema())
        query = parser.parse(query_str)
        results = searcher.search(query)

        for result in results:
            status = db.get(result['id'])
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
