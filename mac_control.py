"""macOS 側の操作：Kindle アプリの前面化、ページ送りキー送信、画面撮影。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# AppleScript の key code（物理キー番号）
KEY_CODES = {"right": 124, "left": 123}


class MacControlError(RuntimeError):
    pass


def _run(cmd: list[str], hint: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise MacControlError(f"{hint}\n  command: {' '.join(cmd)}\n  stderr: {result.stderr.strip()}")
    return result.stderr.strip()


def activate_app(app_name: str) -> None:
    _run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        f"アプリ「{app_name}」を前面にできません。--app で名前を確認してください。",
    )


def press_page_key(app_name: str, direction: str) -> None:
    """Kindle を前面にしたうえで矢印キーを 1 回送る。"""
    script = (
        f'tell application "{app_name}" to activate\n'
        f'tell application "System Events" to key code {KEY_CODES[direction]}'
    )
    _run(
        ["osascript", "-e", script],
        "キー送信に失敗しました。システム設定 > プライバシーとセキュリティ > "
        "アクセシビリティ で、実行しているアプリ（ターミナル等）を許可してください。",
    )


def capture_screen(path: Path, region: tuple[int, int, int, int] | None = None) -> None:
    """screencapture で撮影する。region は (x, y, w, h)、単位はポイント（Retina でも論理座標）。"""
    cmd = ["screencapture", "-x", "-t", "png"]
    if region:
        cmd += ["-R", ",".join(str(v) for v in region)]
    cmd.append(str(path))
    stderr = _run(
        cmd,
        "撮影に失敗しました。システム設定 > プライバシーとセキュリティ > 画面収録 で、"
        "ターミナル等を許可してください。",
    )
    if not path.exists() or path.stat().st_size == 0:
        host = os.environ.get("TERM_PROGRAM", "不明")
        # screencapture は書き込めなくても終了コード 0 を返すことがあるため stderr も出す
        raise MacControlError(
            "撮影ファイルができませんでした。\n"
            f"  screencapture の出力: {stderr or '(なし)'}\n"
            f"  実行中のアプリ（TERM_PROGRAM）: {host}\n"
            "  出力が空なら、このアプリに画面収録を許可し ⌘Q で再起動してください。"
        )
