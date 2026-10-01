"""Spreadsheet-safe CSV cells (CSV / formula injection, OWASP).

A farmer can type ``=HYPERLINK(...)`` as their name; when staff open the
export in Excel or Sheets it would run as a formula. Any text cell starting
with a formula trigger is prefixed with an apostrophe so it stays plain text.
Plain numbers such as ``+919790177750`` or ``-12.5`` are left untouched.
"""
from __future__ import annotations

import re

_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
_PLAIN_NUMBER = re.compile(r"[+-]?\d[\d .]*")


def safe_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    # Google Sheets trims leading spaces before evaluating; full-width "＝"
    # is normalised to "=" by some spreadsheet imports.
    head = value.lstrip(" \u3000").replace("\uff1d", "=")
    if not head.startswith(_TRIGGERS) or _PLAIN_NUMBER.fullmatch(value):
        return value
    return "'" + value


def safe_row(values: list[object]) -> list[object]:
    return [safe_cell(v) for v in values]
