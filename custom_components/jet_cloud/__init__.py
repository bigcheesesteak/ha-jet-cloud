import logging
from typing import Dict, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, UPDATE_INTERVAL
from .api import JetCloudClient

_LOGGER: logging.Logger = logging.getLogger(__name__)
PLATFORMS: List[str] = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client: JetCloudClient = JetCloudClient(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD], session)

    async def async_update_data() -> Dict[str, Dict[str, float]]:
        try:
            device_sns: List[str] = await client.get_devices()
            telemetry_data: Dict[str, Dict[str, float]] = {}
            for sn in device_sns:
                telemetry_data[sn] = await client.get_device_telemetry(sn)
            return telemetry_data
        except Exception as err:
            raise UpdateFailed(f"Error fetching JetCloud data: {err}")

    coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok