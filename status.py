from collections.abc import Iterable
from collections import defaultdict
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

    @property
    def replies_count(self) -> int:
        return self.raw['replies_count']

    @property
    def reblogs_count(self) -> int:
        return self.raw['reblogs_count']

    @property
    def favourites_count(self) -> int:
        return self.raw['favourites_count']

    @property
    def media_attachments(self) -> list[dict[str, Any]]:
        return self.raw['media_attachments']

    def __str__(self) -> str:
        lines = [
            f'Account: {self.account}',
            f'Date: {self.created_at:%Y-%m-%d %H:%M %Z}',
            f'URL: {self.url}',
        ]
        if self.spoiler_text:
            lines.append(f'Spoiler: {self.spoiler_text}')
        if self.media_attachments:
            count = defaultdict(int)
            for item in self.media_attachments:
                count[item['type']] += 1
            text = ', '.join(f'{v} {k}' for k, v in count.items())
            lines.append(f'Attached: {text}')
        lines.append('')
        lines.extend(render.BasicHTML.render(self.content,
                                             display_width=DISPLAY_WIDTH))
        lines.append('')
        lines.append('  '.join([
            f'Replies: {self.replies_count}',
            f'Boosts: {self.reblogs_count}',
            f'Faves: {self.favourites_count}',
        ]))
        return '\n'.join(render.compress(lines))


def print_statuses(statuses: Iterable[Status]):
    for status in statuses:
        print(DISPLAY_WIDTH * '-')
        print(status)
