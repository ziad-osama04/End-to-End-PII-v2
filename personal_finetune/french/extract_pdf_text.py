"""Extract text from any PDF in correct human reading order.

The naive approach -- collect every line and sort by (y, x) -- breaks as soon as
a page places content side by side: a three-column key/value header, a two-column
article, a footer with several address blocks.  Sorting purely by y interleaves
the columns, so labels end up detached from their values.

This module instead segments each page with a recursive XY-cut: repeatedly slice
the page along whichever axis shows the most significant band of whitespace,
alternating as needed, until every region is a single coherent chunk.  Regions
are emitted top-to-bottom / left-to-right, which reproduces reading order for
single-column, multi-column and grid layouts without knowing anything about the
document's format.  All thresholds are derived from the page's own font metrics,
so the same code handles 8pt and 22pt documents.
"""

from __future__ import annotations

import argparse
import bisect
import math
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence, cast

import pymupdf


DEFAULT_INPUT = Path(__file__).with_name("test_brief_01_urologie.pdf")

# Whitespace bands narrower than these fractions are never treated as a cut.
# Both are multiplied by page-local font metrics before use.
X_GAP_IN_CHARS = 2.5  # a column gutter is at least this many characters wide
Y_GAP_IN_LINES = 0.55  # a paragraph/section break relative to line height

# Fragments overlapping vertically by at least this fraction of the shorter
# fragment belong to the same visual row (tolerates baseline/size differences).
ROW_OVERLAP_RATIO = 0.4

# A whitespace-aligned grid is only read as a table if its cells hold values
# rather than prose.  Median words per cell; analyte names, numbers, units and
# reference ranges sit at 1-2, whereas body text runs well above.
MAX_CELL_WORDS = 3
MIN_TABLE_ROWS = 3

MAX_CUT_DEPTH = 40

WHITESPACE = re.compile(r"\s")

# Redaction placeholders such as [ADRES], dropped as noise.
DECORATION_PATTERNS = (re.compile(r"^\[[^\]]*\]$"),)

# Horizontal rules under section headings. These look like pure decoration, but
# NER models trained on this letter format use them as section delimiters:
# stripping them from the ten AZORG letters halved TELEFOON recall (30 -> 15)
# and cost 3 of 10 Hospital_Name detections with the best_cc checkpoint. They
# are therefore kept unless --strip-rules is passed.
RULE_PATTERN = re.compile(r"^[\-=_~*.•·–—\s]{3,}$")

# Used to recognise the same running header/footer across pages: "Page 3 of 12"
# and "Page 4 of 12" collapse to the same shape.
DIGITS = re.compile(r"\d+")


@dataclass
class Fragment:
    """A positioned piece of text: one PDF line, or one whole detected table."""

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    atomic: bool = False  # True for tables: never split, never row-merged
    # Whether the original text carried padding on either side.  Redacted or
    # form-filled PDFs butt boxes together, so the coordinates alone cannot say
    # whether two fragments need a separating space.
    pad_left: bool = False
    pad_right: bool = False
    # Quarter turns of the text baseline. Coordinates above are already in this
    # orientation's reading frame, so x always runs along the text.
    turns: int = 0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass
class PageMetrics:
    line_height: float
    char_width: float
    x_gap: float
    y_gap: float


# --------------------------------------------------------------------------- #
# Fragment collection
# --------------------------------------------------------------------------- #


def _table_fragments(page: pymupdf.Page) -> list[Fragment]:
    """Render ruled tables to markdown so rows survive the column cuts."""
    try:
        finder = page.find_tables()
    except Exception:  # pragma: no cover - defensive: table finder is heuristic
        return []

    fragments: list[Fragment] = []
    for table in finder.tables:
        if table.row_count < 2 or table.col_count < 2:
            continue
        try:
            markdown = table.to_markdown().strip()
        except Exception:  # pragma: no cover
            continue
        if not markdown:
            continue
        x0, y0, x1, y1 = table.bbox
        fragments.append(Fragment(x0, y0, x1, y1, markdown, atomic=True))
    return fragments


def _line_fragments(page: pymupdf.Page, skip: Sequence[Fragment]) -> list[Fragment]:
    data = cast(dict, page.get_text("dict"))
    fragments: list[Fragment] = []
    seen: set[tuple[int, int, str]] = set()

    for block in data.get("blocks", []):
        if block.get("type") != 0:  # images and other non-text blocks
            continue

        for line in block.get("lines", []):
            turns = _quarter_turns(line.get("dir", (1.0, 0.0)))

            # Order spans along the baseline, whichever way the baseline points.
            spans = sorted(
                line.get("spans", []),
                key=lambda span: _reading_frame(tuple(span["bbox"]), turns)[0],
            )
            # Normalise every flavour of Unicode space (nbsp, thin space, ...)
            # so later comparisons and padding checks behave predictably.
            joined = "".join(cast(str, span.get("text", "")) for span in spans)
            raw = WHITESPACE.sub(" ", joined)
            text = raw.strip()
            if not text:
                continue

            bbox = cast(tuple[float, float, float, float], tuple(line.get("bbox", (0, 0, 0, 0))))
            if any(_contains(region, *bbox) for region in skip):
                continue

            # Some generators paint the same run twice to fake bold.
            key = (round(bbox[0]), round(bbox[1]), text)
            if key in seen:
                continue
            seen.add(key)

            x0, y0, x1, y1 = _reading_frame(bbox, turns)
            fragments.append(
                Fragment(
                    x0,
                    y0,
                    x1,
                    y1,
                    text,
                    pad_left=raw[:1].isspace(),
                    pad_right=raw[-1:].isspace(),
                    turns=turns,
                )
            )

    return fragments


def _quarter_turns(direction: Sequence[float]) -> int:
    """Baseline direction of a line, rounded to a multiple of 90 degrees."""
    dx, dy = float(direction[0]), float(direction[1])
    if dx == 0.0 and dy == 0.0:
        return 0
    return round(math.atan2(dy, dx) / (math.pi / 2)) % 4


def _reading_frame(bbox: tuple[float, float, float, float], turns: int) -> tuple[float, float, float, float]:
    """Rotate a bbox so that its text runs left to right along +x.

    This absorbs both page-level /Rotate (a faxed or scanned landscape page) and
    individual rotated runs such as a sideways table header, letting one
    orientation-agnostic segmentation pass handle all of them.
    """
    if turns == 0:
        return bbox

    angle = -turns * math.pi / 2
    cos_a, sin_a = round(math.cos(angle)), round(math.sin(angle))
    x0, y0, x1, y1 = bbox
    corners = [
        (x * cos_a - y * sin_a, x * sin_a + y * cos_a)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    ]
    xs = [point[0] for point in corners]
    ys = [point[1] for point in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _contains(region: Fragment, x0: float, y0: float, x1: float, y1: float) -> bool:
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return region.x0 <= cx <= region.x1 and region.y0 <= cy <= region.y1


def collect_fragments(page: pymupdf.Page, detect_tables: bool = True) -> list[Fragment]:
    tables = _table_fragments(page) if detect_tables else []
    return tables + _line_fragments(page, tables)


def page_metrics(fragments: Sequence[Fragment], page_width: float) -> PageMetrics:
    """Derive cut thresholds from the page's own typography."""
    lines = [f for f in fragments if not f.atomic]

    heights = [f.height for f in lines if f.height > 0]
    line_height = statistics.median(heights) if heights else 12.0

    widths = [f.width / len(f.text) for f in lines if len(f.text) >= 3 and f.width > 0]
    char_width = statistics.median(widths) if widths else line_height * 0.5

    return PageMetrics(
        line_height=line_height,
        char_width=char_width,
        x_gap=max(X_GAP_IN_CHARS * char_width, 0.015 * page_width),
        y_gap=max(Y_GAP_IN_LINES * line_height, 2.0),
    )


# --------------------------------------------------------------------------- #
# Recursive XY-cut
# --------------------------------------------------------------------------- #


def _whitespace_gaps(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    """Gaps between the merged occupied intervals of a projection profile."""
    ordered = sorted(intervals)
    if not ordered:
        return []

    gaps: list[tuple[float, float]] = []
    _, high = ordered[0]
    for low, hi in ordered[1:]:
        if low > high:
            gaps.append((high, low))
            high = hi
        else:
            high = max(high, hi)
    return gaps


def _split_at(
    fragments: Sequence[Fragment],
    cuts: Sequence[float],
    position: Callable[[Fragment], float],
) -> list[list[Fragment]]:
    buckets: list[list[Fragment]] = [[] for _ in range(len(cuts) + 1)]
    for fragment in fragments:
        buckets[bisect.bisect_right(cuts, position(fragment))].append(fragment)
    return [bucket for bucket in buckets if bucket]


def column_cuts(fragments: Sequence[Fragment], candidates: Sequence[float]) -> list[float]:
    """Keep only the vertical cuts that separate genuine columns.

    A wide blank band is ambiguous: it is either a column gutter or a hole punched
    into a single line (justified text, a form field, a redaction that replaced a
    long name with a short placeholder).  The tell is how many visual rows reach
    across it.  Parallel columns are crossed by several rows -- every row of a
    key/value header spans all of its gutters.  A hole is crossed by exactly one
    row, the line it was punched into, so cutting there would tear that line in
    half and emit its halves far apart.
    """
    rows = group_rows(fragments)
    keep: list[float] = []
    for cut in candidates:
        crossing = sum(
            1
            for row in rows
            if any(f.x1 <= cut for f in row) and any(f.x0 >= cut for f in row)
        )
        if crossing != 1:
            keep.append(cut)
    return keep


def _vertical_parts(fragments: Sequence[Fragment], metrics: PageMetrics) -> list[list[Fragment]] | None:
    """Split into side-by-side columns, read left to right."""
    gaps = _whitespace_gaps((f.x0, f.x1) for f in fragments)
    cuts = column_cuts(
        fragments,
        [(low + high) / 2 for low, high in gaps if high - low >= metrics.x_gap],
    )
    if not cuts:
        return None
    parts = _split_at(fragments, cuts, lambda f: f.x0)
    return parts if len(parts) >= 2 else None


def _horizontal_parts(fragments: Sequence[Fragment], metrics: PageMetrics) -> list[list[Fragment]] | None:
    """Split into stacked bands, read top to bottom."""
    gaps = _whitespace_gaps((f.y0, f.y1) for f in fragments)
    cuts = [(low + high) / 2 for low, high in gaps if high - low >= metrics.y_gap]
    if not cuts:
        return None
    parts = _split_at(fragments, cuts, lambda f: f.y0)
    return parts if len(parts) >= 2 else None


def _full_height_columns(
    parts: Sequence[Sequence[Fragment]],
    fragments: Sequence[Fragment],
    coverage: float = 0.8,
) -> bool:
    """True when every candidate column runs nearly the whole region height.

    Parallel columns -- a newspaper spread, a sidebar beside a main body -- start
    and finish together.  A block that only reaches partway down is instead
    something stacked above or below its neighbour, and cutting vertically there
    would pull later content up into an earlier column.
    """
    top = min(f.y0 for f in fragments)
    height = max(f.y1 for f in fragments) - top
    if height <= 0:
        return False
    return all(
        (max(f.y1 for f in part) - min(f.y0 for f in part)) >= coverage * height
        for part in parts
    )


def _aligned_table(parts: Sequence[Sequence[Fragment]], fragments: Sequence[Fragment]) -> bool:
    """True when candidate columns are really the columns of a borderless table.

    Tables ruled with vector lines are found by PyMuPDF up front, but plenty of
    documents align their columns with nothing but whitespace, and there the
    gutters are indistinguishable from those of a multi-column layout on
    geometry alone.  Reading such a region column-major would scatter each row's
    cells, so it has to be read row-major instead.

    Three signals together, all of which a genuine multi-column layout fails:

    * The columns are equally deep and their rows line up, forming a full grid.
      Stacked label/value blocks -- the multi-column letterhead -- have
      independent depths and fail this immediately.
    * There are enough rows for a grid to mean anything.
    * Cells hold short values rather than prose, which is what separates a data
      grid from side-by-side running text.  The median keeps one wordy column
      from masking three terse ones.
    """
    if len(parts) < 2:
        return False

    rows = group_rows(fragments)
    if len(rows) < MIN_TABLE_ROWS:
        return False

    depths = {len(group_rows(part)) for part in parts}
    if depths != {len(rows)}:
        return False

    words = [len(f.text.split()) for f in fragments if not f.atomic]
    return bool(words) and statistics.median(words) <= MAX_CELL_WORDS


def xy_cut(fragments: Sequence[Fragment], metrics: PageMetrics, depth: int = 0) -> list[list[Fragment]]:
    """Segment fragments into leaf regions, returned in reading order.

    Axis preference, in order:

    1. Unambiguous columns -- a gutter with parallel, full-height content on both
       sides.  Taken first so that genuine multi-column text is never sliced into
       horizontal bands, which would interleave the columns line by line.
    2. Otherwise horizontal bands, which preserve the page's top-to-bottom flow.
    3. Otherwise columns that pass the row-crossing guard but are not full
       height -- the multi-column header case, where the label/value stacks in
       each column have different depths.

    If nothing qualifies the region is a leaf, and its fragments are merged into
    visual rows instead.  Regions identified as borderless data grids skip the
    vertical options entirely so their rows survive.
    """
    if len(fragments) <= 1 or depth >= MAX_CUT_DEPTH:
        return [list(fragments)]

    columns = _vertical_parts(fragments, metrics)
    if columns is not None and _aligned_table(columns, fragments):
        # A borderless data grid: keep each row together instead of cutting it
        # into cells, so the region falls through to bands or to row merging.
        columns = None

    order: Callable[[list[Fragment]], float] = lambda part: min(f.x0 for f in part)

    if columns is not None and _full_height_columns(columns, fragments):
        parts = columns
    else:
        bands = _horizontal_parts(fragments, metrics)
        if bands is not None:
            parts = bands
            order = lambda part: min(f.y0 for f in part)
        elif columns is not None:
            parts = columns
        else:
            return [list(fragments)]

    parts.sort(key=order)

    regions: list[list[Fragment]] = []
    for part in parts:
        regions.extend(xy_cut(part, metrics, depth + 1))
    return regions


# --------------------------------------------------------------------------- #
# Region -> text
# --------------------------------------------------------------------------- #


def group_rows(fragments: Sequence[Fragment]) -> list[list[Fragment]]:
    """Group fragments into visual rows, top to bottom, each sorted left to right.

    Rows are found by vertical overlap rather than by an absolute y tolerance, so
    a 12pt label and the 8pt value typeset beside it still land on one row.
    """
    rows: list[list[Fragment]] = []
    for fragment in sorted(fragments, key=lambda f: (f.y0, f.x0)):
        if rows and not fragment.atomic and not rows[-1][0].atomic:
            top = min(f.y0 for f in rows[-1])
            bottom = max(f.y1 for f in rows[-1])
            overlap = min(bottom, fragment.y1) - max(top, fragment.y0)
            shortest = min(bottom - top, fragment.height) or 1.0
            if overlap / shortest >= ROW_OVERLAP_RATIO:
                rows[-1].append(fragment)
                continue
        rows.append([fragment])

    for row in rows:
        row.sort(key=lambda f: f.x0)
    return rows


def assemble_region(fragments: Sequence[Fragment], metrics: PageMetrics) -> list[str]:
    """Render a leaf region as text, one output line per visual row."""
    out: list[str] = []
    for row in group_rows(fragments):
        if row[0].atomic:
            out.extend(row[0].text.splitlines())
            continue

        text = row[0].text
        for previous, fragment in zip(row, row[1:]):
            gap = fragment.x0 - previous.x1
            separated = gap > 0.2 * metrics.char_width or previous.pad_right or fragment.pad_left
            text += (" " if separated else "") + fragment.text
        out.append(text)

    return out


def extract_page_lines(
    page: pymupdf.Page,
    detect_tables: bool = True,
    reading_order: str = "xycut",
) -> list[str]:
    fragments = collect_fragments(page, detect_tables=detect_tables)
    if not fragments:
        return []

    page_width = page.rect.width or 595.0

    # Each text orientation is its own reading flow; upright text comes first.
    orientations: dict[int, list[Fragment]] = {}
    for fragment in fragments:
        orientations.setdefault(fragment.turns, []).append(fragment)

    lines: list[str] = []
    for turns in sorted(orientations):
        group = orientations[turns]
        metrics = page_metrics(group, page_width)

        if reading_order == "flow":  # legacy behaviour: plain top-to-bottom sort
            regions = [sorted(group, key=lambda f: (f.y0, f.x0))]
        else:
            regions = xy_cut(group, metrics)

        for region in regions:
            if lines:
                lines.append("")  # blank line marks a layout boundary
            lines.extend(assemble_region(region, metrics))
    return lines


def extract_page_text_in_visual_order(page: pymupdf.Page, **kwargs) -> str:
    """Reading-order text for a single page."""
    return "\n".join(extract_page_lines(page, **kwargs))


# --------------------------------------------------------------------------- #
# Cleaning for downstream models
# --------------------------------------------------------------------------- #


def _shape(line: str) -> str:
    return DIGITS.sub("#", line.strip().casefold())


def find_running_lines(pages: Sequence[list[str]], min_pages: int = 2) -> set[str]:
    """Header/footer text repeated across pages, matched by shape not exact text."""
    if len(pages) < min_pages:
        return set()

    counts: dict[str, int] = {}
    for lines in pages:
        candidates = [line for line in lines if line.strip()]
        margins = candidates[:3] + candidates[-3:]
        # Count each shape once per page, so a short page whose top and bottom
        # slices overlap cannot vote for its own removal twice.
        for shape in {_shape(line) for line in margins} - {""}:
            counts[shape] = counts.get(shape, 0) + 1

    threshold = max(min_pages, round(0.5 * len(pages)))
    return {shape for shape, count in counts.items() if count >= threshold}


def clean_lines(lines: Sequence[str], running: set[str], strip_rules: bool = False) -> list[str]:
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()

        if not stripped:
            if kept and kept[-1]:
                kept.append("")
            continue

        if _shape(stripped) in running:
            continue

        # A stray ":" left over from a label/value grid belongs to the label.
        # Checked before the noise filters below, which would otherwise drop it.
        if stripped in {":", "-", "|"}:
            if kept and kept[-1] and not kept[-1].endswith(stripped):
                kept[-1] = f"{kept[-1]} {stripped}"
            continue

        if RULE_PATTERN.match(stripped):
            # Kept by default: downstream NER treats these as section delimiters.
            if strip_rules:
                continue
            kept.append(stripped)
            continue

        if not any(char.isalnum() for char in stripped):
            continue
        if any(pattern.match(stripped) for pattern in DECORATION_PATTERNS):
            continue

        kept.append(stripped)

    while kept and not kept[0]:
        kept.pop(0)
    while kept and not kept[-1]:
        kept.pop()
    return kept


# --------------------------------------------------------------------------- #
# Document level
# --------------------------------------------------------------------------- #


def extract_text_from_pdf(
    pdf_path: Path,
    clean_for_model: bool = False,
    detect_tables: bool = True,
    reading_order: str = "xycut",
    strip_rules: bool = False,
) -> str:
    with pymupdf.open(pdf_path) as doc:
        pages = [
            extract_page_lines(doc[number], detect_tables=detect_tables, reading_order=reading_order)
            for number in range(doc.page_count)
        ]
        total = doc.page_count

    empty = [index + 1 for index, lines in enumerate(pages) if not lines]
    if empty:
        print(
            f"Warning: no extractable text on page(s) {', '.join(map(str, empty))} "
            "(scanned images need OCR).",
            file=sys.stderr,
        )

    if clean_for_model:
        running = find_running_lines(pages)
        body = "\n\n".join(
            "\n".join(cleaned)
            for lines in pages
            if (cleaned := clean_lines(lines, running, strip_rules=strip_rules))
        )
        return body.rstrip() + "\n"

    parts = []
    for number, lines in enumerate(pages, start=1):
        rule = "=" * 80
        text = "\n".join(lines).strip("\n")
        parts.append(f"{rule}\nPage {number} of {total}\n{rule}\n{text}\n")
    return "\n".join(parts).rstrip() + "\n"


def save_text(output_path: Path, text: str) -> None:
    output_path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF in reading order and save it as a TXT file."
    )
    parser.add_argument("pdf", nargs="?", type=Path, default=DEFAULT_INPUT, help="Input PDF path")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output TXT path. Defaults to the PDF name with a .txt extension.",
    )
    parser.add_argument(
        "--clean-for-model",
        action="store_true",
        help="Drop repeated headers/footers, placeholders and page banners. Keeps '-----' rules.",
    )
    parser.add_argument(
        "--strip-rules",
        action="store_true",
        help=(
            "Also drop '-----' underlines. Off by default: NER models trained on this "
            "letter format read them as section delimiters, and removing them halved "
            "TELEFOON recall on the AZORG letters."
        ),
    )
    parser.add_argument(
        "--reading-order",
        choices=("xycut", "flow"),
        default="xycut",
        help="xycut: layout-aware segmentation (default). flow: plain top-to-bottom sort.",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Skip ruled-table detection and treat table cells as ordinary text.",
    )
    return parser.parse_args()


def main() -> None:
    # find_tables() prints a one-off advert for the optional pymupdf_layout
    # add-on straight to stdout; keep stdout clean for piping.
    if hasattr(pymupdf, "no_recommend_layout"):
        pymupdf.no_recommend_layout()

    args = parse_args()
    pdf_path: Path = args.pdf
    output_path: Path = args.output or pdf_path.with_suffix(".txt")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    text = extract_text_from_pdf(
        pdf_path,
        clean_for_model=args.clean_for_model,
        detect_tables=not args.no_tables,
        reading_order=args.reading_order,
        strip_rules=args.strip_rules,
    )
    save_text(output_path, text)
    print(f"Saved extracted text to {output_path}")


if __name__ == "__main__":
    main()
