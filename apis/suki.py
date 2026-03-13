from typing import Optional
from .base import BaseImageAPI, ImageData

from astrbot.api import logger


class SukiAPI(BaseImageAPI):
    API_NAME = "Suki"
    API_URL = "https://lolisuki.cn/api/setu/v1"

    TASTE_MAP = {
        0: "随机",
        1: "萝莉",
        2: "少女",
        3: "御姐",
    }

    LEVEL_MAP = {
        0: "除了好看以外没什么特别之处",
        1: "好看，也有点涩",
        2: "涩",
        3: "很涩",
        4: "R18擦边球",
        5: "R18",
        6: "R18+有氧模式",
    }

    async def fetch_images(
        self,
        r18: int = 0,
        num: int = 1,
        tag: Optional[list[str]] = None,
        level: Optional[str] = None,
        taste: Optional[str] = None,
        ai: int = 2,
        full: int = 0,
        proxy: str = "i.pixiv.re",
    ) -> list[ImageData]:
        params = self.build_params(
            r18=r18,
            num=num,
            tag=tag,
            level=level,
            taste=taste,
            ai=ai,
            full=full,
            proxy=proxy,
        )
        
        logger.info(f"[Suki] 请求参数: {params}")
        response = await self._request(params)
        logger.info(f"[Suki] 响应状态: code={response.get('code', -1)}, data_count={len(response.get('data', []))}")
        
        return self.parse_response(response)

    def build_params(
        self,
        r18: int = 0,
        num: int = 1,
        tag: Optional[list[str]] = None,
        level: Optional[str] = None,
        taste: Optional[str] = None,
        ai: int = 2,
        full: int = 0,
        proxy: str = "i.pixiv.re",
    ) -> dict:
        params = {
            "r18": r18,
            "num": min(max(1, num), 5),
            "ai": ai,
            "proxy": proxy,
            "full": full,
        }
        
        if tag:
            params["tag"] = ["|".join(tag)]
        if level:
            params["level"] = level
        if taste:
            params["taste"] = taste
            
        return params

    def parse_response(self, response: dict) -> list[ImageData]:
        code = response.get("code", -1)
        if code != 0:
            error = response.get("error", "未知错误")
            logger.error(f"[Suki] API错误: {error}")
            return []
        
        data = response.get("data", [])
        images = []
        
        for item in data:
            try:
                urls = item.get("urls", {})
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
                    urls=urls,
                    upload_date=item.get("uploadDate"),
                    ai_type=item.get("aiType"),
                    source="Suki",
                    level=item.get("level"),
                    taste=item.get("taste"),
                    description=item.get("description"),
                )
                images.append(image)
            except Exception as e:
                logger.error(f"[Suki] 解析图片数据失败: {e}")
                
        return images
