import argparse
import contextlib
import dataclasses
import sys
from typing import Iterator, Self

import requests
from urllib3.util import Url


@dataclasses.dataclass
class MastodonClient:
    site: Url
    _session: requests.Session

    @classmethod
    @contextlib.contextmanager
    def open(cls, host: str, *, verify_ssl: bool = True) -> Iterator[Self]:
        site = Url(scheme='https', host=host)
        with requests.Session() as session:
            session.verify = verify_ssl
            yield cls(site=site, _session=session)

    def get(self, user: str) -> requests.Response:
        url = self.site._replace(path='/api/v1/accounts/lookup')
        return self._session.get(url.url, params={'acct': user})


def cmd_index(ns: argparse.Namespace):
    """Connect to a mastodon instance and locally index toots."""
    verify_ssl: bool = ns.verify_ssl
    host: str = ns.host
    user: str = ns.user

    with MastodonClient.open(host, verify_ssl=verify_ssl) as c:
        for k, v in c.get(user).json().items():
            print(f'{k}: {v}')


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

    ns = parser.parse_args()
    ns.command(ns)
    return 0


if __name__ == '__main__':
    sys.exit(main())
