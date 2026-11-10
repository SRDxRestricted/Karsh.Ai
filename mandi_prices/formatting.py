"""
formatting.py — Display helpers shared by the mandi price UI.
"""

from __future__ import annotations


def _group_indian(digits: str) -> str:
    """Group digits the Indian way: 194994 -> 1,94,994."""
    if len(digits) <= 3:
        return digits
    last_three, rest = digits[-3:], digits[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts + [last_three])


def inr(value: float | None, decimals: int = 0, signed: bool = False) -> str:
    """Format a number as Indian rupees, e.g. 3500 -> ₹3,500."""
    if value is None:
        return "—"

    sign = ""
    if value < 0:
        sign = "−"
        value = abs(value)
    elif signed and value > 0:
        sign = "+"

    formatted = f"{value:.{decimals}f}"
    whole, _, fraction = formatted.partition(".")
    text = f"{sign}₹{_group_indian(whole)}"
    if decimals and fraction:
        text += f".{fraction}"
    return text


def pct(value: float | None, decimals: int = 1, signed: bool = True) -> str:
    if value is None:
        return "—"
    text = f"{abs(value):.{decimals}f}%"
    if value < 0:
        return f"−{text}"
    if signed and value > 0:
        return f"+{text}"
    return text
