#!/usr/bin/env python3
"""Kindle for Mac の表示画面を 1 ページずつ撮影し、PDF にまとめる（個人利用・購入済み書籍向け）。

使い方:
  kindle2pdf.py capture <タイトル> [--direction left] [--region x,y,w,h] ...
  kindle2pdf.py build   <撮影フォルダ> [--trim]
  kindle2pdf.py run     <タイトル> [--trim] ...      # capture → build を続けて実行
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PIL import Image

import image_ops
import mac_control

DEFAULT_APP = "Amazon Kindle"
DEFAULT_OUTPUT_ROOT = Path.home() / "Desktop" / "kindle_pdf"
DEFAULT_WAIT_SEC = 1.5
DEFAULT_MAX_PAGES = 2000
DEFAULT_COUNTDOWN_SEC = 5
# 同じ画面がこの回数続いたら最終ページとみなす（描画遅延で 1 回だけ同じになる場合に備える）
END_REPEAT = 3
PAGE_GLOB = "page_*.png"


def parse_region(text: str | None) -> tuple[int, int, int, int] | None:
    if not text:
        return None
    parts = text.split(",")
    if len(parts) != 4 or not all(p.strip().lstrip("-").isdigit() for p in parts):
        raise argparse.ArgumentTypeError("--region は x,y,w,h の整数 4 つで指定してください")
    x, y, w, h = (int(p) for p in parts)
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("--region の幅と高さは正の値にしてください")
    return (x, y, w, h)


def safe_title(title: str) -> str:
    cleaned = "".join("_" if c in '/\\:*?"<>|' else c for c in title).strip()
    if not cleaned:
        raise ValueError("タイトルが空です")
    return cleaned


def page_path(folder: Path, index: int) -> Path:
    return folder / f"page_{index:04d}.png"


def capture_book(args: argparse.Namespace) -> Path:
    folder = args.output_root / safe_title(args.title)
    if folder.exists() and any(folder.glob(PAGE_GLOB)):
        raise FileExistsError(f"撮影済みの画像があります（上書きしません）: {folder}")
    folder.mkdir(parents=True, exist_ok=True)

    mac_control.activate_app(args.app)
    print(f"{args.countdown} 秒後に撮影を始めます。Kindle で最初のページを開いておいてください。")
    time.sleep(args.countdown)

    previous: Image.Image | None = None
    repeats = 0
    saved = 0
    tmp = folder / "capture_tmp.png"  # screencapture はドット始まりの名前に書き込めない
    try:
        while saved < args.max_pages:
            mac_control.capture_screen(tmp, args.region)
            with Image.open(tmp) as shot:
                current = shot.copy()

            if previous is not None and image_ops.is_same_page(previous, current):
                repeats += 1
                if repeats >= END_REPEAT:
                    print("\nページが変化しなくなったため終了します（最終ページ）。")
                    break
            else:
                repeats = 0
                saved += 1
                tmp.replace(page_path(folder, saved))
                previous = current
                print(f"\r撮影済み: {saved} ページ", end="", flush=True)

            mac_control.press_page_key(args.app, args.direction)
            time.sleep(args.wait)
    except KeyboardInterrupt:
        print("\n中断しました。撮影済みの画像は残しています。")
    finally:
        tmp.unlink(missing_ok=True)

    print(f"\n{saved} ページを {folder} に保存しました。")
    return folder


def build_book(folder: Path, trim: bool) -> Path:
    pages = sorted(folder.glob(PAGE_GLOB))
    if not pages:
        raise FileNotFoundError(f"{folder} に {PAGE_GLOB} がありません")
    crop = image_ops.common_crop_box(pages) if trim else None
    output = folder / f"{folder.name}.pdf"
    count = image_ops.build_pdf(pages, output, crop=crop)
    print(f"PDF を作成しました（{count} ページ）: {output}")
    return output


def _add_capture_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("title", help="保存フォルダ名・PDF 名になる本のタイトル")
    p.add_argument("--app", default=DEFAULT_APP, help=f"Kindle アプリ名（既定: {DEFAULT_APP}）")
    p.add_argument(
        "--direction", choices=["right", "left"], default="right",
        help="次ページのキー。横書きは right、縦書き（右開き）は left",
    )
    p.add_argument("--region", type=parse_region, default=None, help="撮影範囲 x,y,w,h（省略時は全画面）")
    p.add_argument("--wait", type=float, default=DEFAULT_WAIT_SEC, help="ページ送り後の待ち秒数")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="撮影ページ数の上限")
    p.add_argument("--countdown", type=int, default=DEFAULT_COUNTDOWN_SEC, help="開始前の待ち秒数")
    p.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="保存先の親フォルダ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    _add_capture_options(sub.add_parser("capture", help="撮影のみ"))
    run = sub.add_parser("run", help="撮影して PDF 化")
    _add_capture_options(run)
    run.add_argument("--trim", action="store_true", help="余白を自動で切り落とす")

    build = sub.add_parser("build", help="撮影済みフォルダから PDF 化")
    build.add_argument("folder", type=Path)
    build.add_argument("--trim", action="store_true", help="余白を自動で切り落とす")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            build_book(args.folder, args.trim)
            return 0
        folder = capture_book(args)
        if args.command == "run":
            build_book(folder, args.trim)
        return 0
    except (mac_control.MacControlError, FileExistsError, FileNotFoundError, ValueError) as err:
        print(f"エラー: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
