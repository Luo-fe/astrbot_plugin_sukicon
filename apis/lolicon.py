from typing import Optional
from .base import BaseImageAPI, ImageData

from astrbot.api import logger


class LoliconAPI(BaseImageAPI):
    API_NAME = "Lolicon"
    API_URL = "https://api.lolicon.app/setu/v2"

    async def fetch_images(
        self,
        r18: int = 0,
        num: int = 1,
        tag: Optional[list[str]] = None,
        keyword: Optional[str] = None,
        uid: Optional[list[int]] = None,
        size: Optional[list[str]] = None,
        proxy: str = "i.pixiv.re",
        exclude_ai: bool = False,
        aspect_ratio: Optional[str] = None,
    ) -> list[ImageData]:
        params = self.build_params(
            r18=r18,
            num=num,
            tag=tag,
            keyword=keyword,
            uid=uid,
            size=size,
            proxy=proxy,
            exclude_ai=exclude_ai,
            aspect_ratio=aspect_ratio,
        )
        
        logger.info(f"[Lolicon] 请求参数: {params}")
        response = await self._request(params)
        logger.info(f"[Lolicon] 响应状态: error={response.get('error', '')}, data_count={len(response.get('data', []))}")
        
        return self.parse_response(response)

    def build_params(
        self,
        r18: int = 0,
        num: int = 1,
        tag: Optional[list[str]] = None,
        keyword: Optional[str] = None,
        uid: Optional[list[int]] = None,
        size: Optional[list[str]] = None,
        proxy: str = "i.pixiv.re",
        exclude_ai: bool = False,
        aspect_ratio: Optional[str] = None,
    ) -> dict:
        params = {
            "r18": r18,
            "num": min(max(1, num), 20),
            "proxy": proxy,
        }
        
        if tag:
            params["tag"] = tag
        if keyword:
            params["keyword"] = keyword
        if uid:
            params["uid"] = uid
        if size:
            params["size"] = size
        if exclude_ai:
            params["excludeAI"] = True
        if aspect_ratio:
            params["aspectRatio"] = aspect_ratio
            
        return params

    def parse_response(self, response: dict) -> list[ImageData]:
        error = response.get("error")
        if error:
            logger.error(f"[Lolicon] API错误: {error}")
            return []
        
        data = response.get("data", [])
        images = []
        
        for item in data:
            try:
                image = ImageData(
                    pid=item.get("pid", 0),
                    p=item.get("p", 0),
                    uid=item.get("uid", 0),
                    title=item.get("title", "未知标题"),
                    author=item.get("author", "未知作者"),
                    r18=item.get("r18", False),
                    width=item.get("width", 0),
                    height=item.get("height", 0),
                    tags=item.get("tags", []),
                    ext=item.get("ext", "jpg"),
                    urls=item.get("urls", {}),
                    upload_date=item.get("uploadDate"),
                    ai_type=item.get("aiType"),
                    source="Lolicon",
                )
                images.append(image)
            except Exception as e:
                logger.error(f"[Lolicon] 解析图片数据失败: {e}")
                
        return images
