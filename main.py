from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

import os

@register("egni_core", "Garhapatya", "支持与提供qq机器人Egni-个性化服务的核心插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        template_path = os.path.join(
            os.path.dirname(__file__), "assets", "tcgame", "parchement_ui.j2"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            self.tcgame_template = f.read()


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""


    
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息




    
    async def custom_t2i_tmpl(self, event: AstrMessageEvent):
        options = {} # 可选择传入渲染选项。
        
        url = await self.html_render(self.tcgame_template, {"items": ["吃饭", "睡觉"]}, options=options) # 第二个参数是 Jinja2 的渲染数据
        yield event.image_result(url)