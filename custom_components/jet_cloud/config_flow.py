from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .api import JetCloudClient, JetCloudAuthError, JetCloudApiError

DATA_SCHEMA: vol.Schema = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
})

class JetCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            session: aiohttp.ClientSession = async_get_clientsession(self.hass)
            client: JetCloudClient = JetCloudClient(user_input[CONF_EMAIL], user_input[CONF_PASSWORD], session)
            
            try:
                await client.authenticate()
                return self.async_create_entry(title=user_input[CONF_EMAIL], data=user_input)
            except JetCloudAuthError:
                errors["base"] = "invalid_auth"
            except JetCloudApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )