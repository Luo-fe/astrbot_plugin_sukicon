import asyncio
from datetime import datetime
from pathlib import Path

from astrbot.api import logger


class APILogger:
    def __init__(self, log_dir: Path, retention_days: int = 30):
        self.log_dir = log_dir
        self.retention_days = retention_days
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log_file = None
        self._current_date = None
        self._write_lock = asyncio.Lock()
        self._last_rotation_check = 0

    def _get_log_file(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._current_date = today
            self._current_log_file = self.log_dir / f"api_calls_{today}.log"
        return self._current_log_file

    def _rotate_logs(self):
        if self.retention_days <= 0:
            return
        
        now = datetime.now().timestamp()
        if now - self._last_rotation_check < 3600:
            return
        self._last_rotation_check = now
            
        cutoff_date = now - (self.retention_days * 86400)
        for log_file in self.log_dir.glob("api_calls_*.log"):
            try:
                file_time = log_file.stat().st_mtime
                if file_time < cutoff_date:
                    log_file.unlink()
                    logger.debug(f"[APILogger] 删除过期日志: {log_file}")
            except Exception as e:
                logger.warning(f"[APILogger] 删除日志失败: {e}")

    def log_request(self, api_type: str, params: dict):
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{api_type}] [REQUEST] params={params}\n"
        self._write_log(log_entry)

    def log_response(self, api_type: str, status: str, data: dict):
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{api_type}] [{status}] data={data}\n"
        self._write_log(log_entry)

    def log_error(self, api_type: str, error: str):
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{api_type}] [ERROR] {error}\n"
        self._write_log(log_entry)

    async def _write_log(self, entry: str):
        async with self._write_lock:
            try:
                self._rotate_logs()
                log_file = self._get_log_file()
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(entry)
            except Exception as e:
                logger.error(f"[APILogger] 写入日志失败: {e}")

    async def log_api_call(self, api_type: str, params: dict, response: dict, success: bool):
        await self.log_request(api_type, params)
        if success:
            data_summary = {}
            if 'data' in response:
                data_list = response.get('data', [])
                if data_list:
                    first_item = data_list[0]
                    data_summary = {
                        'count': len(data_list),
                        'first_pid': first_item.get('pid'),
                        'first_title': first_item.get('title'),
                    }
            await self.log_response(api_type, "SUCCESS", data_summary)
        else:
            error_msg = response.get('error', response.get('message', 'Unknown error'))
            await self.log_error(api_type, error_msg)
