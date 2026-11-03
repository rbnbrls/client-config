"""Pure domain logic shared by simulation and activation verification."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def annual_fee(aum: int | float | str, bps: int | float | str) -> int:
    """Return annual fee in minor currency units (cents) for AUM in euros."""
    cents = Decimal(str(aum)) * Decimal(str(bps)) / Decimal(10_000) * 100
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fee_delta(aum: int | float | str, old_bps: int | float | str, new_bps: int | float | str) -> int:
    return annual_fee(aum, new_bps) - annual_fee(aum, old_bps)


def effective_on(start: str, end: str | None, when: str) -> bool:
    return start <= when and (end is None or when < end)
