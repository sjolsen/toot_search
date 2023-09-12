from collections.abc import Iterator
import dataclasses
import html.parser
import textwrap


@dataclasses.dataclass
class Line:
    _chunks: list[str] = dataclasses.field(default_factory=list)

    def append(self, chunk: str):
        self._chunks.append(chunk)

    def contents(self) -> str:
        return ''.join(self._chunks)


@dataclasses.dataclass
class Paragraph:
    _lines: list[Line] = dataclasses.field(default_factory=list)

    def _last_line(self) -> Line:
        if not self._lines:
            self._lines.append(Line())
        return self._lines[-1]

    def append(self, chunk: str):
        self._last_line().append(chunk)

    def line_break(self):
        self._lines.append(Line())

    def lines(self) -> Iterator[str]:
        for line in self._lines:
            yield line.contents()


class BasicHTML(html.parser.HTMLParser):
    _paragraphs: list[Paragraph]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paragraphs = []

    def _last_paragraph(self) -> Paragraph:
        if not self._paragraphs:
            self._paragraphs.append(Paragraph())
        return self._paragraphs[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        if tag == 'p':
            self._paragraphs.append(Paragraph())
        if tag == 'br':
            self._last_paragraph().line_break()

    def handle_data(self, data: str):
        self._last_paragraph().append(data)

    def _raw_lines(self) -> Iterator[str]:
        for paragraph in self._paragraphs:
            yield ''
            yield from paragraph.lines()

    def _compressed_lines(self) -> Iterator[str]:
        i = self._raw_lines()
        # Discard leading whitespace
        while True:
            match next(i, None):
                case None:
                    return
                case '':
                    continue
                case line:
                    yield line
                    break
        # Compress internal whitespace and discard trailing whitespace
        blank_lines = 0
        while True:
            match next(i, None):
                case None:
                    return
                case '':
                    blank_lines += 1
                case line:
                    if blank_lines > 0:
                        yield ''
                        blank_lines = 0
                    yield line

    @classmethod
    def render(cls, src: str, *, display_width: int) -> Iterator[str]:
        r = cls()
        r.feed(src)
        for line in r._compressed_lines():
            yield from textwrap.wrap(line, width=display_width) or ['']
