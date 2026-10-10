"""Sensor platform for Ultrahuman Ring."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import UltrahumanApiClient
from .parser import UltrahumanDataParser, METRICS
from .const import (
    CONF_API_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = UltrahumanApiClient(entry.data[CONF_API_TOKEN])

    async def _fetch():
        return await client.async_get_raw_metrics()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Ultrahuman Ring",
        update_method=_fetch,
        update_interval=timedelta(
            minutes=entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        UltrahumanSensor(entry.entry_id, coordinator, metric)
        for metric in METRICS
    )


class UltrahumanSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        coordinator: DataUpdateCoordinator,
        metric,
    ) -> None:
        super().__init__(coordinator)
        self._metric = metric
        self._attr_name = metric.name
        self._attr_unique_id = f"{entry_id}_{metric.key}"
        self._attr_icon = metric.icon
        self._attr_device_class = metric.device_class
        self._attr_state_class = metric.state_class
        self._attr_native_unit_of_measurement = metric.native_unit

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "ultrahuman_ring")},
            name="Ultrahuman Ring",
            manufacturer="Ultrahuman",
            model="Ring AIR",
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None

        parser = UltrahumanDataParser(self.coordinator.data)
        value = parser.get_value(self._metric.key)

        # Convert ISO strings to datetime for timestamp device class
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None

        return value

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return None
        return UltrahumanDataParser(self.coordinator.data).get_attributes(self._metric.key)
