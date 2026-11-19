from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hola_hello_ciao.features.sensors.service import ensure_sensors_exist
from hola_hello_ciao.features.statistics import repository
from hola_hello_ciao.features.statistics.repository import Aggregate
from hola_hello_ciao.features.statistics.schemas import (
    DEFAULT_WINDOW,
    MetricStat,
    SensorStatistics,
    Stat,
    StatisticsQuery,
    StatisticsResponse,
    StatisticsResult,
)


def compute_statistics(session: Session, query: StatisticsQuery) -> StatisticsResponse:
    """Requested statistics per sensor over the window; NotFoundError for unknown sensor ids."""
    window_end = query.to or datetime.now(UTC)
    window_start = query.from_ or window_end - DEFAULT_WINDOW

    if query.sensor_ids is not None:
        ensure_sensors_exist(session, query.sensor_ids)

    requested_metrics = [requested.name for requested in query.metrics]
    aggregates = repository.aggregate_readings(
        session, query.sensor_ids, requested_metrics, window_start, window_end
    )
    aggregate_by_sensor_and_metric = {
        (aggregate.sensor_id, aggregate.metric): aggregate for aggregate in aggregates
    }
    # Requested sensors appear even without data; otherwise only sensors with data, by id.
    reported_sensor_ids = (
        query.sensor_ids
        if query.sensor_ids is not None
        else sorted({aggregate.sensor_id for aggregate in aggregates})
    )

    sensor_statistics = [
        SensorStatistics(
            sensor_id=sensor_id,
            results=[
                _to_statistics_result(
                    aggregate_by_sensor_and_metric.get((sensor_id, requested.name.value)),
                    requested,
                )
                for requested in query.metrics
            ],
        )
        for sensor_id in reported_sensor_ids
    ]
    return StatisticsResponse(from_=window_start, to=window_end, sensors=sensor_statistics)


def _to_statistics_result(aggregate: Aggregate | None, requested: MetricStat) -> StatisticsResult:
    """Map a repository aggregate to a result; no aggregate means no readings: null, count 0."""
    if aggregate is None:
        return StatisticsResult(metric=requested.name, stat=requested.stat, value=None, count=0)
    value_by_stat = {
        Stat.MIN: aggregate.min,
        Stat.MAX: aggregate.max,
        Stat.SUM: aggregate.sum,
        Stat.AVG: aggregate.avg,
    }
    return StatisticsResult(
        metric=requested.name,
        stat=requested.stat,
        value=value_by_stat[requested.stat],
        count=aggregate.reading_count,
    )
