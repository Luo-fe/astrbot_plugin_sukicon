from __future__ import annotations

import asyncio
from pathlib import Path
from collections.abc import Mapping, MutableMapping
from collections import deque
from types import MappingProxyType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
import random

from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.api.star import StarTools


class ConfigNode:
    _SCHEMA_CACHE: dict[type, dict[str, type]] = {}
    _FIELDS_CACHE: dict[type, set[str]] = {}

    @classmethod
    def _schema(cls) -> dict[str, type]:
        return cls._SCHEMA_CACHE.setdefault(cls, get_type_hints(cls))

    @classmethod
    def _fields(cls) -> set[str]:
        return cls._FIELDS_CACHE.setdefault(
            cls,
            {k for k in cls._schema() if not k.startswith("_")},
        )

    @staticmethod
    def _is_optional(tp: type) -> bool:
        if get_origin(tp) in (Union, UnionType):
            return type(None) in get_args(tp)
        return False

    def __init__(self, data: MutableMapping[str, Any]):
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_children", {})
        for key, tp in self._schema().items():
            if key.startswith("_"):
                continue
            if key in data:
                continue
            if hasattr(self.__class__, key):
                continue
            if self._is_optional(tp):
                continue
            logger.warning(f"[config:{self.__class__.__name__}] 缺少字段: {key}")

    def __getattr__(self, key: str) -> Any:
        if key in self._fields():
            value = self._data.get(key)
            tp = self._schema().get(key)

            if isinstance(tp, type) and issubclass(tp, ConfigNode):
                children: dict[str, ConfigNode] = self.__dict__["_children"]
                if key not in children:
                    if not isinstance(value, MutableMapping):
                        raise TypeError(
                            f"[config:{self.__class__.__name__}] "
                            f"字段 {key} 期望 dict，实际是 {type(value).__name__}"
                        )
                    children[key] = tp(value)
                return children[key]

            return value

        if key in self.__dict__:
            return self.__dict__[key]

        raise AttributeError(key)

    def __setattr__(self, key: str, value: Any) -> None:
        if key in self._fields():
            self._data[key] = value
            return
        object.__setattr__(self, key, value)

    def raw_data(self) -> Mapping[str, Any]:
        return MappingProxyType(self._data)

    def save_config(self) -> None:
        if not isinstance(self._data, AstrBotConfig):
            raise RuntimeError(
                f"{self.__class__.__name__}.save_config() 只能在根配置节点上调用"
            )
        self._data.save_config()


class LoliconConfig(ConfigNode):
    storage_path: str
    default_size: list[str]
    default_proxy: str


class SukiConfig(ConfigNode):
    storage_path: str
    default_level: str
    default_taste: str
    default_proxy: str


class FunnyRepliesConfig(ConfigNode):
    enabled: bool
    fetching: list[str]
    success: list[str]
    no_result: list[str]
    network_error: list[str]
    timeout: list[str]
    cooldown: list[str]
    r18_on: list[str]
    r18_off: list[str]

    def get_random(self, key: str) -> str:
        replies = getattr(self, key, [])
        if not replies:
            return ""
        return random.choice(replies)


class PluginConfig(ConfigNode):
    r18_mode: bool
    cooldown_seconds: int
    max_concurrent_requests: int
    request_timeout: int
    max_retries: int
    enable_logging: bool
    log_retention_days: int
    enable_local_storage: bool
    enable_deduplication: bool
    dedup_history_size: int
    lolicon: LoliconConfig
    suki: SukiConfig
    funny_replies: FunnyRepliesConfig

    _plugin_name = "astrbot_plugin_sukicon"

    def __init__(self, cfg: AstrBotConfig):
        super().__init__(cfg)

        self.data_dir = StarTools.get_data_dir(self._plugin_name)
        self.logs_dir = self.data_dir / "logs"
        self.state_file = self.data_dir / "state.json"
        self.dedup_file = self.data_dir / "dedup.json"

        self._init_directories()
        self._init_state()
        self._init_dedup()

    def _init_directories(self):
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        if self.enable_local_storage:
            lolicon_path = self.get_storage_path('lolicon')
            suki_path = self.get_storage_path('suki')
            lolicon_path.mkdir(parents=True, exist_ok=True)
            suki_path.mkdir(parents=True, exist_ok=True)

    def _init_state(self):
        import json
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    r18_mode = state.get('r18_mode', self.r18_mode)
                    
                    if not isinstance(r18_mode, bool):
                        logger.warning(f"无效的 R18 模式值: {r18_mode}，重置为 {self.r18_mode}")
                        r18_mode = self.r18_mode
                    
                    self._r18_mode = r18_mode
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")
                self._r18_mode = self.r18_mode
        else:
            self._r18_mode = self.r18_mode

    def save_state(self):
        import json
        state = {
            'r18_mode': self._r18_mode
        }
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    @property
    def r18_mode_enabled(self) -> bool:
        return self._r18_mode

    @r18_mode_enabled.setter
    def r18_mode_enabled(self, value: bool):
        self._r18_mode = value
        self.save_state()

    def toggle_r18(self) -> bool:
        self.r18_mode_enabled = not self._r18_mode
        return self._r18_mode

    def get_storage_path(self, api_type: str) -> Path:
        if api_type == 'lolicon':
            path = self.lolicon.storage_path
        else:
            path = self.suki.storage_path
        
        if path:
            return Path(path)
        else:
            return self.data_dir / "images" / api_type

    def get_funny_reply(self, reply_type: str) -> str:
        if not self.funny_replies.enabled:
            return ""
        return self.funny_replies.get_random(reply_type)

    def _init_dedup(self):
        import json
        self._dedup_lock = asyncio.Lock()
        self._sent_pids: deque[int] = deque(maxlen=self.dedup_history_size)
        if self.dedup_file.exists():
            try:
                with open(self.dedup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    pids_list = data.get('sent_pids', [])
                    self._sent_pids = deque(pids_list[-self.dedup_history_size:], maxlen=self.dedup_history_size)
            except Exception as e:
                logger.warning(f"加载去重文件失败: {e}")
                self._sent_pids = deque(maxlen=self.dedup_history_size)

    def is_pid_sent(self, pid: int) -> bool:
        if not self.enable_deduplication:
            return False
        return pid in self._sent_pids

    async def mark_pids_sent(self, pids: list[int]):
        if not self.enable_deduplication or not pids:
            return
        async with self._dedup_lock:
            for pid in pids:
                if pid not in self._sent_pids:
                    self._sent_pids.append(pid)
            await self._save_dedup_async()

    async def _save_dedup_async(self):
        import json
        pids_list = list(self._sent_pids)
        try:
            with open(self.dedup_file, 'w', encoding='utf-8') as f:
                json.dump({'sent_pids': pids_list}, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存去重文件失败: {e}")
