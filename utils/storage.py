import os
import httpx
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from astrbot.api import logger

from ..apis.base import ImageData


class ImageStorage:
    _global_lock = asyncio.Lock()
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._counter_file = storage_path / ".counter"
        self._ensure_directory()

    def _ensure_directory(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def _get_next_index(self) -> int:
        async with self._global_lock:
            counter = 1
            if self._counter_file.exists():
                try:
                    with open(self._counter_file, 'r', encoding='utf-8') as f:
                        counter = int(f.read().strip()) + 1
                except Exception:
                    counter = 1
            
            with open(self._counter_file, 'w', encoding='utf-8') as f:
                f.write(str(counter))
            
            return counter

    async def save_image(self, image: ImageData) -> Optional[Path]:
        if not image.original_url:
            logger.warning(f"[ImageStorage] 图片无有效URL: PID={image.pid}")
            return None

        try:
            index = await self._get_next_index()
            ext = image.ext or "jpg"
            image_filename = f"{index:05d}.{ext}"
            txt_filename = f"{index:05d}.txt"
            
            image_path = self.storage_path / image_filename
            txt_path = self.storage_path / txt_filename
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream('GET', image.original_url) as response:
                    response.raise_for_status()
                    
                    with open(image_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            await self._save_metadata(txt_path, image)
            
            logger.info(f"[ImageStorage] 保存图片成功: {image_path}")
            return image_path
                
        except httpx.HTTPStatusError as e:
            logger.error(f"[ImageStorage] 下载图片HTTP错误: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"[ImageStorage] 下载图片超时")
        except Exception as e:
            logger.error(f"[ImageStorage] 保存图片失败: {e}")
        
        return None

    async def _save_metadata(self, txt_path: Path, image: ImageData):
        content = f"""PID: {image.pid}
标题: {image.title}
作者: {image.author}
标签: {', '.join(image.tags)}
来源: {image.source}
获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        if image.level is not None:
            content += f"Level: {image.level}\n"
        if image.taste is not None:
            content += f"Taste: {image.taste}\n"
        if image.description:
            content += f"描述: {image.description}\n"
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_metadata_sync, txt_path, content)
    
    def _write_metadata_sync(self, txt_path: Path, content: str):
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
