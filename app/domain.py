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


FEE_CALCULATION_RULES_VERSION = "1.0.0"


def round_money(value, decimals=2, mode="half_up"):
    d = Decimal(str(value))
    q = Decimal(1).scaleb(-decimals)
    if mode == "half_up":
        return d.quantize(q, rounding=ROUND_HALF_UP)
    if mode == "half_even":
        from decimal import ROUND_HALF_EVEN
        return d.quantize(q, rounding=ROUND_HALF_EVEN)
    if mode == "floor":
        from decimal import ROUND_FLOOR
        return d.quantize(q, rounding=ROUND_FLOOR)
    if mode == "ceil":
        from decimal import ROUND_CEILING
        return d.quantize(q, rounding=ROUND_CEILING)
    raise ValueError(f"unknown rounding mode {mode}")


def fx_convert(amount, from_ccy, to_ccy, rate):
    if from_ccy == to_ccy:
        return Decimal(str(amount))
    return Decimal(str(amount)) * Decimal(str(rate))


def apply_cap_floor(value, cap=None, floor=None):
    v = Decimal(str(value))
    if floor is not None:
        v = max(v, Decimal(str(floor)))
    if cap is not None:
        v = min(v, Decimal(str(cap)))
    return v


def tiered_fee(aum, tiers):
    """tiers: list of (from, to, bps). Returns fee in same minor units convention? Returns Decimal amount."""
    total = Decimal("0")
    remaining = Decimal(str(aum))
    for lo, hi, bps in tiers:
        band = min(Decimal(str(hi)) if hi is not None else remaining, remaining) - Decimal(str(lo))
        if band <= 0:
            continue
        total += band * Decimal(str(bps)) / Decimal(10000)
        remaining -= band
        if remaining <= 0:
            break
    return total


def minimum_fee(calculated, minimum):
    return max(Decimal(str(calculated)), Decimal(str(minimum)))


def performance_fee(profit, hurdle_rate_pct, high_water_mark=None, performance_fee_pct=0):
    profit = Decimal(str(profit))
    hurdle = Decimal(str(hurdle_rate_pct or 0)) / Decimal(100) * Decimal(str(profit))  # placeholder
    # simple: fee applies to profit above hurdle
    base = profit
    if high_water_mark is not None:
        base = max(base - Decimal(str(high_water_mark)), Decimal("0"))
    fee = base * Decimal(str(performance_fee_pct)) / Decimal(100)
    return fee


def calculate_fee(aum, bps, *, minimum=None, cap=None, floor=None, fx_rate=None, from_ccy="EUR", to_ccy="EUR", rounding="half_up", decimals=2):
    fee = Decimal(str(aum)) * Decimal(str(bps)) / Decimal(10000)
    if fx_rate is not None:
        fee = fx_convert(fee, from_ccy, to_ccy, fx_rate)
    if minimum is not None:
        fee = minimum_fee(fee, minimum)
    fee = apply_cap_floor(fee, cap=cap, floor=floor)
    return round_money(fee, decimals=decimals, mode=rounding)
