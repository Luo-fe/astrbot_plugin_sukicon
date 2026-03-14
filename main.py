import asyncio
from pathlib import Path
from typing import Optional

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Image, Plain

from .config import PluginConfig
from .apis import LoliconAPI, SukiAPI, ImageData
from .utils import APILogger, ImageStorage, parse_setu_args, parse_suki_args, format_image_info


MANUAL_GENERAL = """📖 涩涩手册

【基础指令】
• 切换r18 / r18开关
  切换R18模式 (开/关)
  
• 当前状态 / status
  查看当前R18模式状态

【Lolicon API 命令】
• 色图 / setu / 涩图 [标签] [数量]
  使用Lolicon API获取图片（受R18模式影响）

• 色图r18 / setur18 [标签] [数量]
  强制获取R18图片

• 色图全年龄 / setusafe [标签] [数量]
  强制获取非R18图片

【Suki API 命令】
• suki [标签] [level 等级] [taste 类型] [数量]
  使用Suki API获取图片（受R18模式影响）

• sukir18 [标签] [level 等级] [数量]
  强制获取R18图片

• suki全年龄 / sukisafe [标签] [level 等级] [taste 类型] [数量]
  强制获取非R18图片

【说明】
- R18模式开启后，所有图片获取命令默认获取R18图片
- 使用"色图r18"或"sukir18"可强制获取R18图片
- 使用"色图全年龄"或"suki全年龄"可强制获取非R18图片

【更多帮助】
• lolicon手册 / lolicon - 查看Lolicon API使用说明
• suki手册 / sukihelp - 查看Suki API使用说明
"""

MANUAL_LOLICON = """📖 Lolicon API 手册

【基础命令】
• 色图 / setu / 涩图 [标签] [数量]
  获取图片（受R18模式影响）

• 色图r18 / setur18 [标签] [数量]
  强制获取R18图片

• 色图全年龄 / setusafe [标签] [数量]
  强制获取非R18图片

【标签搜索】
• 多个标签为OR关系（任一匹配）
• 示例：
  - 色图 白丝
  - 色图 白丝 黑丝
  - 色图 白丝 黑丝 3

【数量控制】
• 单次最多获取20张图片
• 示例：色图 5

【图片存储】
• 图片自动保存到本地
• 默认路径：插件数据目录/images/lolicon
• 可在配置中自定义存储路径
"""

MANUAL_SUKI = """📖 Suki API 手册

【基础命令】
• suki [标签] [level 等级] [taste 类型] [数量]
  获取图片（受R18模式影响）

• sukir18 [标签] [level 等级] [数量]
  强制获取R18图片

• suki全年龄 / sukisafe [标签] [level 等级] [taste 类型] [数量]
  强制获取非R18图片

【Level参数 - 社保程度】
• 0: 除了好看以外没什么特别之处
• 1: 好看，也有点涩
• 2: 涩
• 3: 很涩
• 4: R18擦边球
• 5: R18
• 6: R18+有氧模式
• 支持范围：level 2-4

【Taste参数 - 图片类型】
• 0: 随机
• 1: 萝莉
• 2: 少女
• 3: 御姐
• 支持多选：taste 1,2

【综合搜索示例】
• suki 拉菲 level 3 taste 1
  获取拉菲标签、level 3、萝莉类型

• suki 白丝 黑丝 level 2-4 taste 1,2
  获取白丝或黑丝、level 2-4、萝莉或少女类型

• suki level 5 taste 3
  获取level 5、御姐类型的图片

【数量控制】
• 单次最多获取5张图片

【图片存储】
• 图片自动保存到本地
• 默认路径：插件数据目录/images/suki
• 可在配置中自定义存储路径
"""


@register(
    "astrbot_plugin_sukicon", 
    "Luo-fe", 
    "一个功能完整的 AstrBot 插件，集成 Lolicon API 和 Suki Loli API，实现图像资源获取功能。", 
    "1.1.0"
)
class SukiconPlugin(Star):
    _plugin_name = "astrbot_plugin_sukicon"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = PluginConfig(config)
        
        self.lolicon_api = LoliconAPI(
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            max_concurrent=self.config.max_concurrent_requests,
        )
        
        self.suki_api = SukiAPI(
            timeout=self.config.request_timeout,
            max_retries=self.config.max_retries,
            max_concurrent=self.config.max_concurrent_requests,
        )
        
        self.api_logger = APILogger(
            self.config.logs_dir,
            self.config.log_retention_days,
        ) if self.config.enable_logging else None
        
        self.lolicon_storage = ImageStorage(
            self.config.get_storage_path('lolicon')
        ) if self.config.enable_local_storage else None
        
        self.suki_storage = ImageStorage(
            self.config.get_storage_path('suki')
        ) if self.config.enable_local_storage else None
        
        self.last_usage = {}
        self.cooldown_lock = asyncio.Lock()
        self.semaphore = None

    async def initialize(self):
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        logger.info(f"[Sukicon] 插件初始化完成")
        logger.info(f"[Sukicon] R18模式: {'开启' if self.config.r18_mode_enabled else '关闭'}")

    async def terminate(self):
        if self.lolicon_api:
            await self.lolicon_api.close()
        if self.suki_api:
            await self.suki_api.close()
        if self.lolicon_storage:
            await self.lolicon_storage.close()
        if self.suki_storage:
            await self.suki_storage.close()
        logger.info("[Sukicon] 插件已卸载")

    async def _check_and_update_cooldown(self, user_id: str) -> Optional[float]:
        async with self.cooldown_lock:
            now = asyncio.get_event_loop().time()
            if user_id in self.last_usage:
                elapsed = now - self.last_usage[user_id]
                if elapsed < self.config.cooldown_seconds:
                    return self.config.cooldown_seconds - elapsed
            self.last_usage[user_id] = now
            return None

    async def _save_images(self, images: list[ImageData], api_type: str):
        if not self.config.enable_local_storage:
            return
        
        storage = self.lolicon_storage if api_type == 'lolicon' else self.suki_storage
        if storage:
            for image in images:
                try:
                    await storage.save_image(image)
                except Exception as e:
                    logger.error(f"[Sukicon] 保存图片失败: {e}")

    async def _fetch_and_respond(
        self,
        event: AstrMessageEvent,
        api_type: str,
        r18: int,
        num: int,
        tags: list[str],
        level: Optional[str] = None,
        taste: Optional[str] = None,
    ):
        user_id = str(event.get_sender_id())
        
        cooldown = await self._check_and_update_cooldown(user_id)
        if cooldown:
            reply = self.config.get_funny_reply('cooldown')
            if reply:
                yield event.plain_result(f"{reply}\n(还需等待 {cooldown:.1f} 秒)")
            else:
                yield event.plain_result(f"冷却中，请等待 {cooldown:.1f} 秒后重试")
            return
        
        fetching_reply = self.config.get_funny_reply('fetching')
        if fetching_reply:
            yield event.plain_result(fetching_reply)
        
        async with self.semaphore:
            try:
                if self.config.enable_deduplication:
                    if api_type == 'lolicon':
                        fetch_num = min(num * 3, 20)
                    else:
                        fetch_num = min(num * 3, 5)
                    max_attempts = 3
                else:
                    fetch_num = num
                    max_attempts = 1
                
                images = []
                total_fetched = 0
                seen_pids_this_batch = set()
                
                for attempt in range(max_attempts):
                    if api_type == 'lolicon':
                        batch = await self.lolicon_api.fetch_images(
                            r18=r18,
                            num=fetch_num,
                            tag=tags if tags else None,
                            size=self.config.lolicon.default_size,
                            proxy=self.config.lolicon.default_proxy,
                        )
                    else:
                        batch = await self.suki_api.fetch_images(
                            r18=r18,
                            num=fetch_num,
                            tag=tags if tags else None,
                            level=level or self.config.suki.default_level,
                            taste=taste or self.config.suki.default_taste,
                            proxy=self.config.suki.default_proxy,
                        )
                    
                    total_fetched += len(batch)
                    
                    if self.config.enable_deduplication:
                        for img in batch:
                            if not self.config.is_pid_sent(img.pid) and img.pid not in seen_pids_this_batch:
                                images.append(img)
                                seen_pids_this_batch.add(img.pid)
                        if len(images) >= num:
                            images = images[:num]
                            break
                        if not batch:
                            break
                    else:
                        images = batch
                        break
                
                if self.api_logger:
                    await self.api_logger.log_api_call(
                        api_type,
                        {'r18': r18, 'num': num, 'tags': tags, 'level': level, 'taste': taste},
                        {'data': [img.to_dict() for img in images]},
                        success=len(images) > 0,
                    )
                
                if not images:
                    if self.config.enable_deduplication and total_fetched > 0:
                        yield event.plain_result("这个条件下的图片都发过了，换个条件试试吧~\n提示：可以尝试不同的 level 或 taste 参数")
                    else:
                        reply = self.config.get_funny_reply('no_result')
                        if reply:
                            yield event.plain_result(reply)
                        else:
                            yield event.plain_result("没有找到符合条件的图片")
                    return
                
                await self.config.mark_pids_sent([img.pid for img in images])
                
                await self._save_images(images, api_type)
                
                success_reply = self.config.get_funny_reply('success')
                
                if len(images) == 1:
                    image = images[0]
                    chain = [
                        Image.fromURL(image.regular_url),
                        Plain("\n" + format_image_info(image)),
                    ]
                    if success_reply:
                        chain.insert(0, Plain(success_reply + "\n"))
                    yield event.chain_result(chain)
                else:
                    chains = []
                    if success_reply:
                        chains.append(Plain(f"{success_reply}\n\n为您找到 {len(images)} 张图片：\n"))
                    else:
                        chains.append(Plain(f"为您找到 {len(images)} 张图片：\n"))
                    
                    for i, image in enumerate(images, 1):
                        chains.append(Image.fromURL(image.regular_url))
                        chains.append(Plain(f"\n[{i}] PID: {image.pid} - {image.title}\n"))
                    
                    yield event.chain_result(chains)
                    
            except asyncio.TimeoutError:
                reply = self.config.get_funny_reply('timeout')
                if reply:
                    yield event.plain_result(reply)
                else:
                    yield event.plain_result("请求超时，请稍后重试")
            except Exception as e:
                logger.error(f"[Sukicon] 获取图片失败: {e}")
                error_str = str(e).lower()
                
                if 'connect' in error_str or 'connection' in error_str or 'network' in error_str:
                    reply = self.config.get_funny_reply('network_error')
                elif 'timeout' in error_str:
                    reply = self.config.get_funny_reply('timeout')
                else:
                    reply = self.config.get_funny_reply('network_error')
                
                if reply:
                    yield event.plain_result(reply)
                else:
                    yield event.plain_result(f"获取图片失败：{str(e)}")

    @filter.command("切换r18", alias={"r18开关"})
    async def switch_r18(self, event: AstrMessageEvent):
        if not self._is_admin(event):
            yield event.plain_result("⚠️ 此命令仅限管理员使用")
            return
        
        new_state = self.config.toggle_r18()
        if new_state:
            reply = self.config.get_funny_reply('r18_on')
        else:
            reply = self.config.get_funny_reply('r18_off')
        
        if reply:
            yield event.plain_result(reply)
        else:
            state_text = "开启" if new_state else "关闭"
            yield event.plain_result(f"R18模式已{state_text}")

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        try:
            role_info = event.get_sender_role()
            if role_info and role_info in ['admin', 'owner', 'superuser']:
                return True
            
            sender_id = str(event.get_sender_id())
            if hasattr(self.config, 'admin_users') and sender_id in self.config.admin_users:
                return True
            
            return False
        except Exception as e:
            logger.warning(f"[Sukicon] 权限检查异常: {e}")
            return False

    @filter.command("当前状态", alias={"status"})
    async def show_status(self, event: AstrMessageEvent):
        r18_state = "开启" if self.config.r18_mode_enabled else "关闭"
        
        status = f"""当前状态：
R18模式: {r18_state}
Lolicon存储路径: {self.config.get_storage_path('lolicon')}
Suki存储路径: {self.config.get_storage_path('suki')}"""
        yield event.plain_result(status)

    @filter.command("涩涩手册", alias={"sssc"})
    async def show_general_manual(self, event: AstrMessageEvent):
        yield event.plain_result(MANUAL_GENERAL)

    @filter.command("lolicon手册", alias={"lolicon"})
    async def show_lolicon_manual(self, event: AstrMessageEvent):
        yield event.plain_result(MANUAL_LOLICON)

    @filter.command("suki手册", alias={"sukihelp"})
    async def show_suki_manual(self, event: AstrMessageEvent):
        yield event.plain_result(MANUAL_SUKI)

    @filter.command("色图", alias={"setu", "涩图"})
    async def get_setu(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        cmd_match = None
        for cmd in ["色图", "setu", "涩图"]:
            if full_msg.lower().startswith(cmd):
                cmd_match = cmd
                break
        if cmd_match:
            args = full_msg[len(cmd_match):].strip()
        else:
            args = args or ""
        
        parsed = parse_setu_args(args, self.config.r18_mode_enabled)
        r18 = parsed.r18_override if parsed.r18_override is not None else (1 if self.config.r18_mode_enabled else 0)
        
        async for result in self._fetch_and_respond(
            event, "lolicon", r18, parsed.num, parsed.tags
        ):
            yield result

    @filter.command("色图r18", alias={"setur18"})
    async def get_setu_r18(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        cmd_match = None
        for cmd in ["色图r18", "setur18"]:
            if full_msg.lower().startswith(cmd):
                cmd_match = cmd
                break
        if cmd_match:
            args = full_msg[len(cmd_match):].strip()
        else:
            args = args or ""
        
        parsed = parse_setu_args(args, False)
        
        async for result in self._fetch_and_respond(
            event, "lolicon", 1, parsed.num, parsed.tags
        ):
            yield result

    @filter.command("色图全年龄", alias={"setusafe"})
    async def get_setu_safe(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        cmd_match = None
        for cmd in ["色图全年龄", "setusafe"]:
            if full_msg.lower().startswith(cmd):
                cmd_match = cmd
                break
        if cmd_match:
            args = full_msg[len(cmd_match):].strip()
        else:
            args = args or ""
        
        parsed = parse_setu_args(args, False)
        
        async for result in self._fetch_and_respond(
            event, "lolicon", 0, parsed.num, parsed.tags
        ):
            yield result

    @filter.command("suki")
    async def get_suki(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        if full_msg.lower().startswith("suki"):
            args = full_msg[4:].strip()
        else:
            args = args or ""
        
        parsed = parse_suki_args(args)
        
        level = parsed.level or self.config.suki.default_level
        
        if parsed.has_r18_level:
            r18 = 1
        elif self.config.r18_mode_enabled:
            r18 = 2
        else:
            r18 = 0
        
        logger.info(f"[Sukicon] suki命令解析: args={args}, level={level}, has_r18_level={parsed.has_r18_level}, final_r18={r18}")
        
        async for result in self._fetch_and_respond(
            event, "suki", r18, parsed.num, parsed.tags, level, parsed.taste
        ):
            yield result

    @filter.command("sukir18")
    async def get_suki_r18(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        if full_msg.lower().startswith("sukir18"):
            args = full_msg[7:].strip()
        else:
            args = args or ""
        
        parsed = parse_suki_args(args)
        
        async for result in self._fetch_and_respond(
            event, "suki", 1, parsed.num, parsed.tags, parsed.level, parsed.taste
        ):
            yield result

    @filter.command("suki全年龄", alias={"sukisafe"})
    async def get_suki_safe(self, event: AstrMessageEvent, args: Optional[str] = None):
        full_msg = event.get_message_str()
        cmd_match = None
        for cmd in ["suki全年龄", "sukisafe"]:
            if full_msg.lower().startswith(cmd):
                cmd_match = cmd
                break
        if cmd_match:
            args = full_msg[len(cmd_match):].strip()
        else:
            args = args or ""
        
        parsed = parse_suki_args(args)
        
        async for result in self._fetch_and_respond(
            event, "suki", 0, parsed.num, parsed.tags, parsed.level, parsed.taste
        ):
            yield result
