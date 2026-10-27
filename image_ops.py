"""撮影済みページ画像の比較・余白トリミング・PDF 結合（macOS に依存しない純粋な処理）。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageChops

# 画素差がこの値以下なら「同じ色」とみなす（アンチエイリアスの揺れ対策）
PIXEL_TOLERANCE = 16
# 差分画素の割合がこれ未満なら「同じページ」とみなす（カーソル等の小さな変化を無視）
SAME_PAGE_RATIO = 0.001
DEFAULT_TRIM_PADDING = 12

BBox = tuple[int, int, int, int]


def _diff_mask(a: Image.Image, b: Image.Image) -> Image.Image:
    diff = ImageChops.difference(a.convert("L"), b.convert("L"))
    return diff.point(lambda v: 255 if v > PIXEL_TOLERANCE else 0)


def is_same_page(a: Image.Image, b: Image.Image, ratio: float = SAME_PAGE_RATIO) -> bool:
    """2 枚のスクリーンショットが実質同じページかを判定する。"""
    if a.size != b.size:
        return False
    changed = _diff_mask(a, b).histogram()[255]
    return changed / (a.width * a.height) < ratio


def content_bbox(img: Image.Image) -> BBox | None:
    """左上隅の色を背景とみなし、それ以外の画素を囲む矩形を返す。全面背景なら None。"""
    rgb = img.convert("RGB")
    background = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
    return _diff_mask(rgb, background).getbbox()


def union_bbox(boxes: Iterable[BBox | None]) -> BBox | None:
    valid = [b for b in boxes if b is not None]
    if not valid:
        return None
    return (
        min(b[0] for b in valid),
        min(b[1] for b in valid),
        max(b[2] for b in valid),
        max(b[3] for b in valid),
    )


def pad_bbox(box: BBox, padding: int, size: tuple[int, int]) -> BBox:
    width, height = size
    return (
        max(box[0] - padding, 0),
        max(box[1] - padding, 0),
        min(box[2] + padding, width),
        min(box[3] + padding, height),
    )


def common_crop_box(paths: Sequence[Path], padding: int = DEFAULT_TRIM_PADDING) -> BBox | None:
    """全ページ共通の本文領域を求める（ページごとに大きさが揺れないよう和集合をとる）。"""
    boxes: list[BBox | None] = []
    size = (0, 0)
    for path in paths:
        with Image.open(path) as img:
            size = img.size
            boxes.append(content_bbox(img))
    merged = union_bbox(boxes)
    return pad_bbox(merged, padding, size) if merged else None


def build_pdf(
    paths: Sequence[Path],
    output: Path,
    crop: BBox | None = None,
    dpi: int = 144,
    quality: int = 90,
) -> int:
    """画像群を 1 つの PDF にまとめ、ページ数を返す。既存ファイルは上書きしない。"""
    if not paths:
        raise ValueError("PDF にする画像がありません")
    if output.exists():
        raise FileExistsError(f"出力先が既に存在します（上書きしません）: {output}")

    pages = [_load_page(p, crop) for p in paths]
    pages[0].save(
        output, "PDF", save_all=True, append_images=pages[1:], resolution=dpi, quality=quality
    )
    return len(pages)


def _load_page(path: Path, crop: BBox | None) -> Image.Image:
    with Image.open(path) as img:
        page = img.convert("RGB")
    return page.crop(crop) if crop else page
