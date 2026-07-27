from pydantic import Field
from pydantic.dataclasses import dataclass
from typing import Any
import json
from mcp.types import TextContent, CallToolResult

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class card_search(FunctionTool[AstrAgentContext]):
    name: str = "card_search"  # 工具名称
    description: str = "一个提供游戏王卡片搜索并输出卡片详细信息的工具，输出结果包含一个json格式的字符串提供本页搜索结果，和一个标识下一页起始位置的数字"  # 工具描述
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索卡片的关键词，需要符合基本的精确搜索逻辑。\n内容可以是卡名、卡密、卡片种类、卡片种族/属性/等级/攻/守，卡片效果等。\n关键词用于填入apiurl，不能出现违法URL语法的字符",
                },
                "start": {
                    "type": "integer",
                    "description": "搜索结果的起始位置，0则表示表示从第一页开始，通过填入上一次调用此工具得到的输出中标识下一页起始位置的数字来获取下一页",
                },
            },
            "required": ["keywords", "start"],
        }
    )
    deck_handle: Any = None
    
    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        info: list[dict]
        next: int
        info, next = self.deck_handle.search_card(query=kwargs.get("keywords", ""), start=kwargs.get("start", 0))
        infos = json.dumps(info, ensure_ascii=False, indent=0)
        return CallToolResult(content=[
            TextContent(type="text", text=f"本页查卡结果： {infos}"),
            TextContent(type="text", text=f"下一页查卡起始位置(输出0则无下页)： {next}"),
        ])