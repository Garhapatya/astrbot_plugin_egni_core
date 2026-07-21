from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger

import os
import random
from typing import Any


@register("egni_core", "Garhapatya", "支持与提供qq机器人Egni-个性化服务的核心插件", "1.0.0")
class EgniCore(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config: Any = config



    async def initialize(self):
        self.repeat_blacklist = await self.get_kv_data("repeat_blacklist", []) 


    async def terminate(self):
        pass


    repeat_memory = {}
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def repeat(self, event: AstrMessageEvent):
        """自动跟风复读群友消息"""

        if not self.config.repeat.get("enable") or event.get_group_id() in self.config.repeat.get("blacklist", []):
            return

        message = event.get_messages()
        group_id = event.get_group_id()

        if (
            group_id not in self.repeat_memory
            or self.repeat_memory[group_id]["previous_message"] != message
        ):
            self.repeat_memory[group_id] = {"count": 0, "previous_message": message}
        elif self.repeat_memory[group_id]["count"] == -1:
            pass
        else:
            self.repeat_memory[group_id]["count"] += 1

        if random.random() < self.repeat_memory[group_id]["count"] * self.config.repeat.get("probability", 0.4):
            yield event.chain_result(message)
            self.repeat_memory[group_id]["count"] = -1
 


            
        



