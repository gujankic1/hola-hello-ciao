from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hola_hello_ciao.features.sensors.service import ensure_sensors_exist
from hola_hello_ciao.features.statistics import repository
from hola_hello_ciao.features.statistics.schemas import (
    DEFAULT_RANGE,
    Stat,
    StatisticsQuery,
    StatisticsResponse,
    StatisticsResult,
)


def query(session: Session, data: StatisticsQuery) -> StatisticsResponse:
    """Per sensor and metric statistic over the window; NotFoundError for unknown sensor ids."""
    end = data.to or datetime.now(UTC)
    start = data.from_ or end - DEFAULT_RANGE

    if data.sensor_ids is not None:
        ensure_sensors_exist(session, data.sensor_ids)

    rows = repository.aggregate(
        session, data.sensor_ids, [m.name for m in data.metrics], start, end
    )
    by_key = {(r.sensor_id, r.metric): r for r in rows}
    sensor_ids = (
        data.sensor_ids if data.sensor_ids is not None else sorted({r.sensor_id for r in rows})
    )

    results = []
    for sensor_id in sensor_ids:
        for wanted in data.metrics:
            row = by_key.get((sensor_id, wanted.name.value))
            results.append(
                StatisticsResult(
                    sensor_id=sensor_id,
                    metric=wanted.name,
                    stat=wanted.stat,
                    value=None if row is None else _stat_value(row, wanted.stat),
                    count=0 if row is None else row.n,
                )
            )
    return StatisticsResponse(from_=start, to=end, results=results)


def _stat_value(row: repository.Aggregate, stat: Stat) -> float:
    return {Stat.MIN: row.min, Stat.MAX: row.max, Stat.SUM: row.sum, Stat.AVG: row.avg}[stat]
