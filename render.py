from collections.abc import Iterator
import html.parser
import textwrap


class BasicHTML(html.parser.HTMLParser):
    _lines: list[list[str]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lines = []

    def _get_line(self, i: int) -> str:
        result = ''.join(self._lines[i])
        self._lines[i] = [result]
        return result

    def lines(self) -> Iterator[str]:
        for i in range(len(self._lines)):
            yield self._get_line(i)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        if tag == 'p' and self._lines:
            self._lines.append([])
            self._lines.append([])
        if tag == 'br':
            self._lines.append([])

    def handle_data(self, data: str):
        if not self._lines:
            self._lines.append([])
        self._lines[-1].append(data)

    @classmethod
    def render(cls, src: str, *, display_width: int) -> Iterator[str]:
        r = cls()
        r.feed(src)
        for raw_line in r.lines():
            output_lines = textwrap.wrap(raw_line, width=display_width)
            if not output_lines:
                yield ''
            yield from output_lines
