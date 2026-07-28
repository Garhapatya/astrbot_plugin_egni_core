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
    description: str = "游戏王卡片查询，返回卡片信息（自动翻页聚合）"
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索匹配关键词：使用卡名/卡密/效果/面板，每次查询只能传入一词，不能混合，不能空格分割",
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
                "灵摆效果": card.get("text", {}).get("pdesc"),
                "效果": card.get("text", {}).get("desc"),
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
    
