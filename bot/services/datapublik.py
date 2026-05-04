import aiohttp
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class SourceResult:
    source: str
    status_code: int
    name: Optional[str] = None
    tags: list[dict] = field(default_factory=list)
    tag_count: int = 0
    error: Optional[str] = None
    profile_image: Optional[str] = None
    raw_data: Optional[dict] = None # Simpan respon mentah untuk fleksibilitas

@dataclass
class MultiSourceResponse:
    success: bool
    message: str
    phone_number: str
    sources: list[SourceResult] = field(default_factory=list)
    remaining_tokens: int = 0
    from_cache: bool = False
    error: Optional[str] = None

class DataPublikClient:
    """Client for interacting with the data-publik.com API."""

    def __init__(self, base_url: str, default_key: str):
        self.base_url = base_url.rstrip("/")
        self.default_key = default_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_multisource(self, phone_number: str, key: Optional[str] = None) -> tuple[MultiSourceResponse, dict]:
        """
        Perform a multi-source phone number lookup.
        Returns a tuple of (MultiSourceResponse, raw_data_dict).
        """
        url = self.base_url
        
        # Ensure phone starts with + as per user request example: "+628111806159"
        full_phone = phone_number if phone_number.startswith("+") else f"+{phone_number}"
        
        payload = {
            "phoneNumber": full_phone,
            "key": key or self.default_key
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return MultiSourceResponse(
                            success=False, 
                            message=f"HTTP Error {resp.status}", 
                            phone_number=phone_number,
                            error=error_text
                        ), {}
                    
                    data = await resp.json()
                    return self._parse_multisource_response(phone_number, data), data
                    
        except Exception as e:
            logger.error(f"Multisource search error: {e}")
            return MultiSourceResponse(
                success=False, 
                message="Network or parsing error", 
                phone_number=phone_number,
                error=str(e)
            ), {}

    def _parse_multisource_response(self, phone: str, data: dict) -> MultiSourceResponse:
        """Parse the raw API response into MultiSourceResponse object."""
        success = data.get("success", False)
        message = data.get("message", "")
        remaining_tokens = data.get("remainingTokens", 0)
        from_cache = data.get("fromCache", False)
        
        sources_list = []
        api_data = data.get("data", {})
        raw_sources = api_data.get("sources", [])
        
        for s in raw_sources:
            source_name = s.get("source", "unknown")
            results = s.get("results", {})
            status_code = results.get("statusCode", 0)
            response = results.get("response", {})
            
            source_res = SourceResult(
                source=source_name,
                status_code=status_code,
                raw_data=response
            )
            
            if status_code == 200:
                # Handle different sources based on their typical response structure
                if source_name == "getcontact":
                    source_res.name = response.get("displayName")
                    source_res.tag_count = response.get("tagCount", 0)
                    source_res.profile_image = response.get("profileImage")
                    # Extract tags
                    extra = response.get("extra", {})
                    source_res.tags = extra.get("tags", [])
                else:
                    # Generic name extraction for truecaller, callapp, callerid, etc.
                    source_res.name = response.get("name")
            else:
                source_res.error = response.get("error", "Unknown error")
                
            sources_list.append(source_res)
            
        return MultiSourceResponse(
            success=success,
            message=message,
            phone_number=phone,
            sources=sources_list,
            remaining_tokens=remaining_tokens,
            from_cache=from_cache
        )
