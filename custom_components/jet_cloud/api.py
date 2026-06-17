import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

from .const import BASE_URL

class JetCloudApiError(Exception):
    pass

class JetCloudAuthError(JetCloudApiError):
    pass

class JetCloudClient:
    def __init__(self, email: str, password: str, session: aiohttp.ClientSession) -> None:
        self.email: str = email
        self.password: str = password
        self.session: aiohttp.ClientSession = session
        self.token: Optional[str] = None
        self._app_version: str = "1.260613.3"

    def _hash_password(self, clear_text: str) -> str:
        return hashlib.md5(clear_text.encode('utf-8')).hexdigest()

    def _get_base_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "InterfaceType": "2",
            "projectType": "10",
            "appVersion": self._app_version,
        }
        if self.token:
            headers["token"] = self.token
        return headers

    async def authenticate(self) -> bool:
        url: str = f"{BASE_URL}/user/login"
        headers: Dict[str, str] = self._get_base_headers()
        headers["Content-Type"] = "application/json;charset=UTF-8"
        
        payload: Dict[str, str] = {
            "email": self.email,
            "password": self._hash_password(self.password),
            "phoneOs": "1",
            "phoneModel": "ha_integration",
            "appVersion": self._app_version
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise JetCloudApiError(f"HTTP error {response.status} during authentication")
                
                data: Dict[str, Any] = await response.json()
                if data.get("result") == 0:
                    self.token = data.get("obj", {}).get("token")
                    return True
                
                self.token = None
                raise JetCloudAuthError("Invalid credentials or access denied")
        except aiohttp.ClientError as err:
            raise JetCloudApiError(f"Connection error: {err}")

    async def _async_request(self, endpoint: str, payload: Dict[str, Any], content_type: str, retry: bool = True) -> Dict[str, Any]:
        if not self.token:
            await self.authenticate()

        url: str = f"{BASE_URL}{endpoint}"
        headers: Dict[str, str] = self._get_base_headers()
        headers["Content-Type"] = content_type

        request_kwargs: Dict[str, Any] = {"json": payload} if "json" in content_type else {"data": payload}

        try:
            async with self.session.post(url, headers=headers, **request_kwargs) as response:
                if response.status in (401, 403) and retry:
                    self.token = None
                    return await self._async_request(endpoint, payload, content_type, retry=False)
                    
                if response.status != 200:
                    raise JetCloudApiError(f"HTTP error {response.status} calling {endpoint}")

                data: Dict[str, Any] = await response.json()
                
                if data.get("result") != 0:
                    if retry:
                        self.token = None
                        return await self._async_request(endpoint, payload, content_type, retry=False)
                    raise JetCloudApiError(f"API returned error: {data.get('msg')}")
                    
                return data
        except aiohttp.ClientError as err:
            raise JetCloudApiError(f"Connection error calling {endpoint}: {err}")

    async def get_devices(self) -> List[str]:
        payload: Dict[str, int] = {"pageNow": 1, "pageSize": 99}
        data: Dict[str, Any] = await self._async_request("/plant/getPlantPage", payload, "application/json;charset=UTF-8")
        
        device_sns: List[str] = []
        plants: List[Dict[str, Any]] = data.get("obj", {}).get("dataList", [])
        for plant in plants:
            device_sns.extend(plant.get("deviceSnList", []))
        return device_sns

    async def get_device_telemetry(self, device_sn: str, device_type: int = 57) -> Dict[str, float]:
        payload: Dict[str, Any] = {
            "deviceType": device_type,
            "sn": device_sn,
            "time": datetime.now().strftime("%Y-%m-%d")
        }
        
        data: Dict[str, Any] = await self._async_request("/device/getDeviceBySn", payload, "application/x-www-form-urlencoded")
        info_map: Dict[str, Any] = data.get("obj", {}).get("deviceInfoMap", {})
        return self._parse_telemetry(info_map)

    def _parse_telemetry(self, info_map: Dict[str, Any]) -> Dict[str, float]:
        parsed_data: Dict[str, float] = {}
        target_categories: List[str] = ["Grid Information", "PV Information"]
        
        for category in target_categories:
            if category in info_map:
                for key, value_str in info_map[category].items():
                    if isinstance(value_str, str):
                        match: Optional[re.Match] = re.search(r"(-?\d+\.?\d*)", value_str)
                        if match:
                            clean_key: str = key.lower().replace(" ", "_").replace("-", "_")
                            parsed_data[clean_key] = float(match.group(1))
        return parsed_data