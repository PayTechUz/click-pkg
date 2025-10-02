import httpx
from httpx import AsyncClient, AsyncHTTPTransport

# Global reusable async client
async_http_transport = AsyncHTTPTransport(retries=3, http2=True)
async_http_client = AsyncClient(
    transport=async_http_transport,
    timeout=10,
)


class Http:
    def __init__(self):
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def post(
            self,
            url: str,
            body: dict,
            headers: dict,
            timeout: int = 10
    ):
        """
        POST so‘rovini asinxron yuborish.
        """
        headers = {**self.default_headers, **(headers or {})}

        try:
            response = await async_http_client.post(
                url,
                headers=headers,
                json=body,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # 2xx bo'lmagan javob
            return {
                "error": True,
                "status_code": e.response.status_code,
                "detail": e.response.text,
            }
        except httpx.RequestError as e:
            # Tarmoq xatosi, vaqt tugashi, DNS va boshqalar.
            return {
                "error": True,
                "detail": str(e),
            }
