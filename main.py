from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger
from typing import Any



from .src.chat.repeat import RepeatHandler


@register("egni_core", "Garhapatya", "支持与提供qq机器人Egni-个性化服务的核心插件", "1.0.0")
class EgniCore(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config: Any = config
        self.repeat_handler = RepeatHandler(self.config.repeat)


    async def initialize(self):
        self.repeat_blacklist = await self.get_kv_data("repeat_blacklist", [])


    async def terminate(self):
        pass


    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def repeat(self, event: AstrMessageEvent):
        """自动跟风复读群友消息"""
        if self.repeat_handler.is_blocked(event.get_group_id()):
            return

        message = event.get_messages()
        if self.repeat_handler.should_repeat(event.get_group_id(), message):
            yield event.chain_result(message)
 


            
        



