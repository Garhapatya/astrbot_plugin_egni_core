"""PdfGenerator - 将卡组/卡片数据渲染为 A4 PDF，每页 3×3 卡图网格。"""

import os
import tempfile
from typing import Any

from ..ygo.deck_handle import Card, Deck

try:
    from fpdf import FPDF

    _HAS_FPDF = True
except ImportError:
    FPDF = None  # type: ignore[assignment]
    _HAS_FPDF = False


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
    """YGO 卡牌 PDF 生成器。

    依赖 ``fpdf2`` - 执行 ``pip install fpdf2`` 安装。
    """

    PDF_UNIT = "mm"

    @staticmethod
    def mm_to_pt(mm: float) -> float:
        """毫米转印刷磅（1 pt = 1/72 英寸）。"""
        return mm * 72 / 25.4

    @staticmethod
    def _ensure_fpdf() -> None:
        if not _HAS_FPDF:
            raise ImportError("缺少 fpdf2，请执行: pip install fpdf2")

    # ── 底层辅助方法 ──────────────────────────────────────────

    @staticmethod
    def download_card_image(
        code: int,
        cdn_url: str = "https://cdn.233.momobako.com/ygopro/pics/{code}.jpg",
    ) -> bytes:
        """从 CDN 下载单张卡图的 JPEG 字节流。

        Args:
            code: 卡片密码。
            cdn_url: CDN 地址模板，``{code}`` 会被替换为卡片密码。

        Returns:
            原始图片字节 (JPEG)。
        """
        from ..ygo.deck_handle import DeckHandle

        return DeckHandle.fetch_card_image(code, cdn_url)

    @staticmethod
    def _download_page_images(
        cards: list[Card],
        cdn_url: str,
        temp_dir: str,
    ) -> list[str | None]:
        """批量下载一批卡片的卡图到临时文件。

        Returns:
            与输入等长的列表，每项为临时文件路径或 ``None``（下载失败）。
        """
        paths: list[str | None] = []
        for i, card in enumerate(cards):
            try:
                img_bytes = PdfGenerator.download_card_image(card.code, cdn_url)
                tmp = os.path.join(temp_dir, f"{i}.jpg")
                with open(tmp, "wb") as f:
                    f.write(img_bytes)
                paths.append(tmp)
            except Exception:
                paths.append(None)
        return paths

    @staticmethod
    def _draw_card_placeholder(pdf: Any, x: float, y: float, code: int) -> None:
        """当图片缺失时绘制一个灰色占位框。"""
        pdf.set_draw_color(200, 200, 200)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(x, y, CARD_WIDTH_MM, CARD_HEIGHT_MM, style="DF")
        pdf.set_xy(x, y + CARD_HEIGHT_MM / 2 - 3)
        pdf.set_font("Helvetica", size=6)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(CARD_WIDTH_MM, 6, str(code), align="C")

    # ── 高层公开 API ──────────────────────────────────────────

    @staticmethod
    def generate_card_page(
        cards: list[Card],
        output_path: str,
        cdn_url: str = "https://cdn.233.momobako.com/ygopro/pics/{code}.jpg",
    ) -> str:
        """生成单页 A4 PDF，卡图按 3×3 网格排版。

        Args:
            cards: 最多 9 张卡片，超出的条目被静默忽略。
            output_path: PDF 文件保存路径。
            cdn_url: 卡图 CDN 地址模板。

        Returns:
            生成 PDF 的绝对路径。
        """
        PdfGenerator._ensure_fpdf()
        assert FPDF is not None
        page_cards = cards[:CARDS_PER_PAGE]

        pdf = FPDF(unit=PdfGenerator.PDF_UNIT, format="A4")
        temp_dir = tempfile.mkdtemp(prefix="ygopdf_")

        try:
            image_paths = PdfGenerator._download_page_images(
                page_cards, cdn_url, temp_dir
            )
            pdf.add_page()

            for idx, (card, img_path) in enumerate(zip(page_cards, image_paths)):
                row = idx // COLS
                col = idx % COLS
                x = MARGIN_H_MM + col * CARD_WIDTH_MM
                y = MARGIN_V_MM + row * CARD_HEIGHT_MM

                if img_path:
                    pdf.image(img_path, x=x, y=y, w=CARD_WIDTH_MM, h=CARD_HEIGHT_MM)
                else:
                    PdfGenerator._draw_card_placeholder(pdf, x, y, card.code)

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            pdf.output(output_path)
        finally:
            _clean_temp_dir(temp_dir)

        return os.path.abspath(output_path)

    @staticmethod
    def generate_deck_pdf(
        deck: Deck,
        output_path: str,
        cdn_url: str = "https://cdn.233.momobako.com/ygopro/pics/{code}.jpg",
    ) -> bytes:
        """为完整的 **卡组** 生成多页 A4 PDF，每页 9 张卡片。

        卡牌顺序遵循 YDK 惯例：主卡组 → 额外卡组 → 副卡组。

        ``count > 1`` 的卡会重复占位，使每张实体卡都有独立卡位。

        每张卡图为 62 × 89 mm（标准 YGO 卡片尺寸），
        每页居中排布 3 × 3 网格。

        Args:
            deck: 待渲染的卡组。
            output_path: 输出 PDF 文件路径。
            cdn_url: CDN 地址模板，``{code}`` 会被替换为卡片密码。

        Returns:
            PDF 文件字节流。
        """
        PdfGenerator._ensure_fpdf()
        assert FPDF is not None

        # 按 count 展开为平坦列表
        flat: list[Card] = []
        for section in (deck.main_deck, deck.extra_deck, deck.side_deck):
            for card in section:
                flat.extend([card] * card.count)

        pdf = FPDF(unit=PdfGenerator.PDF_UNIT, format="A4")
        temp_dir = tempfile.mkdtemp(prefix="ygopdf_")

        try:
            for page_start in range(0, len(flat), CARDS_PER_PAGE):
                page_cards = flat[page_start : page_start + CARDS_PER_PAGE]
                image_paths = PdfGenerator._download_page_images(
                    page_cards, cdn_url, temp_dir
                )

                pdf.add_page()

                for idx, (card, img_path) in enumerate(zip(page_cards, image_paths)):
                    row = idx // COLS
                    col = idx % COLS
                    x = MARGIN_H_MM + col * CARD_WIDTH_MM
                    y = MARGIN_V_MM + row * CARD_HEIGHT_MM

                    if img_path:
                        pdf.image(
                            img_path,
                            x=x,
                            y=y,
                            w=CARD_WIDTH_MM,
                            h=CARD_HEIGHT_MM,
                        )
                    else:
                        PdfGenerator._draw_card_placeholder(pdf, x, y, card.code)

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            pdf.output(output_path)
            with open(output_path, "rb") as f:
                pdf_bytes = f.read()
        finally:
            _clean_temp_dir(temp_dir)

        return pdf_bytes


def _clean_temp_dir(temp_dir: str) -> None:
    """删除临时目录及其全部内容。"""
    if not os.path.exists(temp_dir):
        return
    for fname in os.listdir(temp_dir):
        fpath = os.path.join(temp_dir, fname)
        try:
            os.remove(fpath)
        except OSError:
            pass
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass
