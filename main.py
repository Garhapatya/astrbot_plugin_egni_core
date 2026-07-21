from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger

import os
import random
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PluginConfig:
    @dataclass
    class Repeat:
        enable: bool = True
        probability: float = 0.4
        blacklist: list[Any] = field(default_factory=list)

        def __post_init__(self):
            if not (0 <= self.probability <= 1):
                self.probability = 0.4
        

    repeat: Repeat = field(default_factory=Repeat)


@register("egni_core", "Garhapatya", "支持与提供qq机器人Egni-个性化服务的核心插件", "1.0.0")
class EgniCore(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.setting = PluginConfig(
            repeat=PluginConfig.Repeat(**self.config.get("repeat", {})),
        )



    async def initialize(self):
        self.repeat_blacklist = await self.get_kv_data("repeat_blacklist", []) 


    async def save_config(self):
        self.config.update(asdict(self.setting))
        await self.config.save_config_async()


    async def terminate(self):
        await self.save_config()



    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def repeat(self, event: AstrMessageEvent):
        """自动跟风复读群友消息"""

        if not self.setting.repeat.enable or event.get_group_id() in self.setting.repeat.blacklist: return    

        previous_message = None
        count = 0
        while True:
            message = event.get_message_outline()
            if "[转发消息]" in message or previous_message != message:
                count = 0
                previous_message = message
            elif count == -1: 
                pass
            else:
                count += 1
            
                
            
            if random.random() < count * self.setting.repeat.probability:
                event.get_messages()
                yield
                count = -1  

            if not self.setting.repeat.enable or event.get_group_id() in self.setting.repeat.blacklist: return  


            
        



