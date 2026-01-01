"""
Cookie持久化与告警模块
功能:
  1. 定期保存刷新后的Cookie到文件
  2. 启动时加载持久化的Cookie
  3. Cookie失效时发送Bark通知
"""
import os
import json
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# ============ 配置 ============
COOKIE_PERSIST_PATH = Path(os.getenv("COOKIE_PERSIST_PATH", "/app/cookies_persist.json"))
COOKIE_SAVE_INTERVAL = int(os.getenv("COOKIE_SAVE_INTERVAL", 300))  # 默认5分钟保存一次

# Bark通知配置
BARK_KEY = os.getenv("BARK_KEY", "")
BARK_SERVER = os.getenv("BARK_SERVER", "https://api.day.app")
ENABLE_BARK = os.getenv("ENABLE_BARK_NOTIFICATION", "false").lower() == "true"


class CookiePersistence:
    """Cookie持久化管理器"""

    def __init__(self, persist_path: Path = COOKIE_PERSIST_PATH):
        self.persist_path = persist_path
        self._last_saved_cookies: Dict[str, str] = {}
        self._save_task: Optional[asyncio.Task] = None
        self._running = False

    def load_cookies(self) -> Optional[Dict[str, str]]:
        """从文件加载持久化的Cookie"""
        if not self.persist_path.exists():
            logger.info(f"Cookie持久化文件不存在: {self.persist_path}")
            return None

        try:
            with open(self.persist_path, 'r') as f:
                data = json.load(f)

            cookies = data.get("cookies", {})
            saved_at = data.get("saved_at", "unknown")

            # 验证Cookie完整性
            required_keys = ["__Secure-1PSID", "__Secure-1PSIDCC", "__Secure-1PSIDTS"]
            if all(cookies.get(k) for k in required_keys):
                logger.info(f"已加载持久化Cookie (保存于: {saved_at})")
                return cookies
            else:
                logger.warning("持久化Cookie不完整，忽略")
                return None

        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return None

    def save_cookies(self, cookies: Dict[str, str]) -> bool:
        """保存Cookie到文件"""
        try:
            # 检查是否有变化
            if cookies == self._last_saved_cookies:
                return True

            data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "version": "v4.0"
            }

            # 确保目录存在
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.persist_path, 'w') as f:
                json.dump(data, f, indent=2)

            self._last_saved_cookies = cookies.copy()
            logger.debug(f"Cookie已保存到: {self.persist_path}")
            return True

        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False

    async def start_auto_save(self, get_cookies_func):
        """启动自动保存任务

        Args:
            get_cookies_func: 获取当前Cookie的回调函数
        """
        self._running = True
        logger.info(f"Cookie自动保存已启动 (间隔: {COOKIE_SAVE_INTERVAL}秒)")

        while self._running:
            try:
                await asyncio.sleep(COOKIE_SAVE_INTERVAL)

                cookies = get_cookies_func()
                if cookies:
                    self.save_cookies(cookies)

            except asyncio.CancelledError:
                logger.info("Cookie自动保存任务已取消")
                break
            except Exception as e:
                logger.error(f"自动保存Cookie出错: {e}")

    def stop(self):
        """停止自动保存"""
        self._running = False
        if self._save_task:
            self._save_task.cancel()


class BarkNotifier:
    """Bark通知管理器"""

    def __init__(self, key: str = BARK_KEY, server: str = BARK_SERVER):
        self.key = key
        self.server = server.rstrip('/')
        self.enabled = bool(key) and ENABLE_BARK
        self._last_notify_time: Dict[str, float] = {}
        self._notify_cooldown = 3600  # 同类通知冷却时间(秒)

    async def notify(self, title: str, body: str, group: str = "gemini-api") -> bool:
        """发送Bark通知

        Args:
            title: 通知标题
            body: 通知内容
            group: 通知分组
        """
        if not self.enabled:
            logger.debug("Bark通知未启用")
            return False

        # 检查冷却时间
        now = datetime.now().timestamp()
        last_time = self._last_notify_time.get(group, 0)
        if now - last_time < self._notify_cooldown:
            logger.debug(f"通知冷却中: {group}")
            return False

        try:
            url = f"{self.server}/{self.key}/{title}/{body}"
            params = {"group": group, "sound": "alarm"}

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                self._last_notify_time[group] = now
                logger.info(f"Bark通知已发送: {title}")
                return True
            else:
                logger.warning(f"Bark通知失败: {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"Bark通知出错: {e}")
            return False

    async def notify_cookie_expired(self):
        """Cookie过期通知"""
        await self.notify(
            title="⚠️ Gemini Cookie过期",
            body="请尽快更新Cookie，服务已受影响",
            group="cookie-expired"
        )

    async def notify_cookie_refreshed(self):
        """Cookie刷新成功通知"""
        await self.notify(
            title="✅ Cookie已刷新",
            body=f"自动刷新成功 - {datetime.now().strftime('%H:%M')}",
            group="cookie-refreshed"
        )

    async def notify_service_error(self, error: str):
        """服务错误通知"""
        await self.notify(
            title="🔴 Gemini API错误",
            body=error[:100],
            group="service-error"
        )


# 全局实例
cookie_persistence = CookiePersistence()
bark_notifier = BarkNotifier()
