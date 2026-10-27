# kindle-to-pdf

Kindle for Mac で開いている本を 1 ページずつ撮影し、PDF にまとめるツール。購入済みの本を個人で使う範囲に限る。
DRM は解除しない。画面に表示されたものを撮影する方式。

> **注意**: 作った PDF を他人に渡したり公開したりしないでください。利用規約と著作権法を守る責任は使う人にあります。動作確認は macOS だけです。

## 準備（初回だけ）

1. システム設定 > プライバシーとセキュリティ で、実行するアプリ（ターミナル等）に次の 2 つを許可する
   - **アクセシビリティ**（ページ送りのキー入力に使う）
   - **画面収録**（撮影に使う）
2. 依存パッケージを入れる

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 使い方

1. Kindle で本を開き、**1 ページ表示・フルスクリーン**にして最初のページを表示する
2. 実行すると 5 秒後から撮影が始まる。同じ画面が 3 回続いたら最終ページとみなして自動で止まる（Ctrl+C でも止められる）

```bash
# 横書きの本（→ で次ページ）。撮影して余白を切り落とし、PDF にする
.venv/bin/python kindle2pdf.py run "本のタイトル" --trim

# 縦書きの本（右開き。← で次ページ）
.venv/bin/python kindle2pdf.py run "本のタイトル" --direction left --trim

# 撮影済みのフォルダから PDF だけ作り直す
.venv/bin/python kindle2pdf.py build ~/Desktop/kindle_pdf/本のタイトル --trim
```

保存先は `~/Desktop/kindle_pdf/<タイトル>/` で、中に `page_0001.png` … と `<タイトル>.pdf` ができる。
撮影済みの画像や PDF がすでにあるときは、上書きせずにエラーで止まる。

| オプション | 既定 | 用途 |
|---|---|---|
| `--direction` | `right` | 次ページへ進むキー |
| `--wait` | `1.5` | ページ送り後に待つ秒数。描画が遅い本やページが飛ぶときは増やす |
| `--region x,y,w,h` | 全画面 | 撮影範囲（ポイント単位） |
| `--max-pages` | `2000` | 撮影ページ数の上限 |
| `--app` | `Amazon Kindle` | Kindle アプリの名前 |

## テスト

```bash
.venv/bin/python -m unittest -v
```

## ライセンス

MIT
