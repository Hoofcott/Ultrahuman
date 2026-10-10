"""Parser and sensor registry for Ultrahuman API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)


@dataclass(frozen=True)
class UltrahumanMetric:
    key: str
    name: str
    icon: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit: str | None = None


_M = SensorStateClass.MEASUREMENT
_MIN = UnitOfTime.MINUTES
_DUR = SensorDeviceClass.DURATION

# 🔑 SINGLE SOURCE OF TRUTH FOR ALL SENSORS
# Keys of the original sensors are kept unchanged so existing entities
# (unique_id = f"{entry_id}_{key}") and their history survive the update.
METRICS: tuple[UltrahumanMetric, ...] = (
    # ---- Cardio ----
    UltrahumanMetric("hr_last", "Heart Rate", "mdi:heart-pulse", None, _M, "bpm"),
    UltrahumanMetric("night_rhr", "Night Resting HR", "mdi:heart", None, _M, "bpm"),
    UltrahumanMetric("hrv_avg", "HRV", "mdi:heart-flash", None, _M, "ms"),
    UltrahumanMetric("hrv_day_avg", "HRV Day Average", "mdi:heart-flash", None, _M, "ms"),
    UltrahumanMetric("sleep_rhr", "Sleep RHR", "mdi:heart-minus", None, _M, "bpm"),
    UltrahumanMetric("spo2_avg", "SpO2", "mdi:water-percent", None, _M, PERCENTAGE),
    UltrahumanMetric("vo2_max", "VO2 Max", "mdi:lungs", None, _M, "mL/kg/min"),

    # ---- Sleep ----
    UltrahumanMetric("sleep_score", "Sleep Score", "mdi:sleep", None, _M, None),
    UltrahumanMetric("total_sleep", "Total Sleep", "mdi:bed-clock", _DUR, _M, _MIN),
    UltrahumanMetric("sleep_start", "Sleep Start", "mdi:bed", SensorDeviceClass.TIMESTAMP, None, None),
    UltrahumanMetric("sleep_end", "Sleep End", "mdi:bed-outline", SensorDeviceClass.TIMESTAMP, None, None),
    UltrahumanMetric("time_in_bed", "Time in Bed", "mdi:bed-king", _DUR, _M, _MIN),
    UltrahumanMetric("deep_sleep", "Deep Sleep", "mdi:sleep", _DUR, _M, _MIN),
    UltrahumanMetric("rem_sleep", "REM Sleep", "mdi:eye-refresh", _DUR, _M, _MIN),
    UltrahumanMetric("light_sleep", "Light Sleep", "mdi:weather-night", _DUR, _M, _MIN),
    UltrahumanMetric("awake_time", "Awake Time", "mdi:eye", _DUR, _M, _MIN),
    UltrahumanMetric("sleep_efficiency", "Sleep Efficiency", "mdi:percent", None, _M, PERCENTAGE),
    UltrahumanMetric("restorative_sleep", "Restorative Sleep", "mdi:battery-charging", None, _M, PERCENTAGE),
    UltrahumanMetric("sleep_cycles", "Full Sleep Cycles", "mdi:sync", None, _M, None),
    UltrahumanMetric("tosses_and_turns", "Tosses and Turns", "mdi:rotate-3d-variant", None, _M, None),
    UltrahumanMetric("sleep_movements", "Sleep Movements", "mdi:motion-sensor", None, _M, None),
    UltrahumanMetric("morning_alertness", "Morning Alertness", "mdi:alarm", _DUR, _M, _MIN),

    # ---- Recovery & Activity ----
    UltrahumanMetric("recovery_index", "Recovery Index", "mdi:battery-heart-variant", None, _M, None),
    UltrahumanMetric("movement_index", "Movement Index", "mdi:run", None, _M, None),
    UltrahumanMetric("active_minutes", "Active Minutes", "mdi:timer", _DUR, _M, _MIN),
    UltrahumanMetric("weekly_active_minutes", "Weekly Active Minutes", "mdi:calendar-week", _DUR, _M, _MIN),
    UltrahumanMetric("inactive_time", "Inactive Time", "mdi:seat-recline-normal", _DUR, _M, _MIN),
    UltrahumanMetric("steps", "Steps", "mdi:shoe-print", None, SensorStateClass.TOTAL_INCREASING, "steps"),

    # ---- Temperature ----
    UltrahumanMetric("temp", "Temperature", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, _M, UnitOfTemperature.CELSIUS),
    UltrahumanMetric("sleep_body_temp", "Sleep Body Temperature", "mdi:thermometer-lines", SensorDeviceClass.TEMPERATURE, _M, UnitOfTemperature.CELSIUS),
    # A deviation is a delta, not an absolute temperature: no TEMPERATURE device
    # class, otherwise HA would convert it wrongly for °F users.
    UltrahumanMetric("temp_deviation", "Temperature Deviation", "mdi:thermometer-alert", None, _M, "°C"),
)


def _num(value):
    """Return value as int when integral, else as rounded float. None stays None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else round(f, 2)


def _positive(value):
    """Treat 0 / negative as 'no measurement' (the API sends 0 when absent)."""
    v = _num(value)
    return v if v is not None and v > 0 else None


class UltrahumanDataParser:
    """Parse Ultrahuman API payload into normalized values."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw
        self._tz = raw.get("latest_time_zone")

        metrics_by_day = raw.get("metrics", {})
        self._day_key = next(iter(metrics_by_day), None)
        self._metrics = metrics_by_day.get(self._day_key, []) if self._day_key else []

    # ---------- helpers ----------

    def _get_metric(self, metric_type: str) -> dict | None:
        return next(
            (m for m in self._metrics if m.get("type") == metric_type),
            None,
        )

    def _obj(self, metric_type: str) -> dict:
        metric = self._get_metric(metric_type)
        obj = metric.get("object") if metric else None
        return obj if isinstance(obj, dict) else {}

    def _sleep(self, *path):
        """Safely walk a path inside the sleep object."""
        node = self._obj("sleep")
        for part in path:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node

    def _sleep_stage_minutes(self, stage_type: str):
        for stage in self._sleep("sleep_stages") or []:
            if stage.get("type") == stage_type and stage.get("stage_time") is not None:
                return round(stage["stage_time"] / 60)
        return None

    def _last_value(self, metric_type: str):
        values = self._obj(metric_type).get("values") or []
        for item in reversed(values):
            if item.get("value") is not None:
                return item["value"]
        return None

    def _iso(self, ts: int | None) -> str | None:
        if not ts:
            return None
        return datetime.fromtimestamp(
            ts,
            tz=ZoneInfo(self._tz) if self._tz else None,
        ).isoformat()

    # ---------- public API ----------

    def get_value(self, key: str):
        # ---- Cardio ----
        if key == "hr_last":
            return _positive(self._obj("hr").get("last_reading"))
        if key == "night_rhr":
            return _positive(self._obj("night_rhr").get("avg"))
        if key == "hrv_avg":
            return _positive(self._obj("avg_sleep_hrv").get("value"))
        if key == "hrv_day_avg":
            return _positive(self._obj("hrv").get("avg"))
        if key == "sleep_rhr":
            return _positive(self._obj("sleep_rhr").get("value"))
        if key == "spo2_avg":
            # The API reports 0 when SpO2 could not be measured.
            return _positive(self._obj("spo2").get("avg"))
        if key == "vo2_max":
            return _positive(self._obj("vo2_max").get("value"))

        # ---- Sleep ----
        if key == "sleep_score":
            return _num(self._sleep("sleep_score", "score"))
        if key == "total_sleep":
            return _num(self._sleep("total_sleep", "minutes"))
        if key == "sleep_start":
            return self._iso(self._sleep("bedtime_start"))
        if key == "sleep_end":
            return self._iso(self._sleep("bedtime_end"))
        if key == "time_in_bed":
            return _num(self._sleep("time_in_bed", "minutes"))
        # Stage durations: the dedicated objects add up exactly to total_sleep,
        # unlike sleep_stages[] which can disagree by several minutes.
        if key == "deep_sleep":
            return _num(self._sleep("deep_sleep", "minutes"))
        if key == "rem_sleep":
            return _num(self._sleep("rem_sleep", "minutes"))
        if key == "light_sleep":
            return _num(self._sleep("light_sleep", "minutes"))
        if key == "awake_time":
            return self._sleep_stage_minutes("awake")
        if key == "sleep_efficiency":
            return _num(self._sleep("sleep_efficiency", "percentage"))
        if key == "restorative_sleep":
            return _num(self._sleep("restorative_sleep", "percentage"))
        if key == "sleep_cycles":
            return _num(self._sleep("full_sleep_cycles", "cycles"))
        if key == "tosses_and_turns":
            return _num(self._sleep("tosses_and_turns", "count"))
        if key == "sleep_movements":
            return _num(self._sleep("movements", "count"))
        if key == "morning_alertness":
            return _num(self._sleep("morning_alertness", "minutes"))

        # ---- Recovery & Activity ----
        if key == "recovery_index":
            return _num(self._obj("recovery_index").get("value"))
        if key == "movement_index":
            return _num(self._obj("movement_index").get("value"))
        if key == "active_minutes":
            return _num(self._obj("active_minutes").get("value"))
        if key == "weekly_active_minutes":
            return _num(self._obj("weekly_active_minutes").get("value"))
        if key == "inactive_time":
            return _num(self._obj("inactive_time").get("value"))
        if key == "steps":
            total = _num(self._obj("steps").get("total"))
            return int(total) if total is not None else None

        # ---- Temperature ----
        if key == "temp":
            # last_reading is truncated to an integer; the last raw sample keeps decimals.
            return _positive(self._last_value("temp") or self._obj("temp").get("last_reading"))
        if key == "sleep_body_temp":
            return _positive(self._sleep("average_body_temperature", "celsius"))
        if key == "temp_deviation":
            dev = _num(self._sleep("temperature_deviation", "celsius"))
            return round(dev, 2) if dev is not None else None

        return None

    def get_attributes(self, key: str) -> dict | None:
        """Extra state attributes for a few sensors."""
        if key == "sleep_score":
            attrs = {}
            for item in self._sleep("summary") or []:
                title = item.get("title")
                if title and item.get("score") is not None:
                    attrs[title.lower().replace(" ", "_")] = _num(item["score"])
            trend = self._sleep("score_trend") or {}
            for k in ("week_avg", "month_avg", "year_avg"):
                if trend.get(k) is not None:
                    attrs[f"score_{k}"] = trend[k]
            return attrs or None
        if key == "steps":
            trend = self._obj("steps").get("trend_title")
            return {"trend_vs_average": trend} if trend is not None else None
        if key == "hrv_day_avg":
            trend = self._obj("hrv").get("trend_title")
            return {"trend_vs_average": trend} if trend is not None else None
        return None
