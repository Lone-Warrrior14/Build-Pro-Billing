"""
All monetary values are stored in the database as integer paise
(1 rupee = 100 paise) to avoid floating-point rounding errors
accumulating across thousands of invoices. These helpers convert
cleanly between rupee (float/Decimal, used in the UI) and paise (int,
used in the DB).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

try:
    from num2words import num2words
    _HAS_NUM2WORDS = True
except ImportError:
    _HAS_NUM2WORDS = False


def to_paise(rupees) -> int:
    """Convert a rupee amount (float, str, or Decimal) to integer paise,
    rounding half-up to the nearest paisa."""
    d = Decimal(str(rupees))
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_rupees(paise: int) -> float:
    return round(paise / 100.0, 2)


def format_inr(paise: int) -> str:
    rupees = to_rupees(paise)
    # Indian digit grouping (e.g. 1,23,456.00)
    is_negative = rupees < 0
    rupees = abs(rupees)
    whole = int(rupees)
    frac = round((rupees - whole) * 100)
    s = str(whole)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    formatted = f"Rs. {s}.{frac:02d}"
    return f"-{formatted}" if is_negative else formatted


def amount_in_words(paise: int) -> str:
    rupees = to_rupees(paise)
    whole = int(rupees)
    frac = round((rupees - whole) * 100)
    if _HAS_NUM2WORDS:
        words = num2words(whole, lang="en_IN").replace(",", "").title()
        result = f"Rupees {words} Only"
        if frac:
            paise_words = num2words(frac, lang="en_IN").title()
            result = f"Rupees {words} and {paise_words} Paise Only"
        return result
    return f"Rupees {whole} and {frac:02d}/100 Only"
