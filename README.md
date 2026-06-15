# markdown-viewer

Windows 向けの軽量 Markdown ビューア。`.md` ファイルをダブルクリックすると、色分けされた見やすい HTML としてブラウザに表示する。サイドバーでフォルダ内のファイルを切り替えたり、その場で編集したりできる。

外部依存はほぼゼロ。ローカルで完結する（ネットワークに何も送らない）。

## 特徴

- 📄 **見やすい表示** — 見出しの色分け・コードハイライト・テーブル装飾
- 🎨 **カラーユニバーサルデザイン（CUD）対応** — 色覚に配慮した配色（紫・マゼンタを排除し、青・シアン・アンバー系で構成）
- 📁 **サイドバー** — 同じフォルダの `.md` 一覧表示 + フォルダ移動
- ✏️ **編集モード** — 左エディタ + 右ライブプレビューの分割ビュー、自動保存（1.5秒）+ `Ctrl+S`
- 🔍 **文字サイズ変更** — ボタンで拡大・縮小
- 🔒 **ローカル限定** — `localhost` のみで動作、クロスオリジンからのアクセスを遮断

## インストール

### 方法 A: exe を使う（Python 不要・おすすめ）

1. [Releases](https://github.com/kozimusafu-create/markdown-viewer/releases) から `md_viewer.exe` をダウンロード
2. `setup_md_viewer.ps1` と同じフォルダに置く
3. PowerShell で `setup_md_viewer.ps1` を実行（管理者権限不要）

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_md_viewer.ps1
```

### 方法 B: ソースから使う（Python 3.10+ が必要）

```powershell
pip install markdown
powershell -ExecutionPolicy Bypass -File .\setup_md_viewer.ps1
```

`md_viewer.exe` が無ければ自動で `md_viewer.py` + `pythonw.exe` を使う。

### ⚠️ Windows 10/11 の既定アプリ設定について

Windows 10/11 はセキュリティ上、既定アプリの変更をスクリプトから直接できない。セットアップ後、**一度だけ手動設定**が必要:

1. `.md` ファイルを右クリック → **プログラムから開く** → **別のプログラムを選択**
2. **markdown-viewer** を選び、**「常にこのアプリを使う」**にチェック

以降はダブルクリックで開くようになる。

## 使い方

- **ダブルクリック** で `.md` を開く
- コマンドラインからも開ける:

```powershell
md_viewer.exe path\to\file.md
# または
pythonw md_viewer.py path\to\file.md
```

- 引数なしで起動するとファイル選択ダイアログが出る

## アンインストール

ファイル関連付けを解除する:

```powershell
powershell -ExecutionPolicy Bypass -File .\unsetup_md_viewer.ps1
```

その後、ダウンロードしたファイルを削除すれば完了。

## 仕組み

- ローカルに HTTP サーバ（`localhost` のランダムポート）を立て、既定ブラウザで表示する
- ファイルの読み書き API は `Host` / `Origin` ヘッダを検証し、他サイト・LAN からのアクセスを拒否する
- レンダリングは Python の [`markdown`](https://pypi.org/project/markdown/) ライブラリ（`tables` / `fenced_code` / `nl2br` / `sane_lists` 拡張）

## ソースからの exe ビルド

```powershell
pip install markdown pyinstaller
pyinstaller --onefile --noconsole md_viewer.py
# dist\md_viewer.exe が生成される
```

## ライセンス

[MIT License](LICENSE) © 2026 kozimusafu-create
