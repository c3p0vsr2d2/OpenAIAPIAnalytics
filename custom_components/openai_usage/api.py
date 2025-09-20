import aiohttp
from datetime import date, timedelta
from .const import USAGE_URL

class OpenAIUsageClient:
    """Async client for fetching OpenAI usage."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_usage(self, days: int = 365):
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{USAGE_URL}?start_date={start_date}&end_date={today}",
                headers=headers,
                timeout=30,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
