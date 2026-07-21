import base64
import json
import urllib.parse
import urllib.request


class Card:
    """一张卡的数据。"""

    def __init__(self, code: int, count: int = 1, image_url: str = ""):
        self.code = code
        self.count = count
        self.image_url = image_url

    def __repr__(self) -> str:
        return f"Card(code={self.code}, count={self.count})"


class Deck:
    """一个完整卡组的数据，包含主卡组、额外卡组、副卡组和牌组名。"""

    def __init__(
        self,
        name: str = "",
        main_deck: list[Card] | None = None,
        extra_deck: list[Card] | None = None,
        side_deck: list[Card] | None = None,
    ):
        self.name = name
        self.main_deck = main_deck or []
        self.extra_deck = extra_deck or []
        self.side_deck = side_deck or []

    @property
    def total_cards(self) -> int:
        """实际卡牌总数（含复数张）。"""
        return (
            sum(c.count for c in self.main_deck)
            + sum(c.count for c in self.extra_deck)
            + sum(c.count for c in self.side_deck)
        )

    def __repr__(self) -> str:
        return (
            f"Deck(name={self.name!r}, main={len(self.main_deck)} positions"
            f" ({sum(c.count for c in self.main_deck)} cards), "
            f"extra={len(self.extra_deck)} positions, "
            f"side={len(self.side_deck)} positions)"
        )


class DeckHandle:
    """卡组编解码器。"""

    @staticmethod
    def from_ourygo_url(url: str) -> Deck:
        """从 ourygo 分享 URL 解码出卡组。

        Args:
            url: 形如 http://deck.ourygo.top?name=...&v=1&d={data} 的网址。

        Returns:
            Deck 对象。
        """
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        name = urllib.parse.unquote(params.get("name", [""])[0])
        d_param = params.get("d", [""])[0]
        if not d_param:
            raise ValueError("URL 中缺少 d 参数 (卡组数据)。")

        # URL-safe base64 → 标准 base64
        d = d_param.replace("-", "+").replace("_", "/")
        pad = 4 - len(d) % 4
        if pad != 4:
            d += "=" * pad

        raw = base64.b64decode(d)
        bits = "".join(f"{b:08b}" for b in raw)

        # 解析头部
        main_count = int(bits[0:8], 2)
        extra_count = int(bits[8:12], 2)
        side_count = int(bits[12:16], 2)

        # 解析每张卡 (29 bit = 2 count + 27 code)
        pos = 16
        decks: dict[str, list[Card]] = {"main": [], "extra": [], "side": []}
        for key, cnt in [
            ("main", main_count),
            ("extra", extra_count),
            ("side", side_count),
        ]:
            for _ in range(cnt):
                card_bits = bits[pos : pos + 29]
                card_count = int(card_bits[0:2], 2)
                card_code = int(card_bits[2:29], 2)
                decks[key].append(Card(card_code, card_count))
                pos += 29

        return Deck(
            name=name,
            main_deck=decks["main"],
            extra_deck=decks["extra"],
            side_deck=decks["side"],
        )

    @staticmethod
    def to_ydk(deck: Deck) -> str:
        """将卡组导出为 ydk 格式文本。

        Args:
            deck: Deck 对象。

        Returns:
            ydk 格式字符串，可直接保存为 .ydk 文件。
        """
        lines = ["#created by AstrBot Egni Core", "#main"]
        for card in deck.main_deck:
            for _ in range(card.count):
                lines.append(str(card.code))
        lines.append("#extra")
        for card in deck.extra_deck:
            for _ in range(card.count):
                lines.append(str(card.code))
        lines.append("!side")
        for card in deck.side_deck:
            for _ in range(card.count):
                lines.append(str(card.code))
        return "\n".join(lines)

    @staticmethod
    def _build_url(template: str, code: int) -> str:
        """将 {code} 占位符替换为实际卡密，无占位符时追加在末尾。"""
        placeholder = "{code}"
        if placeholder in template:
            return template.replace(placeholder, str(code))
        return template.rstrip("/") + "/" + str(code)

    @staticmethod
    def fetch_card_image(
        code: int,
        cdn_url: str = "https://cdn.233.momobako.com/ygopro/pics/{code}.jpg",
    ) -> bytes:
        """从 CDN 下载卡图 jpg 字节流。

        Args:
            code: 卡片 passcode。
            cdn_url: 卡图 CDN 地址模板，使用 {code} 作为卡密占位符。

        Returns:
            JPEG 图片的原始字节。
        """
        url = DeckHandle._build_url(cdn_url, code)
        req = urllib.request.Request(
            url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read()

    @staticmethod
    def fetch_card_name(
        code: int,
        api_url: str = "https://ygocdb.com/api/v0/card/{code}",
    ) -> str:
        """通过百鸽 API 查询卡片的中文名称。

        Args:
            code: 卡片 passcode。
            api_url: 百鸽 API 地址模板，默认使用 {code} 占位符。

        Returns:
            中文卡片名称，API 不可用时返回 'Unknown Card ({code})'。
        """
        try:
            url = DeckHandle._build_url(api_url, code)
            req = urllib.request.Request(
                url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            return data["text"]["name"]
        except Exception:
            return f"Unknown Card ({code})"

    @staticmethod
    def fetch_card_info(
        code: int,
        api_url: str = "https://ygocdb.com/api/v0/card/{code}",
    ) -> dict | None:
        """通过百鸽 API 查询卡片的完整信息。

        Args:
            code: 卡片 passcode。
            api_url: 百鸽 API 地址模板。

        Returns:
            包含 id, cid, text (含 name/types/desc), data (含 atk/def/level 等)
            的 dict，API 不可用时返回 None。
        """
        try:
            url = DeckHandle._build_url(api_url, code)
            req = urllib.request.Request(
                url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
            )
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception:
            return None

    @staticmethod
    def search_cards(
        query: str,
        start: int = 0,
        api_url: str = "https://ygocdb.com/api/v0/",
    ) -> list[dict]:
        """通过百鸽 API 搜索卡片。

        Args:
            query: 搜索关键词（卡名、效果文本、密码、cid 等）。
            start: 结果偏移量，用于分页，默认 0。
            api_url: 百鸽搜索 API 地址。

        Returns:
            搜索结果列表，每项包含 id, cid, cn_name, text, data 等字段，
            API 不可用时返回空列表。
        """
        try:
            url = api_url.rstrip("/") + "/"
            params = urllib.parse.urlencode({"search": query, "start": start})
            req = urllib.request.Request(
                url + "?" + params,
                headers={"User-Agent": "AstrBot-EgniCore/1.0"},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            return data.get("result", [])
        except Exception:
            return []
