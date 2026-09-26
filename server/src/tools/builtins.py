from __future__ import annotations

import ast
import datetime
import math
import operator
import platform
import sys
import re
from typing import Any
from zoneinfo import ZoneInfo
from dateutil import parser as date_parser

from .base import Tool

# Client context tracking for user-specific location & timezone
_client_timezone: str | None = None


def set_client_timezone(tz: str | None) -> None:
    """Stores the client browser's detected IANA timezone (e.g. 'Asia/Kolkata')."""
    global _client_timezone
    if tz and tz.strip():
        _client_timezone = tz.strip()


def get_client_timezone() -> str | None:
    return _client_timezone


# Comprehensive timezone and city/country alias dictionary
TIMEZONE_ALIASES: dict[str, str] = {
    # Japan & East Asia
    "tokyo": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "kyoto": "Asia/Tokyo",
    "osaka": "Asia/Tokyo",
    "nagoya": "Asia/Tokyo",
    "sapporo": "Asia/Tokyo",
    "fukuoka": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "korea": "Asia/Seoul",
    "south korea": "Asia/Seoul",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "guangzhou": "Asia/Shanghai",
    "shenzhen": "Asia/Shanghai",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "taiwan": "Asia/Taipei",
    "taipei": "Asia/Taipei",
    "singapore": "Asia/Singapore",
    "bangkok": "Asia/Bangkok",
    "thailand": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh",
    "hanoi": "Asia/Ho_Chi_Minh",
    "saigon": "Asia/Ho_Chi_Minh",
    "jakarta": "Asia/Jakarta",
    "indonesia": "Asia/Jakarta",
    "manila": "Asia/Manila",
    "philippines": "Asia/Manila",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "malaysia": "Asia/Kuala_Lumpur",

    # South Asia
    "india": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "bombay": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "calcutta": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "madras": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "pune": "Asia/Kolkata",
    "ahmedabad": "Asia/Kolkata",
    "jaipur": "Asia/Kolkata",
    "pakistan": "Asia/Karachi",
    "karachi": "Asia/Karachi",
    "lahore": "Asia/Karachi",
    "islamabad": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka",
    "dhaka": "Asia/Dhaka",
    "sri lanka": "Asia/Colombo",
    "colombo": "Asia/Colombo",
    "nepal": "Asia/Kathmandu",
    "kathmandu": "Asia/Kathmandu",

    # Middle East & Central Asia
    "dubai": "Asia/Dubai",
    "uae": "Asia/Dubai",
    "united arab emirates": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "doha": "Asia/Qatar",
    "qatar": "Asia/Qatar",
    "riyadh": "Asia/Riyadh",
    "saudi arabia": "Asia/Riyadh",
    "kuwait": "Asia/Kuwait",
    "bahrain": "Asia/Bahrain",
    "muscat": "Asia/Muscat",
    "oman": "Asia/Muscat",
    "tel aviv": "Asia/Jerusalem",
    "jerusalem": "Asia/Jerusalem",
    "israel": "Asia/Jerusalem",
    "beirut": "Asia/Beirut",
    "lebanon": "Asia/Beirut",
    "cairo": "Africa/Cairo",
    "egypt": "Africa/Cairo",
    "istanbul": "Europe/Istanbul",
    "turkey": "Europe/Istanbul",
    "ankara": "Europe/Istanbul",

    # Americas - United States
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "ny": "America/New_York",
    "washington": "America/New_York",
    "washington dc": "America/New_York",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "florida": "America/New_York",
    "atlanta": "America/New_York",
    "philadelphia": "America/New_York",
    "detroit": "America/Detroit",
    "chicago": "America/Chicago",
    "illinois": "America/Chicago",
    "houston": "America/Chicago",
    "dallas": "America/Chicago",
    "austin": "America/Chicago",
    "texas": "America/Chicago",
    "denver": "America/Denver",
    "colorado": "America/Denver",
    "phoenix": "America/Phoenix",
    "arizona": "America/Phoenix",
    "salt lake city": "America/Denver",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "sf": "America/Los_Angeles",
    "california": "America/Los_Angeles",
    "san diego": "America/Los_Angeles",
    "san jose": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "portland": "America/Los_Angeles",
    "las vegas": "America/Los_Angeles",
    "nevada": "America/Los_Angeles",
    "honolulu": "Pacific/Honolulu",
    "hawaii": "Pacific/Honolulu",
    "anchorage": "America/Anchorage",
    "alaska": "America/Anchorage",

    # Americas - Canada & Latin America
    "toronto": "America/Toronto",
    "ontario": "America/Toronto",
    "vancouver": "America/Vancouver",
    "british columbia": "America/Vancouver",
    "montreal": "America/Toronto",
    "quebec": "America/Toronto",
    "ottawa": "America/Toronto",
    "calgary": "America/Edmonton",
    "canada": "America/Toronto",
    "mexico city": "America/Mexico_City",
    "mexico": "America/Mexico_City",
    "guadalajara": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "brazil": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "argentina": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "chile": "America/Santiago",
    "bogota": "America/Bogota",
    "colombia": "America/Bogota",
    "lima": "America/Lima",
    "peru": "America/Lima",

    # Europe
    "london": "Europe/London",
    "uk": "Europe/London",
    "england": "Europe/London",
    "scotland": "Europe/London",
    "great britain": "Europe/London",
    "manchester": "Europe/London",
    "paris": "Europe/Paris",
    "france": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "germany": "Europe/Berlin",
    "munich": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "rome": "Europe/Rome",
    "italy": "Europe/Rome",
    "milan": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "spain": "Europe/Madrid",
    "barcelona": "Europe/Madrid",
    "amsterdam": "Europe/Amsterdam",
    "netherlands": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "belgium": "Europe/Brussels",
    "vienna": "Europe/Vienna",
    "austria": "Europe/Vienna",
    "zurich": "Europe/Zurich",
    "switzerland": "Europe/Zurich",
    "geneva": "Europe/Zurich",
    "stockholm": "Europe/Stockholm",
    "sweden": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "norway": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "denmark": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "finland": "Europe/Helsinki",
    "dublin": "Europe/Dublin",
    "ireland": "Europe/Dublin",
    "lisbon": "Europe/Lisbon",
    "portugal": "Europe/Lisbon",
    "athens": "Europe/Athens",
    "greece": "Europe/Athens",
    "warsaw": "Europe/Warsaw",
    "poland": "Europe/Warsaw",
    "prague": "Europe/Prague",
    "czech republic": "Europe/Prague",
    "budapest": "Europe/Budapest",
    "hungary": "Europe/Budapest",
    "bucharest": "Europe/Bucharest",
    "romania": "Europe/Bucharest",
    "moscow": "Europe/Moscow",
    "russia": "Europe/Moscow",
    "saint petersburg": "Europe/Moscow",

    # Oceania & Pacific
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "adelaide": "Australia/Adelaide",
    "australia": "Australia/Sydney",
    "auckland": "Pacific/Auckland",
    "wellington": "Pacific/Auckland",
    "new zealand": "Pacific/Auckland",
    "fiji": "Pacific/Fiji",

    # Standard Abbreviations & Codes
    "utc": "UTC",
    "gmt": "UTC",
    "z": "UTC",
    "jst": "Asia/Tokyo",
    "kst": "Asia/Seoul",
    "ist": "Asia/Kolkata",
    "pkt": "Asia/Karachi",
    "sgt": "Asia/Singapore",
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "akst": "America/Anchorage",
    "akdt": "America/Anchorage",
    "hst": "Pacific/Honolulu",
    "bst": "Europe/London",
    "cet": "Europe/Paris",
    "cest": "Europe/Paris",
    "eet": "Europe/Athens",
    "eest": "Europe/Athens",
    "msk": "Europe/Moscow",
    "aest": "Australia/Sydney",
    "aedt": "Australia/Sydney",
    "acst": "Australia/Adelaide",
    "acdt": "Australia/Adelaide",
    "awst": "Australia/Perth",
    "nzst": "Pacific/Auckland",
    "nzdt": "Pacific/Auckland",
}


def resolve_timezone(location_query: str | None) -> tuple[datetime.tzinfo, str, str]:
    """
    Resolves any given location, city, country, or timezone string to a valid tzinfo object.
    Returns: (tzinfo, canonical_name, display_location)
    """
    # Check for empty or user/local aliases
    LOCAL_ALIASES = {
        "", "local", "here", "my timezone", "my location", "user",
        "user timezone", "default", "me", "current", "system",
        "current time", "current location", "now"
    }

    if not location_query or location_query.strip().lower() in LOCAL_ALIASES:
        # Check if client browser provided an explicit IANA timezone
        if _client_timezone:
            try:
                # Format friendly city/region name from IANA timezone (e.g. Asia/Kolkata -> Kolkata / India)
                tz_parts = _client_timezone.split("/")
                city_name = tz_parts[-1].replace("_", " ") if len(tz_parts) > 1 else _client_timezone
                region_name = tz_parts[0].replace("_", " ") if len(tz_parts) > 1 else ""
                display_label = (
                    f"User's Local Time ({city_name}, {region_name})"
                    if region_name
                    else f"User's Local Time ({city_name})"
                )
                return (
                    ZoneInfo(_client_timezone),
                    _client_timezone,
                    display_label,
                )
            except Exception:
                pass

        now_local = datetime.datetime.now().astimezone()
        tz_name = now_local.tzname() or "Local"
        return now_local.tzinfo, tz_name, "User's Local Time"

    clean = location_query.strip().lower()

    # 1. Alias dictionary lookup
    if clean in TIMEZONE_ALIASES:
        tz_key = TIMEZONE_ALIASES[clean]
        try:
            return ZoneInfo(tz_key), tz_key, location_query.strip().title()
        except Exception:
            pass

    # 2. Direct ZoneInfo lookup (e.g. "Asia/Tokyo", "Europe/London", "America/New_York")
    try:
        return ZoneInfo(location_query.strip()), location_query.strip(), location_query.strip()
    except Exception:
        pass

    # 3. Partial substring search in aliases
    for alias, tz_key in TIMEZONE_ALIASES.items():
        if len(alias) >= 3 and (alias == clean or alias in clean or clean in alias):
            try:
                return ZoneInfo(tz_key), tz_key, alias.title()
            except Exception:
                pass

    # 4. Fallback to client/local time with descriptive note
    if _client_timezone:
        try:
            return (
                ZoneInfo(_client_timezone),
                _client_timezone,
                f"{location_query.strip()} (fallback to {_client_timezone})",
            )
        except Exception:
            pass

    now_local = datetime.datetime.now().astimezone()
    tz_name = now_local.tzname() or "Local"
    return (
        now_local.tzinfo,
        f"{tz_name} (Unrecognized '{location_query}')",
        location_query.strip(),
    )


def get_current_time(
    location: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """
    Returns current time and date for any requested city, country, or timezone worldwide.
    If no location is provided, returns current user's local time and date by default.
    """
    target = location or timezone
    tz, tz_identifier, display_name = resolve_timezone(target)
    now = datetime.datetime.now(tz)
    offset_str = now.strftime("%z")
    formatted_offset = (
        f"UTC{offset_str[:3]}:{offset_str[3:]}" if len(offset_str) >= 5 else offset_str
    )

    is_user_local = (
        not target
        or target.strip().lower() in {
            "", "local", "here", "my timezone", "my location", "user",
            "user timezone", "default", "me", "current", "system",
            "current time", "current location", "now"
        }
    )

    return {
        "status": "success",
        "location": display_name,
        "is_user_local_time": is_user_local,
        "time_12h": now.strftime("%I:%M %p").lstrip("0"),
        "time_24h": now.strftime("%H:%M:%S"),
        "date": now.strftime("%A, %B %d, %Y"),
        "timezone_name": now.strftime("%Z") or tz_identifier,
        "utc_offset": formatted_offset,
        "is_morning": 5 <= now.hour < 12,
        "is_afternoon": 12 <= now.hour < 17,
        "is_evening": 17 <= now.hour < 21,
        "is_night": now.hour >= 21 or now.hour < 5,
        "iso_timestamp": now.isoformat(),
        "instruction": (
            "This is the user's specific local time and date. Answer with this time directly."
            if is_user_local
            else f"This is the current time in {display_name}."
        ),
    }


def get_timezone_info(location: str | None = None) -> dict[str, Any]:
    """
    Provides comprehensive timezone metadata (IANA identifier, UTC offset, DST status,
    and current time) for any location or the user's current environment.
    """
    tz, tz_identifier, display_name = resolve_timezone(location)
    now = datetime.datetime.now(tz)
    offset = now.utcoffset()
    offset_seconds = int(offset.total_seconds()) if offset else 0
    offset_hours = offset_seconds / 3600.0

    sign = "+" if offset_seconds >= 0 else "-"
    abs_seconds = abs(offset_seconds)
    hours = abs_seconds // 3600
    minutes = (abs_seconds % 3600) // 60
    formatted_offset = f"UTC{sign}{hours:02d}:{minutes:02d}"

    dst_val = bool(now.dst()) if now.dst() is not None else False

    return {
        "status": "success",
        "location": display_name,
        "iana_timezone": tz_identifier,
        "abbreviation": now.strftime("%Z") or tz_identifier,
        "utc_offset": formatted_offset,
        "utc_offset_hours": offset_hours,
        "daylight_saving_active": dst_val,
        "current_time_12h": now.strftime("%I:%M %p").lstrip("0"),
        "current_time_24h": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%A, %B %d, %Y"),
    }


def get_current_date(
    location: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any]:
    """
    Returns current calendar date, day of week, month, year, and day of year for any timezone.
    If no location is provided, defaults to the user's local date.
    """
    target = location or timezone
    tz, tz_identifier, display_name = resolve_timezone(target)
    now = datetime.datetime.now(tz)

    is_user_local = (
        not target
        or target.strip().lower() in {
            "", "local", "here", "my timezone", "my location", "user",
            "user timezone", "default", "me", "current", "system",
            "current time", "current location", "now"
        }
    )

    return {
        "status": "success",
        "location": display_name,
        "is_user_local_date": is_user_local,
        "day_of_week": now.strftime("%A"),
        "formatted_date": now.strftime("%A, %B %d, %Y"),
        "month": now.strftime("%B"),
        "day": now.day,
        "year": now.year,
        "day_of_year": now.timetuple().tm_yday,
        "is_weekend": now.weekday() >= 5,
        "timezone": now.strftime("%Z") or tz_identifier,
        "iso_date": now.date().isoformat(),
        "instruction": (
            "This is the user's specific local date today. Answer with this date directly."
            if is_user_local
            else f"This is the current date in {display_name}."
        ),
    }


def time_difference(location_a: str, location_b: str) -> dict[str, Any]:
    """
    Calculates the exact current time difference and compares time between two cities/timezones.
    """
    tz_a, id_a, name_a = resolve_timezone(location_a)
    tz_b, id_b, name_b = resolve_timezone(location_b)

    now_a = datetime.datetime.now(tz_a)
    now_b = datetime.datetime.now(tz_b)

    offset_a = now_a.utcoffset().total_seconds() / 3600.0 if now_a.utcoffset() else 0.0
    offset_b = now_b.utcoffset().total_seconds() / 3600.0 if now_b.utcoffset() else 0.0
    diff_hours = offset_b - offset_a

    if diff_hours == 0:
        relationship = f"{name_b} and {name_a} are in the same time zone."
    elif diff_hours > 0:
        relationship = f"{name_b} is {diff_hours:g} hours ahead of {name_a}."
    else:
        relationship = f"{name_b} is {abs(diff_hours):g} hours behind {name_a}."

    return {
        "status": "success",
        "location_a": {
            "name": name_a,
            "current_time": now_a.strftime("%I:%M %p").lstrip("0"),
            "current_date": now_a.strftime("%A, %b %d"),
            "timezone": now_a.strftime("%Z"),
        },
        "location_b": {
            "name": name_b,
            "current_time": now_b.strftime("%I:%M %p").lstrip("0"),
            "current_date": now_b.strftime("%A, %b %d"),
            "timezone": now_b.strftime("%Z"),
        },
        "difference_hours": diff_hours,
        "summary": relationship,
    }


def convert_time(
    time_str: str,
    from_location: str,
    to_location: str,
    date_str: str | None = None,
) -> dict[str, Any]:
    """
    Converts a specific time from one timezone/city to another.
    Example: '3:00 PM' from 'New York' to 'Tokyo'.
    """
    tz_from, id_from, name_from = resolve_timezone(from_location)
    tz_to, id_to, name_to = resolve_timezone(to_location)

    now_from = datetime.datetime.now(tz_from)

    # Parse reference date
    ref_date = now_from.date()
    if date_str and date_str.strip():
        try:
            parsed_d = date_parser.parse(date_str, default=now_from)
            ref_date = parsed_d.date()
        except Exception:
            pass

    # Parse time_str
    try:
        parsed_time = date_parser.parse(time_str)
    except Exception as err:
        return {
            "status": "error",
            "error": f"Could not parse time string '{time_str}': {err}",
        }

    dt_from = datetime.datetime(
        year=ref_date.year,
        month=ref_date.month,
        day=ref_date.day,
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=parsed_time.second,
        tzinfo=tz_from,
    )

    dt_to = dt_from.astimezone(tz_to)

    day_diff = (dt_to.date() - dt_from.date()).days
    if day_diff > 0:
        day_rel = f"+{day_diff} day (following day)"
    elif day_diff < 0:
        day_rel = f"{day_diff} day (previous day)"
    else:
        day_rel = "same day"

    from_time_fmt = dt_from.strftime("%I:%M %p").lstrip("0")
    to_time_fmt = dt_to.strftime("%I:%M %p").lstrip("0")

    summary = (
        f"{from_time_fmt} in {name_from} ({dt_from.strftime('%Z')}) is "
        f"{to_time_fmt} in {name_to} ({dt_to.strftime('%Z')}) [{day_rel}]."
    )

    return {
        "status": "success",
        "from": {
            "location": name_from,
            "time": from_time_fmt,
            "date": dt_from.strftime("%A, %B %d, %Y"),
            "timezone": dt_from.strftime("%Z"),
        },
        "to": {
            "location": name_to,
            "time": to_time_fmt,
            "date": dt_to.strftime("%A, %B %d, %Y"),
            "timezone": dt_to.strftime("%Z"),
        },
        "day_relative": day_rel,
        "summary": summary,
    }


def get_day_of_week(
    date_str: str,
    location: str | None = None,
) -> dict[str, Any]:
    """
    Determines the exact day of the week, calendar details, and days relative to today
    for any past, present, or future date (e.g. 'December 25, 2026', '2026-10-31', 'tomorrow').
    """
    tz, _, loc_name = resolve_timezone(location)
    now = datetime.datetime.now(tz)

    try:
        target_dt = date_parser.parse(date_str, default=now)
    except Exception as err:
        return {
            "status": "error",
            "error": f"Could not parse date string '{date_str}': {err}",
        }

    days_diff = (target_dt.date() - now.date()).days
    if days_diff == 0:
        rel = "Today"
    elif days_diff == 1:
        rel = "Tomorrow"
    elif days_diff == -1:
        rel = "Yesterday"
    elif days_diff > 0:
        rel = f"In {days_diff} days"
    else:
        rel = f"{abs(days_diff)} days ago"

    return {
        "status": "success",
        "date_query": date_str,
        "day_of_week": target_dt.strftime("%A"),
        "formatted_date": target_dt.strftime("%A, %B %d, %Y"),
        "month": target_dt.strftime("%B"),
        "day": target_dt.day,
        "year": target_dt.year,
        "relative_to_today": rel,
        "days_difference": days_diff,
        "is_weekend": target_dt.weekday() >= 5,
    }


# ─── Safe Mathematical Expression Evaluator (No unsafe eval) ─────────────────

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    if isinstance(node, ast.Name):
        if node.id.lower() in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id.lower()]
        raise ValueError(f"Unknown variable: {node.id}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if op_type == ast.Pow and (right > 100 or left > 1000):
                raise ValueError("Exponent too large to compute safely.")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type}")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](_eval_node(node.operand))
        raise ValueError(f"Unsupported unary operator: {op_type}")

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id.lower() in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id.lower()]
            args = [_eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Function call not permitted: {ast.dump(node.func)}")

    raise ValueError(f"Unsupported expression element: {ast.dump(node)}")


def calculate(expression: str) -> dict[str, Any]:
    """
    Safely computes arithmetic expressions, percentages, powers, and math functions.
    Examples: '458 * 32', '15% of 85', 'sqrt(144)', '2 ** 10'
    """
    if not expression or not expression.strip():
        return {"status": "error", "error": "Empty expression provided."}

    raw_expr = expression.strip()

    # Pre-process percentage syntax: "X% of Y" -> "(X / 100) * Y"
    pct_match = re.match(r"^([\d.]+)\s*%\s*(?:of)?\s*([\d.]+)$", raw_expr, re.IGNORECASE)
    if pct_match:
        pct_val = float(pct_match.group(1))
        base_val = float(pct_match.group(2))
        res = (pct_val / 100.0) * base_val
        return {
            "status": "success",
            "expression": f"{pct_val}% of {base_val}",
            "result": round(res, 6) if not res.is_integer() else int(res),
        }

    # Pre-process trailing % e.g. "50%" -> "0.5"
    if raw_expr.endswith("%"):
        try:
            num = float(raw_expr[:-1].strip())
            return {"status": "success", "expression": raw_expr, "result": num / 100.0}
        except ValueError:
            pass

    try:
        parsed = ast.parse(raw_expr, mode="eval")
        result = _eval_node(parsed.body)
        formatted_result = (
            round(result, 6)
            if isinstance(result, float) and not result.is_integer()
            else (int(result) if isinstance(result, float) and result.is_integer() else result)
        )
        return {
            "status": "success",
            "expression": raw_expr,
            "result": formatted_result,
        }
    except Exception as err:
        return {
            "status": "error",
            "error": f"Could not calculate expression '{raw_expr}': {err}",
        }


def get_system_status() -> dict[str, Any]:
    """Returns application runtime metrics and system environment information."""
    from src.llm import get_provider_info

    provider_info = get_provider_info()
    return {
        "status": "online",
        "companion": "Akari Watanabe AI Assistant",
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": sys.version.split()[0],
        "active_llm_provider": provider_info.get("active_provider", "unknown"),
        "active_llm_model": provider_info.get("active_model", "unknown"),
        "tool_calling_capability": provider_info.get("active_tool_calling_supported", False),
        "client_timezone": _client_timezone or "System Default",
    }


def get_available_tools() -> dict[str, Any]:
    """
    Returns a catalog of all currently enabled and registered tools with their purposes and usage instructions.
    Invoke this whenever you need to check which tools or capabilities are available to assist {{user}}.
    """
    tools_summary = []
    for tool in BUILTIN_TOOLS:
        if tool.enabled:
            tools_summary.append({
                "name": tool.name,
                "display_name": tool.user_friendly_name,
                "description": tool.description,
            })
    return {
        "status": "success",
        "total_tools": len(tools_summary),
        "available_tools": tools_summary,
        "note": "Call any of these tools by name with the appropriate arguments to retrieve real-time data.",
    }


# ─── Registered Tool Catalog ──────────────────────────────────────────────────

BUILTIN_TOOLS: list[Tool] = [
    Tool(
        name="get_available_tools",
        user_friendly_name="Available Tools",
        description="Returns a complete list of all currently available tools, capabilities, and descriptions.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=get_available_tools,
        enabled=False,
    ),
    Tool(
        name="get_current_time",
        user_friendly_name="Current Time",
        description="Returns current time and date for any city, country, or timezone worldwide (e.g. 'Tokyo', 'London', 'New York', 'Paris', 'India', 'PST', 'UTC', 'JST', 'IST'). If no location is provided or if asked about user/local time, returns user's current local time.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City, country, or timezone name (e.g., 'Tokyo', 'New York', 'London', 'Paris', 'India', 'PST', 'UTC', 'Asia/Tokyo'). Defaults to user local time if omitted.",
                },
                "timezone": {
                    "type": "string",
                    "description": "Optional timezone identifier (e.g., 'Asia/Tokyo', 'America/New_York', 'UTC', 'IST').",
                },
            },
            "required": [],
        },
        func=get_current_time,
        enabled=True,
    ),
    Tool(
        name="get_timezone_info",
        user_friendly_name="Timezone Details",
        description="Returns detailed timezone metadata, IANA code, and UTC offset (e.g. UTC+05:30) for any location or user's local timezone.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Optional city, country, or timezone (e.g. 'Tokyo', 'London', 'India', 'PST', 'local'). Defaults to user's timezone if omitted.",
                }
            },
            "required": [],
        },
        func=get_timezone_info,
        enabled=True,
    ),
    Tool(
        name="convert_time",
        user_friendly_name="Timezone Converter",
        description="Converts a specific time between two cities, countries, or timezones (e.g. '3:00 PM' from 'New York' to 'Tokyo'). Handles day offsets and time differences.",
        parameters={
            "type": "object",
            "properties": {
                "time_str": {
                    "type": "string",
                    "description": "The time to convert (e.g. '3:00 PM', '15:30', '9 AM', 'noon').",
                },
                "from_location": {
                    "type": "string",
                    "description": "Source city, country, or timezone (e.g. 'New York', 'London', 'PST', 'local').",
                },
                "to_location": {
                    "type": "string",
                    "description": "Destination city, country, or timezone (e.g. 'Tokyo', 'Paris', 'India', 'UTC').",
                },
                "date_str": {
                    "type": "string",
                    "description": "Optional calendar date for the conversion. Defaults to today.",
                },
            },
            "required": ["time_str", "from_location", "to_location"],
        },
        func=convert_time,
        enabled=True,
    ),
    Tool(
        name="time_difference",
        user_friendly_name="Time Difference",
        description="Calculates the exact current time difference and compares time between two cities, countries, or timezones (e.g. between 'New York' and 'Tokyo').",
        parameters={
            "type": "object",
            "properties": {
                "location_a": {
                    "type": "string",
                    "description": "First city, country, or timezone (e.g. 'New York', 'London', 'PST', 'local').",
                },
                "location_b": {
                    "type": "string",
                    "description": "Second city, country, or timezone (e.g. 'Tokyo', 'Paris', 'JST', 'India').",
                },
            },
            "required": ["location_a", "location_b"],
        },
        func=time_difference,
        enabled=True,
    ),
    Tool(
        name="get_current_date",
        user_friendly_name="Current Date",
        description="Returns the current calendar date, day of the week, month, year, and day of year for any timezone or city. If no location is provided, returns current local date.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Optional city, country, or timezone name (e.g. 'Tokyo', 'London', 'New York', 'UTC', 'local'). Defaults to local date if omitted.",
                }
            },
            "required": [],
        },
        func=get_current_date,
        enabled=True,
    ),
    Tool(
        name="get_day_of_week",
        user_friendly_name="Day of Week",
        description="Calculates the day of the week, full calendar date, and days relative to today for any specific past or future date (e.g. 'December 25, 2026', '2026-10-31', 'tomorrow').",
        parameters={
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "The date to inspect (e.g. 'December 25, 2026', 'October 31', '2026-07-04').",
                },
                "location": {
                    "type": "string",
                    "description": "Optional location/timezone context.",
                },
            },
            "required": ["date_str"],
        },
        func=get_day_of_week,
        enabled=True,
    ),
    Tool(
        name="calculate",
        user_friendly_name="Calculator",
        description="Accurately evaluates mathematical expressions, arithmetic, percentages, powers, and math functions (e.g. '458 * 32', '15% of 85', 'sqrt(144)', '2 ** 10'). Always use this for math questions to guarantee precision.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '458 * 32', '15% of 85', '125 + 380'.",
                }
            },
            "required": ["expression"],
        },
        func=calculate,
        enabled=True,
    ),
    Tool(
        name="get_system_status",
        user_friendly_name="System Status",
        description="Returns application and system runtime health, host OS, Python runtime version, active AI model, and WebSocket status.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        func=get_system_status,
        enabled=True,
    ),
]
