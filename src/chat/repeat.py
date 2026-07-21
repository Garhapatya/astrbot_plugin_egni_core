import random
from typing import Any


class RepeatHandler:
    """群聊复读逻辑管理器，维护每个群的复读状态。"""

    def __init__(self, config: dict[str, Any]):
        self.memory: dict[str, dict] = {}
        self.config = config

    def is_blocked(self, group_id: str) -> bool:
        """是否因开关关闭或群号在黑名单中而禁止复读。"""
        return (
            not self.config.get("enable", True)
            or group_id in self.config.get("blacklist", [])
        )

    def should_repeat(self, group_id: str, message: Any) -> bool:
        """判断是否应该复读本条消息。如果返回 True，外部应当 yield 复读消息。"""
        state = self.memory.get(group_id)

        # 首次出现或消息变化 → 重置计数
        if state is None or state["previous_message"] != message:
            self.memory[group_id] = {"count": 0, "previous_message": message}
            return False

        # 计数为 -1 表示已复读过，跳过
        if state["count"] == -1:
            return False

        state["count"] += 1
        probability = self.config.get("probability", 0.4)

        if random.random() < state["count"] * probability:
            state["count"] = -1
            return True

        return False
