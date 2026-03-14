from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod
import httpx
import asyncio

from astrbot.api import logger


@dataclass
class ImageData:
    pid: int
    p: int
    uid: int
    title: str
    author: str
    r18: bool
    width: int
    height: int
    tags: list[str]
    ext: str
    urls: dict[str, str]
    upload_date: Optional[int] = None
    ai_type: Optional[int] = None
    source: str = "unknown"
    
    level: Optional[int] = None
    taste: Optional[int] = None
    description: Optional[str] = None

    @property
    def original_url(self) -> str:
        return self.urls.get('original', self.urls.get('regular', ''))

    @property
    def regular_url(self) -> str:
        return self.urls.get('regular', self.urls.get('original', ''))

    def to_dict(self) -> dict:
        return {
            'pid': self.pid,
            'p': self.p,
            'uid': self.uid,
            'title': self.title,
            'author': self.author,
            'r18': self.r18,
            'width': self.width,
            'height': self.height,
            'tags': self.tags,
            'ext': self.ext,
            'urls': self.urls,
            'upload_date': self.upload_date,
            'ai_type': self.ai_type,
            'source': self.source,
            'level': self.level,
            'taste': self.taste,
            'description': self.description,
        }


class BaseImageAPI(ABC):
    API_NAME: str = "base"
    API_URL: str = ""
    
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_concurrent: int = 10,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._max_concurrent = max_concurrent
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout, connect=5.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        max_connections=self._max_concurrent
                    )
                )
            return self._client

    async def close(self):
        async with self._client_lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                self._client = None

    async def _request(self, params: dict) -> dict:
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                client = await self._get_client()
                response = await client.post(self.API_URL, json=params)
                response.raise_for_status()
                return response.json()
                        
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(f"[{self.API_NAME}] 连接错误，重试 {retry_count + 1}/{self.max_retries}: {e}")
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[{self.API_NAME}] 请求超时，重试 {retry_count + 1}/{self.max_retries}: {e}")
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"[{self.API_NAME}] HTTP错误: {e.response.status_code}")
                raise
            except Exception as e:
                last_error = e
                logger.error(f"[{self.API_NAME}] 未知错误: {e}")
                raise
            
            retry_count += 1
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * retry_count)
        
        raise last_error or Exception("请求失败")

    @abstractmethod
    async def fetch_images(self, **kwargs) -> list[ImageData]:
        pass

    @abstractmethod
    def build_params(self, **kwargs) -> dict:
        pass

    @abstractmethod
    def parse_response(self, response: dict) -> list[ImageData]:
        pass
