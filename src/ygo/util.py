import asyncio
import base64
import json
import os
from urllib import parse,request
import zipfile
from dataclasses import dataclass
from typing import Callable


@dataclass
class Card:
    """一张卡的数据。"""

    def __init__(self, code: str, count: int = 1, path: str = ""):
        self.code = code
        self.count = count
        self.image = path

    def __repr__(self) -> str:
        return f"Card(code={self.code}, count={self.count})"

    
    def image_is_url(self,) -> bool:
        """判断卡图路径是否为 URL。"""
        try:
            return parse.urlsplit(self.image).scheme.lower() == "file"
        except ValueError:
            return False

@dataclass
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



class PriorityGet:
    """超先行 YPK 包管理。

    读取 ``{data_path}/priority.json``，其中：
    - ``yrp_ver``: 最近一次下载的超先行 YPK 版本号。
    - ``cards``: 需要优先更新的卡片 code 列表。

    Args:
        data_path: AstrBot 数据目录路径。
        temp_path: 临时文件目录路径。
    """

    def __init__(self, data_path: str, temp_path: str) -> None:
        self.work_dir = data_path.strip("/") + "/priority"
        self.temp_path = temp_path
        self.version: str = ""
        self.cards: list[str] = []

        config_path = data_path.strip("/") + "/priority.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.version = raw.get("yrp_ver", "")
                self.cards = raw.get("cards", [])
            except (json.JSONDecodeError, OSError):
                pass
            
    def get_image(self, code: str) -> str | None:
        """获取超先行 YPK 中的卡图路径。
        """
        if code not in self.cards:
            return None
        img_path = os.path.join(self.work_dir, f"pics/{code}.jpg")
        if os.path.exists(img_path):
            return img_path
        else:
            return None
    
    def fetch_superpre_ypk_url(self) -> str | None:
        """获取最新 MC 超先行 YPK 补丁下载地址。"""
        url = (
            "https://cdntx.moecube.com/ygopro-super-pre/data/latest-tag.txt"
        )
        req = request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        try:
            resp = request.urlopen(req, timeout=10)
            text = resp.read().decode("utf-8").strip()
            if text.endswith(".ypk"):
                return text
            return None
        except Exception:
            return None

    def ver_check(self) -> tuple[str, str] | None:
        """
        检查本地 YPK 版本是否过期。
        """
        url = self.fetch_superpre_ypk_url()
        if not url:
            return None
        
        latest_ver = url.split("/")[-1].replace(".ypk", "")

        if latest_ver != self.version:
            return url, latest_ver 
        else:
            return None

    async def download(self, url: str) -> str | None:
        """下载 YPK 文件到本地。
        """
        os.makedirs(self.temp_path, exist_ok=True)
        fname = url.split("/")[-1]
        save_path = os.path.join(self.temp_path, fname)
        try:
            def _download() -> str:
                req = request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                            " AppleWebKit/537.36"
                        )
                    },
                )
                resp = request.urlopen(req, timeout=300)
                with open(save_path, "wb") as f:
                    f.write(resp.read())
                return save_path

            return await asyncio.to_thread(_download)
        except Exception:
            return None

    async def update_priority(self, is_force: bool = False) -> str | None:
        """更新超先行。"""
        if not is_force:
            result = self.ver_check()
            if result is None:
                return  # 已是最新版本，无需更新
            latest_url, latest_ver = result
        else:
            latest_url = self.fetch_superpre_ypk_url()
            if latest_url is None:
                return  # 无法获取最新 YPK 地址
            latest_ver = latest_url.split("/")[-1].replace(".ypk", "") 

        # 清理工作目录
        os.makedirs(self.work_dir, exist_ok=True)
        for file in os.listdir(self.work_dir):
            file_path = os.path.join(self.work_dir, file)
            try:
                os.remove(file_path)
            except OSError:
                pass

        # 下载最新 YPK
        ypk_path = await self.download(latest_url)
        if not ypk_path:
            return  # 下载失败
        
        # 解压 YPK 文件
        new_cards = []
        try:
            with zipfile.ZipFile(ypk_path, "r") as yrp:
                for file in yrp.namelist():
                    if file.startswith("pics/") and file.endswith(".jpg") and file.count("/") == 1:
                        yrp.extract(file, self.work_dir)
                        code = file.split("/")[1].replace(".jpg", "")
                        new_cards.append(code)

        except Exception:
            return  # 解压失败

        # 更新记录
        try:
            with open(os.path.join(self.work_dir, "priority.json"), "w", encoding="utf-8") as f:
                json.dump({"yrp_ver": latest_ver, "cards": new_cards}, f, ensure_ascii=False, indent=4)
        except Exception:
            pass # 写入失败
        self.version = latest_ver
        self.cards = new_cards
        return latest_ver

    

class DeckHandle:
    """
    卡组编解码器与数据获取。
    """


    def __init__(
        self,
        config: dict,
        data_path: str,
        temp_path: str,
    ) -> None: 
        def url_template(template: str) -> Callable[[str], str]:
            """把含 {code} 的 URL 模板变成可调用对象。"""
            def _build(code: str) -> str:
                if "{code}" in template:
                    return template.replace("{code}", code)
                return template.rstrip("/") + "/" + code
            return _build

        self.cdn_url: Callable[[str], str] = url_template(config.get("CDNurl", ""))
        self.card_info_url: Callable[[str], str] = url_template(config.get("CardInfoUrl", ""))

        self.search_url: str = config.get("SearchUrl", "")
        self.data_path = data_path
        self.temp_path = temp_path

        self.priority = PriorityGet(self.data_path, self.temp_path)

    def get_image_path(self, code: str) -> str:
        """获取卡图路径，优先使用超先行 YPK 中的图片。"""
        img_path = self.priority.get_image(code)
        if img_path is None:
            img_path = self.cdn_url(code)
        return img_path


    def from_ourygo_url(self, url: str) -> Deck:
        """
        从 ourygo 分享 URL 解码出卡组。
        """
        parsed = parse.urlparse(url)
        params = parse.parse_qs(parsed.query)

        name = parse.unquote(params.get("name", [""])[0])
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
                card_code = str(int(card_bits[2:29], 2))
                decks[key].append(Card(card_code, card_count, self.get_image_path(card_code)))
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

    def fetch_card_image_bytes(self, url: str) -> bytes:
        """从 CDN 下载卡图 jpg 字节流。

        Args:
            code: 卡片 passcode。

        Returns:
            JPEG 图片的原始字节。
        """

        req = request.Request(
            url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
        )
        resp = request.urlopen(req, timeout=15)
        return resp.read()

    def fetch_card_image_path(self, card: Card, dl_path: str | None = None) -> str:
        """从 CDN 下载卡图到本地。

        Args:
            code: 卡片 passcode。

        Returns:
            本地卡图文件的路径。
        """
        if not card.image_is_url():
            return card.image
            
        if dl_path is None:
            image_path = self.temp_path
        else:
            image_path = dl_path
        img_bytes = self.fetch_card_image_bytes(card.image)
        os.makedirs(image_path, exist_ok=True)
        tmp = os.path.join(image_path, card.code + ".jpg")
        if not os.path.exists(tmp) or dl_path:
            with open(tmp, "wb") as f:
                f.write(img_bytes)
        return tmp

    def fetch_card_name(self, code: str) -> str:
        """通过百鸽 API 查询卡片的中文名称。

        Args:
            code: 卡片 passcode。

        Returns:
            中文卡片名称，API 不可用时返回 'Unknown Card ({code})'。
        """
        try:
            url = self.card_info_url(code)
            req = request.Request(
                url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
            )
            resp = request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            return data["text"]["name"]
        except Exception:
            return f"Unknown Card ({code})"

    def fetch_card_info(self, code: str) -> dict | None:
        """通过百鸽 API 查询卡片的完整信息。

        Args:
            code: 卡片 passcode。

        Returns:
            包含 id, cid, text (含 name/types/desc), data (含 atk/def/level 等)
            的 dict，API 不可用时返回 None。
        """
        try:
            url = self.card_info_url(code)
            req = request.Request(
                url, headers={"User-Agent": "AstrBot-EgniCore/1.0"}
            )
            resp = request.urlopen(req, timeout=15)
            return json.loads(resp.read())
        except Exception:
            return None

    def search_cards(self, query: str, start: int = 0) -> list[dict]:
        """通过百鸽 API 搜索卡片。

        Args:
            query: 搜索关键词（卡名、效果文本、密码、cid 等）。
            start: 结果偏移量，用于分页，默认 0。

        Returns:
            搜索结果列表，每项包含 id, cid, cn_name, text, data 等字段，
            API 不可用时返回空列表。
        """
        try:
            url = self.search_url.rstrip("/") + "/"
            params = parse.urlencode({"search": query, "start": start})
            req = request.Request(
                url + "?" + params,
                headers={"User-Agent": "AstrBot-EgniCore/1.0"},
            )
            resp = request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            return data.get("result", [])
        except Exception:
            return []


