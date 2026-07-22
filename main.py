from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
import astrbot.api.message_components as Comp
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger
from typing import Any

from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path,get_astrbot_temp_path
import traceback

from .src.chat import RepeatHandler
from .src.ygo import *
from .src.pdf import PdfGenerator

@register("egni_core", "Garhapatya", "支持与提供qq机器人Egni-个性化服务的核心插件", "1.0.0")
class EgniCore(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config: Any = config
        self.repeat_handler = RepeatHandler(self.config.repeat)
        self.plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name

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


    @filter.command_group("repeat")
    @filter.permission_type(filter.PermissionType.ADMIN)
    def repeat_command():
        pass

    @repeat_command.group("blacklist")
    def blacklist_command():
        pass

    @blacklist_command.command("add")
    async def add_blacklist(self, event: AstrMessageEvent):
        """将当前群添加到复读黑名单"""
        group_id = event.get_group_id()
        if self.repeat_handler.add_blacklist(group_id):
            self.config.save_config()
            yield event.plain_result(f"已将群 {group_id} 添加到复读黑名单。")
        else:
            yield event.plain_result(f"群 {group_id} 已在复读黑名单中。")

    @blacklist_command.command("rm")
    async def remove_blacklist(self, event: AstrMessageEvent):
        """从复读黑名单中移除当前群"""
        group_id = event.get_group_id()
        if self.repeat_handler.remove_blacklist(group_id):
            self.config.save_config()
            yield event.plain_result(f"已将群 {group_id} 从复读黑名单中移除。")
        else:
            yield event.plain_result(f"群 {group_id} 不在复读黑名单中。")


    @filter.command("prdeck", alias={"打印卡组"})
    async def print_deck(self, event: AstrMessageEvent, url: str):
        """从 ourygo 分享 URL 生成卡组 PDF"""

        logger.info(f"print_deck: decoding deck URL: {url}")
        deck = DeckHandle.from_ourygo_url(url)

        logger.info(f"print_deck: decoded deck '{deck.name}' — "
                     f"main {len(deck.main_deck)} / extra {len(deck.extra_deck)} / side {len(deck.side_deck)} cards")
        yield event.plain_result("生成中…")

        output_path = get_astrbot_temp_path() 
        cdn = self.config.ygo.get("cdn_url", "https://cdn.233.momobako.com/ygopro/pics/{code}.jpg")

        logger.info(f"print_deck: generating PDF -> {output_path}")
        try:
            pdf_bytes = PdfGenerator.generate_deck_pdf(deck, output_path + f"/{deck.name}.pdf", cdn)
        except Exception as e:
            logger.error(f"print_deck: PDF generation failed: {e}\n{traceback.format_exc()}")
            yield event.plain_result("生成 PDF 失败，请检查日志。")
            return

        logger.info(f"print_deck: PDF generated successfully, {deck.total_cards} cards, sending...")

        yield event.send(MessageEventResult([Comp.File(file=output_path, name=f"{deck.name}.pdf")]))
        logger.info(f"print_deck: PDF sent successfully, cleaning up...")
        