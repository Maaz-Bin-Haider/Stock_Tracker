"""Report registry primitives.

Every SRS §5 report is a `Report`: a declared filter set plus a `build`
function that turns parsed filters into `Section`s of plain-value rows.
The JSON endpoint, the Excel renderer, and the PDF renderer all consume the
same `ReportResult`, so an export always contains exactly the dataset the
user saw with those filters (FR-098).
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    """One report column. ``kind`` drives alignment and number/date formats
    in the UI and both export renderers: text | qty | money | percent |
    date | datetime | bool."""

    key: str
    label: str
    kind: str = "text"


@dataclass
class Section:
    """One table of a report. Single-table reports have exactly one; the
    valuation summary has several (by bucket / location / category / top)."""

    title: str
    columns: list[Column]
    rows: list[dict]


@dataclass
class ReportResult:
    sections: list[Section]
    totals: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Report:
    """``build(filters, is_admin)`` returns the full filtered dataset.
    ``admin_only`` mirrors FR-116 and is enforced server-side in the views
    and the export pipeline, never just hidden in the UI."""

    key: str
    title: str
    description: str
    filters: tuple[str, ...]
    build: Callable[[dict, bool], ReportResult]
    admin_only: bool = False
