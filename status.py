from collections.abc import Iterable
import dataclasses
import datetime
from typing import Any

import render

DISPLAY_WIDTH: int = 70


@dataclasses.dataclass
class Status:
    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.raw['id'])

    @property
    def url(self) -> str:
        return self.raw['url']

    @property
    def created_at(self) -> datetime.datetime:
        return self.raw['created_at']

    @property
    def account(self) -> str:
        return self.raw['account']['acct']

    @property
    def content(self) -> str:
        return self.raw['content']

    @property
    def spoiler_text(self) -> str:
        return self.raw['spoiler_text']

    def __str__(self) -> str:
        lines = [
            f'Account: {self.account}',
            f'Date: {self.created_at:%Y-%m-%d %H:%M %Z}',
            f'URL: {self.url}',
        ]
        if self.spoiler_text:
            lines.append(f'Spoiler: {self.spoiler_text}')
        lines.append('')
        lines.extend(render.BasicHTML.render(self.content,
                                             display_width=DISPLAY_WIDTH))
        return '\n'.join(lines)


def print_statuses(statuses: Iterable[Status]):
    for status in statuses:
        print(DISPLAY_WIDTH * '-')
        print(status)
        print('')
