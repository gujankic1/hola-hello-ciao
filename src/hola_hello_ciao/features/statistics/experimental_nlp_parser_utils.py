"""Parser utilities for the experimental natural-language aggregate query (ADR-009).

`parse_statistics_query` reads an English sentence as a `StatisticsQuery` in four steps:

1. **Time window.** Each phrase in `_TIME_PHRASES` is searched in order; a match becomes a
   `(start, end)` window and is cut out of the sentence, so its numbers ("last 3 days") are not
   read as sensor IDs later. More than one time phrase is an error; none means the default
   window of `StatisticsService`.
2. **Sensor IDs.** "sensor 3", "sensor #3" and lists such as "sensors 1, 2 and 5" are collected
   and cut out. No sensor, or "all sensors", means all sensors; both together is an error.
3. **Statistics and metrics.** The remaining text is scanned left to right for the terms in
   `_STAT_BY_TERM` and `_METRIC_BY_TERM`; every other word is ignored. Statistics apply to the
   metric that follows them ("min and max temperature"); a metric without its own statistics
   reuses the previous ones ("average temperature and humidity").
4. **Validation.** The pieces are validated as a `StatisticsQuery`, so the structured query's
   rules (e.g. a 1 to 31 day window) apply unchanged.

Every failure raises `InvalidQueryError` with a message saying what is missing or wrong.
All patterns ignore case and match whole words only (`\\b`), so "temp" never matches inside
"temperature"; they are written with `re.VERBOSE`, where whitespace is ignored and `#` starts a
comment, so each part is explained next to it.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from hola_hello_ciao.core.errors import InvalidQueryError
from hola_hello_ciao.features.shared.metrics import Metric
from hola_hello_ciao.features.statistics.schemas import (
    MAX_WINDOW,
    MetricStat,
    Stat,
    StatisticsQuery,
)

TimeWindow = tuple[datetime, datetime]
MetricStatPair = tuple[Metric, Stat]

_PATTERN_FLAGS = re.IGNORECASE | re.VERBOSE

# --- Vocabulary ----------------------------------------------------------------------------

_METRIC_BY_TERM = {
    "temperature": Metric.TEMPERATURE,
    "temperatures": Metric.TEMPERATURE,
    "temp": Metric.TEMPERATURE,
    "humidity": Metric.HUMIDITY,
    "wind": Metric.WIND_SPEED,  # in "wind speed", "speed" is ignored
    "windspeed": Metric.WIND_SPEED,
    "wind_speed": Metric.WIND_SPEED,
    "pressure": Metric.PRESSURE,
    "rainfall": Metric.RAINFALL,
    "rain": Metric.RAINFALL,
    "precipitation": Metric.RAINFALL,
}
_STAT_BY_TERM = {
    "min": Stat.MIN,
    "minimum": Stat.MIN,
    "lowest": Stat.MIN,
    "max": Stat.MAX,
    "maximum": Stat.MAX,
    "highest": Stat.MAX,
    "peak": Stat.MAX,
    "sum": Stat.SUM,
    "total": Stat.SUM,
    "avg": Stat.AVG,
    "average": Stat.AVG,
    "mean": Stat.AVG,
}
# Any statistic or metric term as a whole word, e.g. "average" or "temp".
_STAT_OR_METRIC_TERM_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in {**_STAT_BY_TERM, **_METRIC_BY_TERM}) + r")\b",
    re.IGNORECASE,
)
_VOCABULARY_HINT = (
    f"Known metrics: {', '.join(Metric)}; statistics: {', '.join(Stat)}, "
    "each statistic written before its metric"
)

# --- Time phrases --------------------------------------------------------------------------

_DURATION_BY_UNIT = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": MAX_WINDOW,  # "one month" is the longest window (ADR-004)
}
_UNIT = r"(?P<unit> hour | day | week | month )"
# An ISO 8601 date, optionally with a time and a UTC offset: "2026-11-01", "2026-11-01T06:00",
# "2026-11-01 06:00:30+01:00", "2026-11-01T06:00Z". Calendar validity is checked when parsed.
_ISO_DATETIME = r"""
    \d{4}-\d{2}-\d{2}               # date
    (?: [T ] \d{2}:\d{2}            # optional time, after "T" or a space ...
        (?: :\d{2} )?               # ... with optional seconds
    )?
    (?: Z | [+-]\d{2}:\d{2} )?      # optional UTC offset
"""


def _parse_iso_datetime(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text.upper())  # "z" and "t" are accepted in upper case only
    except ValueError:
        raise InvalidQueryError(f"Invalid date: {text}") from None


def _window_between_datetimes(match: re.Match[str], _now: datetime) -> TimeWindow:
    return _parse_iso_datetime(match["start"]), _parse_iso_datetime(match["end"])


def _window_since_datetime(match: re.Match[str], now: datetime) -> TimeWindow:
    return _parse_iso_datetime(match["start"]), now


def _window_of_last_n_units(match: re.Match[str], now: datetime) -> TimeWindow:
    try:
        return now - int(match["count"]) * _DURATION_BY_UNIT[match["unit"].lower()], now
    except OverflowError:
        raise InvalidQueryError("Time range too long") from None


def _window_of_last_unit(match: re.Match[str], now: datetime) -> TimeWindow:
    return now - _DURATION_BY_UNIT[match["unit"].lower()], now


def _window_of_yesterday(_match: re.Match[str], now: datetime) -> TimeWindow:
    start_of_today = datetime.combine(now.astimezone(UTC).date(), time(), tzinfo=UTC)
    return start_of_today - timedelta(days=1), start_of_today


@dataclass(frozen=True)
class _TimePhrase:
    pattern: re.Pattern[str]
    to_time_window: Callable[[re.Match[str], datetime], TimeWindow]


# Searched in this order. "last 3 days" is tried before "last day", which cannot match it anyway.
_TIME_PHRASES = [
    _TimePhrase(  # "between 2026-11-01 and 2026-11-05", "from ... to ...", "from ... until ..."
        re.compile(
            rf"""\b (?: between | from ) \s+ (?P<start> {_ISO_DATETIME} )
                 \s+ (?: and | to | until ) \s+ (?P<end> {_ISO_DATETIME} )""",
            _PATTERN_FLAGS,
        ),
        _window_between_datetimes,
    ),
    _TimePhrase(  # "since 2026-11-10": until now
        re.compile(rf"\b since \s+ (?P<start> {_ISO_DATETIME} )", _PATTERN_FLAGS),
        _window_since_datetime,
    ),
    _TimePhrase(  # "last 3 days", "past 48 hours", "last 1 week"
        re.compile(rf"\b (?: last | past ) \s+ (?P<count> \d+ ) \s+ {_UNIT} s? \b", _PATTERN_FLAGS),
        _window_of_last_n_units,
    ),
    _TimePhrase(  # "last week", "past day", "last month" (31 days)
        re.compile(rf"\b (?: last | past ) \s+ {_UNIT} \b", _PATTERN_FLAGS),
        _window_of_last_unit,
    ),
    _TimePhrase(  # "yesterday": the previous UTC calendar day
        re.compile(r"\b yesterday \b", _PATTERN_FLAGS),
        _window_of_yesterday,
    ),
]

# --- Sensor phrases ------------------------------------------------------------------------

_SENSOR_ID = r"\#? \d+"  # "3" or "#3"; "#" is escaped because it starts a comment in VERBOSE
_SENSOR_ID_SEPARATOR = r"""
    (?: \s* , \s* (?: and \s+ )?    # ", " or ", and "
      | \s+ and \s+                 # " and "
      | \s* & \s*                   # " & "
    )
"""
# "sensor 3", "sensors 1, 2 and 5", "sensors #1 & #2"
_SENSOR_IDS_PATTERN = re.compile(
    rf"\b sensors? \s+ {_SENSOR_ID} (?: {_SENSOR_ID_SEPARATOR} {_SENSOR_ID} )*", _PATTERN_FLAGS
)
_ALL_SENSORS_PATTERN = re.compile(r"\b (?: all | every ) \s+ sensors? \b", _PATTERN_FLAGS)


# --- Parsing -------------------------------------------------------------------------------


def parse_statistics_query(sentence: str, now: datetime) -> StatisticsQuery:
    """Read `sentence` as a query (see the module docstring); relative times count back from
    `now`. InvalidQueryError if the sentence cannot be read or breaks a query rule."""
    time_window, remaining_text = _extract_time_window(sentence, now)
    sensor_ids, remaining_text = _extract_sensor_ids(remaining_text)
    metric_stat_pairs = _pair_stats_with_metrics(remaining_text)
    return _build_statistics_query(sensor_ids, metric_stat_pairs, time_window)


def _extract_time_window(text: str, now: datetime) -> tuple[TimeWindow | None, str]:
    """The window the text names, if any, and the text with the time phrase cut out."""
    time_windows: list[TimeWindow] = []
    for time_phrase in _TIME_PHRASES:
        time_windows.extend(
            time_phrase.to_time_window(match, now) for match in time_phrase.pattern.finditer(text)
        )
        text = time_phrase.pattern.sub(" ", text)
    if len(time_windows) > 1:
        raise InvalidQueryError("More than one time range given")
    return (time_windows[0] if time_windows else None), text


def _extract_sensor_ids(text: str) -> tuple[list[int] | None, str]:
    """The sensor IDs the text names (None: all sensors), and the text with them cut out."""
    sensor_ids = [
        int(sensor_id)
        for match in _SENSOR_IDS_PATTERN.finditer(text)
        for sensor_id in re.findall(r"\d+", match[0])
    ]
    remaining_text = _SENSOR_IDS_PATTERN.sub(" ", text)
    if sensor_ids and _ALL_SENSORS_PATTERN.search(remaining_text):
        raise InvalidQueryError("Both 'all sensors' and specific sensors given")
    # "sensor 1 and 1" is not worth a 422: keep each ID once, where it was first named.
    return list(dict.fromkeys(sensor_ids)) or None, remaining_text


def _pair_stats_with_metrics(text: str) -> list[MetricStatPair]:
    """Each metric with the statistics written before it; a metric without its own statistics
    reuses the previous metric's ("average temperature and humidity")."""
    stats_awaiting_metric: list[Stat] = []
    stats_of_previous_metric: list[Stat] = []
    metric_stat_pairs: list[MetricStatPair] = []
    for match in _STAT_OR_METRIC_TERM_PATTERN.finditer(text):
        term = match[0].lower()
        if term in _STAT_BY_TERM:
            stats_awaiting_metric.append(_STAT_BY_TERM[term])
            continue
        metric = _METRIC_BY_TERM[term]
        if stats_awaiting_metric:
            stats_of_previous_metric, stats_awaiting_metric = stats_awaiting_metric, []
        if not stats_of_previous_metric:
            raise InvalidQueryError(f"No statistic given for {metric}. {_VOCABULARY_HINT}")
        metric_stat_pairs.extend((metric, stat) for stat in stats_of_previous_metric)

    if stats_awaiting_metric:
        raise InvalidQueryError(
            f"Statistic {stats_awaiting_metric[-1]} is not followed by a metric. {_VOCABULARY_HINT}"
        )
    if not metric_stat_pairs:
        raise InvalidQueryError(f"No metric recognised. {_VOCABULARY_HINT}")
    # "avg temp and average temperature" names one pair twice; that is not worth a 422.
    return list(dict.fromkeys(metric_stat_pairs))


def _build_statistics_query(
    sensor_ids: list[int] | None,
    metric_stat_pairs: list[MetricStatPair],
    time_window: TimeWindow | None,
) -> StatisticsQuery:
    window_start, window_end = time_window if time_window else (None, None)
    try:
        return StatisticsQuery(
            sensor_ids=sensor_ids,
            metrics=[MetricStat(name=metric, stat=stat) for metric, stat in metric_stat_pairs],
            from_=window_start,
            to=window_end,
        )
    except ValidationError as e:
        raise InvalidQueryError("; ".join(map(_describe_validation_error, e.errors()))) from None


def _describe_validation_error(error: ErrorDetails) -> str:
    """E.g. "sensor_ids: Input should be greater than or equal to 1"; model-level rules have no
    field: "date range must be between 1 day and 31 days"."""
    message = error["msg"].removeprefix("Value error, ")
    return f"{error['loc'][0]}: {message}" if error["loc"] else message
