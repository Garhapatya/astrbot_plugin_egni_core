from pydantic import Field
from pydantic.dataclasses import dataclass
from typing import Any
import json

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class card_search(FunctionTool[AstrAgentContext]):
    name: str = "card_search"
    description: str = "搜索游戏王卡片，返回卡片信息（自动翻页聚合），效果字段只保留前100个字符，灵摆效果字段只保留前100个字符"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索关键词：卡名/卡密/效果等",
                },
            },
            "required": ["keywords"],
        }
    )
    deck_handle: Any = None

    def filter(self, info:list[dict[str, Any]]) -> list[dict[str, Any]]:
        """过滤掉不必要的字段"""
        filtered_info = []
        for card in info:
            filtered_card = {
                "卡密": card.get("id"),
                "卡名": card.get("cn_name"),
                "官方翻译": card.get("sc_name"),
                "大师决斗翻译": card.get("md_name"),
                "NW翻译": card.get("nwbbs_n"),
                "CNOCG翻译": card.get("cnocg_n"),
                "日文读音": card.get("jp_ruby"),
                "日文名": card.get("jp_name"),
                "英文名": card.get("en_name"),
                "卡片类型": card.get("text", {}).get("types"),
                "灵摆效果": card.get("text", {}).get("pdesc", "")[:100],
                "效果": card.get("text", {}).get("desc", "")[:100],
                "关联卡片": card.get("html", {}).get("refer"),
            }
            filtered_info.append(filtered_card)
        return filtered_info

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        query = kwargs.get("keywords", "")
        all_cards: list[dict] = []
        start = 0
        max_pages = 3

        for _ in range(max_pages):
            page, next_start = self.deck_handle.search_cards(
                query=query, start=start
            )
            all_cards.extend(page)
            if not next_start:
                break
            start = next_start

        all_cards = self.filter(all_cards)
        return json.dumps(all_cards, ensure_ascii=False, separators=(",", ":"))
    





@dataclass
class card_desc(FunctionTool[AstrAgentContext]):
    name: str = "card_desc"
    description: str = "检索固定卡密（卡片id）所对应卡的完整效果"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "code": {
                    "type": "integer",
                    "description": "卡片卡密(id), 例如：10000000",
                },
            },
            "required": ["code"],
        }
    )
    deck_handle: Any = None

    def filter(self, info:dict[str, Any]) -> dict[str, Any]:
        """过滤掉不必要的字段"""

        filtered_info = {
            "卡密": info.get("id"),
            "卡名": info.get("cn_name"),

            "灵摆效果": info.get("text", {}).get("pdesc", ""),
            "效果": info.get("text", {}).get("desc", ""),
        }

        return filtered_info

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        code = kwargs.get("code", "0")


        info = self.deck_handle.fetch_card_info(
                code=code
            )


        info = self.filter(info)
        return json.dumps(info, ensure_ascii=False, separators=(",", ":"))