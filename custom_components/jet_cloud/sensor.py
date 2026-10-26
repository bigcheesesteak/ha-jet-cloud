import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

@dataclass
class JetCloudSensorEntityDescription(SensorEntityDescription):
    data_key: str = ""

PV_KEY_PATTERN: re.Pattern = re.compile(r"^pv(\d+)_(power|voltage|current)$")

PV_SENSOR_KWARGS: Dict[str, Dict] = {
    "power": {
        "native_unit_of_measurement": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
    },
    "voltage": {
        "native_unit_of_measurement": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
    },
    "current": {
        "native_unit_of_measurement": UnitOfElectricCurrent.AMPERE,
        "device_class": SensorDeviceClass.CURRENT,
    },
}

SENSOR_TYPES: tuple[JetCloudSensorEntityDescription, ...] = (
    JetCloudSensorEntityDescription(
        key="power",
        name="Grid Output Power",
        data_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JetCloudSensorEntityDescription(
        key="today_energy",
        name="Energy Generated Today",
        data_key="real_time_power_generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    JetCloudSensorEntityDescription(
        key="voltage",
        name="Grid Voltage",
        data_key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JetCloudSensorEntityDescription(
        key="current",
        name="Grid Current",
        data_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JetCloudSensorEntityDescription(
        key="frequency",
        name="Grid Frequency",
        data_key="ac_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JetCloudSensorEntityDescription(
        key="temp",
        name="Inverter Temperature",
        data_key="temperature_1",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JetCloudSensorEntityDescription(
        key="total_energy",
        name="Total Energy Generated",
        data_key="total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: List[JetCloudSensor] = []

    for device_sn, device_data in coordinator.data.items():
        for description in SENSOR_TYPES:
            entities.append(JetCloudSensor(coordinator, device_sn, description))
        for description in _pv_sensor_descriptions(device_data):
            entities.append(JetCloudSensor(coordinator, device_sn, description))

    async_add_entities(entities)


def _pv_sensor_descriptions(device_data: Dict[str, float]) -> List[JetCloudSensorEntityDescription]:
    """Create PV sensors for PV1, PV2 and any further PV input the inverter reports."""
    descriptions: List[JetCloudSensorEntityDescription] = []
    always_present = {f"pv{n}_{kind}" for n in (1, 2) for kind in PV_SENSOR_KWARGS}
    for data_key in sorted(always_present | set(device_data)):
        match: Optional[re.Match] = PV_KEY_PATTERN.match(data_key)
        if not match:
            continue
        pv_number, kind = match.groups()
        descriptions.append(
            JetCloudSensorEntityDescription(
                key=data_key,
                name=f"PV{pv_number} {kind.capitalize()}",
                data_key=data_key,
                state_class=SensorStateClass.MEASUREMENT,
                **PV_SENSOR_KWARGS[kind],
            )
        )
    return descriptions


class JetCloudSensor(CoordinatorEntity, SensorEntity):
    entity_description: JetCloudSensorEntityDescription
    _attr_has_entity_name: bool = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_sn: str,
        description: JetCloudSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._device_sn: str = device_sn
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{device_sn}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_sn)},
            name=f"JET Inverter {device_sn}",
            manufacturer="JET",
            model="Microinverter",
        )

    @property
    def native_value(self) -> Optional[float]:
        device_data: Dict[str, float] = self.coordinator.data.get(self._device_sn, {})
        return device_data.get(self.entity_description.data_key)