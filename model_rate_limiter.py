#!/usr/bin/env python3
"""
Redis模型限流中间件
确保同一个图片生成模型的调用间隔至少5秒
"""
import redis
import time
from typing import Optional

class ModelRateLimiter:
    """基于Redis的模型级别速率限制器"""

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0, redis_password: str = None):
        """
        初始化Redis连接

        Args:
            redis_host: Redis服务器地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            redis_password: Redis密码（可选）
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self.min_interval = 5  # 最小间隔时间（秒）

    def check_and_update(self, model_name: str, client_id: Optional[str] = None) -> tuple[bool, float]:
        """
        检查是否可以调用，并更新最后调用时间

        Args:
            model_name: 模型名称（如 imagen-3.0-generate-001）
            client_id: 客户端ID（可选，用于区分不同用户）

        Returns:
            (是否允许调用, 需要等待的秒数)
        """
        # 生成Redis key
        if client_id:
            key = f"rate_limit:model:{model_name}:client:{client_id}"
        else:
            key = f"rate_limit:model:{model_name}"

        current_time = time.time()

        # 获取最后调用时间
        last_call_time = self.redis_client.get(key)

        if last_call_time:
            last_call_time = float(last_call_time)
            elapsed = current_time - last_call_time

            if elapsed < self.min_interval:
                # 还需要等待
                wait_time = self.min_interval - elapsed
                return False, wait_time

        # 更新最后调用时间
        self.redis_client.setex(
            key,
            int(self.min_interval * 2),  # TTL设置为间隔的2倍，防止无限增长
            str(current_time)
        )

        return True, 0.0

    def get_remaining_time(self, model_name: str, client_id: Optional[str] = None) -> float:
        """
        获取还需要等待多少秒

        Returns:
            剩余等待时间（秒），0表示可以立即调用
        """
        if client_id:
            key = f"rate_limit:model:{model_name}:client:{client_id}"
        else:
            key = f"rate_limit:model:{model_name}"

        last_call_time = self.redis_client.get(key)

        if not last_call_time:
            return 0.0

        last_call_time = float(last_call_time)
        elapsed = time.time() - last_call_time

        if elapsed >= self.min_interval:
            return 0.0

        return self.min_interval - elapsed

    def reset(self, model_name: str, client_id: Optional[str] = None):
        """重置指定模型的限流记录"""
        if client_id:
            key = f"rate_limit:model:{model_name}:client:{client_id}"
        else:
            key = f"rate_limit:model:{model_name}"

        self.redis_client.delete(key)

    def health_check(self) -> bool:
        """检查Redis连接是否正常"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False


# 使用示例
if __name__ == "__main__":
    # 初始化限流器
    limiter = ModelRateLimiter(redis_host="localhost", redis_port=6379)

    # 检查Redis连接
    if not limiter.health_check():
        print("❌ Redis连接失败")
        exit(1)

    print("✅ Redis连接成功")

    # 测试限流
    model = "imagen-3.0-generate-001"

    print(f"\n测试模型: {model}")

    # 第一次调用
    allowed, wait_time = limiter.check_and_update(model)
    print(f"第1次调用: {'✅ 允许' if allowed else '❌ 拒绝'}, 等待时间: {wait_time:.2f}秒")

    # 立即第二次调用
    allowed, wait_time = limiter.check_and_update(model)
    print(f"第2次调用: {'✅ 允许' if allowed else '❌ 拒绝'}, 等待时间: {wait_time:.2f}秒")

    # 等待5秒后再调用
    print(f"\n等待 {wait_time:.2f} 秒...")
    time.sleep(wait_time + 0.1)

    allowed, wait_time = limiter.check_and_update(model)
    print(f"第3次调用: {'✅ 允许' if allowed else '❌ 拒绝'}, 等待时间: {wait_time:.2f}秒")
