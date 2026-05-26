[中文](./README_zh.md) | 日本語 | [English](./README.md)

<div align="center">

# LEA — Lab Experiment Assistant

**物理・化学実験の全工程をカバーするデスクトップ GUI ツール**

プロジェクト初期化 → データ分析 → 可視化 → フォーマット変換 → クリーンアップ

</div>

> [!NOTE]
> `user_data/` ディレクトリは gitignore されており、Git で追跡されません。
> 必要に応じて手動で作成し、ユーザーデータファイルを配置してください。

## 機能

### Project — ワンクリック足場生成
テンプレート（Default / Scientific / Custom）から標準的な実験ディレクトリ構造を作成。
`.gitignore` の生成や git リポジトリの初期化もオプションで可能。

### Data — CSV 分析と可視化 **[コア]**
- エンコード・区切り文字・ヘッダー行を設定して CSV を読み込み
- テーブルビューでプレビュー
- matplotlib 埋め込みによる **散布図** と **ヒストグラム**
- `scipy.optimize.curve_fit` による **線形フィット**（不確かさと R² 付き）
- フィット結果を LaTeX 数式としてコピー / PNG としてエクスポート

### Convertor — Beamer PDF → PPTX
- 各ページを調整可能な DPI（100–400）でレンダリングし、フルスライド PNG として `.pptx` に埋め込み
- **PDF ページエディタ**: ページ範囲指定で削除・抽出・分割（`1,3,5-8,10-`）

### Cache Cleaner
- LaTeX: 出力 PDF と補助ファイル（`.aux`, `.log`, `.toc`, `.out` など）を削除
- Python: `__pycache__/`、`*.pyc`、`*.pyo` を再帰的に削除

### Settings
- **リアルタイム言語切替** — 中文 / English / 日本語（181 翻訳キー）
- フォントファミリー・サイズ、デフォルト DPI / 出力形式、テンプレート用学籍番号

## インストール

```bash
# クローン
git clone https://github.com/Didi-Huang/lea.git
cd lea

# 仮想環境作成と依存関係インストール
python3 -m venv .venv && source .venv/bin/activate
pip install PySide6 pymupdf python-pptx pandas matplotlib scipy numpy
```

## 使い方

```bash
python main.py
```

1. **Project** タブ — 実験名を入力 → 親フォルダとテンプレートを選択 → "作成"
2. **Data** タブ — CSV を参照 → "読み込み" → X/Y 列を選択 → "散布図" / "ヒストグラム" / "線形フィット"
3. **Convertor** タブ — ソース PDF、出力先、DPI を選択 → "変換"
4. **Cache Cleaner** — LaTeX または Python の "自動クリア" をクリック
5. **Settings** — 言語切替、設定保存

## プロジェクト構造

```
lea/
├── main.py                  # PySide6 GUI エントリポイント
├── src/
│   ├── convertor.py         # Beamer PDF → PPTX 変換
│   ├── pdf_editor.py        # PDF ページ削除・抽出・分割
│   └── project_builder.py   # 実験ディレクトリ生成
├── ui/
│   └── main_window.ui       # Qt Designer UI レイアウト
├── locales/
│   ├── en.json / zh_CN.json / ja.json   # i18n（各 181 キー）
├── templates/
│   ├── structures/          # プロジェクトテンプレート (JSON)
│   ├── gitignore/           # .gitignore テンプレート
│   └── readme/              # README テンプレート
├── fonts/                   # HarmonyOS Sans フォント
└── user_data/               # ユーザー設定・履歴・カスタムテンプレート (gitignored)
```

## 依存関係

| パッケージ | 用途 |
|-----------|------|
| PySide6 | GUI フレームワーク |
| PyMuPDF (`fitz`) | PDF レンダリング・ページ操作 |
| python-pptx | PPTX 生成 |
| pandas | CSV データ読み込み |
| matplotlib | グラフ描画（散布図・ヒストグラム・フィット） |
| scipy | カーブフィッティング |
| numpy | 数値配列 |

## ライセンス

MIT
