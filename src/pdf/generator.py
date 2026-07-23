"""PdfGenerator - 将卡组/卡片数据渲染为 A4 PDF，每页 3×3 卡图网格。"""

import os
import tempfile
from typing import Any

from ..ygo.util import Card, Deck, DeckHandle


from fpdf import FPDF


# A4 尺寸 (mm)
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

# 标准 YGO 卡片尺寸 (mm)
CARD_WIDTH_MM = 62
CARD_HEIGHT_MM = 89

# 每页网格布局
COLS = 3
ROWS = 3
CARDS_PER_PAGE = COLS * ROWS  # 9

# 自动计算边距，使 3×3 网格在 A4 上居中
MARGIN_H_MM = (A4_WIDTH_MM - COLS * CARD_WIDTH_MM) / 2  # 12 mm
MARGIN_V_MM = (A4_HEIGHT_MM - ROWS * CARD_HEIGHT_MM) / 2  # 15 mm


class PdfGenerator:
    """YGO 打印 PDF 生成器。
    使用实例生命周期管理临时文件。
    """

    PDF_UNIT = "mm"

    def __init__(self, DeckHandle: DeckHandle) -> None:
        self.deck_handle = DeckHandle

        self.pdf = FPDF(unit=self.PDF_UNIT, format="A4")




    # ── 底层辅助方法 ──────────────────────────────────────────

    @staticmethod
    def _draw_card_placeholder(pdf: Any, x: float, y: float, code: str) -> None:
        """当图片缺失时绘制一个灰色占位框。"""
        pdf.set_draw_color(200, 200, 200)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(x, y, CARD_WIDTH_MM, CARD_HEIGHT_MM, style="DF")
        pdf.set_xy(x, y + CARD_HEIGHT_MM / 2 - 3)
        pdf.set_font("Helvetica", size=6)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(CARD_WIDTH_MM, 6, code, align="C")

    # ── 高层公开 API ──────────────────────────────────────────



    def embed_deck(
        self,
        deck: Deck,
    ) -> None:
        """为完整的 **卡组** 生成多页 A4 PDF，每页 9 张卡片。

        卡牌顺序遵循 YDK 惯例：主卡组 → 额外卡组 → 副卡组。

        ``count > 1`` 的卡会重复占位，使每张实体卡都有独立卡位。

        每张卡图为 62 × 89 mm（标准 YGO 卡片尺寸），
        每页居中排布 3 × 3 网格。

        Args:
            deck: 待渲染的卡组。
            output_path: 输出 PDF 文件路径。

        Returns:
            None
        """


        # 按 count 展开为平坦列表
        flat: list[Card] = []
        for section in (deck.main_deck, deck.extra_deck, deck.side_deck):
            for card in section:
                flat.extend([card] * card.count)



        for page_start in range(0, len(flat), CARDS_PER_PAGE):
            page_cards = flat[page_start : page_start + CARDS_PER_PAGE]
            image_paths: list[str | None] = []
            for card in page_cards:
                image_paths.append(self.deck_handle.fetch_card_image_path(card))

            self.pdf.add_page()

            for idx, (card, img_path) in enumerate(zip(page_cards, image_paths)):
                if img_path is not None and not os.path.exists(img_path):
                    img_path = None
                row = idx // COLS
                col = idx % COLS
                x = MARGIN_H_MM + col * CARD_WIDTH_MM
                y = MARGIN_V_MM + row * CARD_HEIGHT_MM

                if img_path:
                    self.pdf.image(
                        img_path,
                        x=x,
                        y=y,
                        w=CARD_WIDTH_MM,
                        h=CARD_HEIGHT_MM,
                    )
                else:
                    PdfGenerator._draw_card_placeholder(self.pdf, x, y, card.code)

    def save_pdf(self, output_path: str) -> bytes:
        """将 PDF 保存到指定路径，并返回字节流。"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        self.pdf.output(output_path)
        with open(output_path, "rb") as f:
            return f.read()
