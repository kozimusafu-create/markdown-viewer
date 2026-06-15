#!/usr/bin/env python3
"""Markdownビューア — サイドバー付きローカルHTTPサーバー版"""
import sys, os, json, threading, time, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

# ------------------------------------------------------------------ helpers --

def render_md(text):
    try:
        import markdown
        return markdown.markdown(
            text, extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
        )
    except ImportError:
        import html as h
        return "<pre>" + h.escape(text) + "</pre>"

def scan_dir(directory):
    """サブディレクトリと .md ファイルを返す。"""
    dirs, files = [], []
    try:
        for name in sorted(os.listdir(directory)):
            full = os.path.join(directory, name).replace("\\", "/")
            if os.path.isdir(os.path.join(directory, name)):
                dirs.append({"name": name, "path": full})
            elif name.lower().endswith((".md", ".markdown")):
                files.append({"name": name, "path": full})
    except Exception:
        pass
    return dirs, files

def parent_of(directory):
    p = os.path.dirname(directory)
    return None if p == directory else p.replace("\\", "/")

# ------------------------------------------------------------------- assets --

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  display: flex; height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Yu Gothic UI', 'Meiryo', sans-serif;
  background: #f4f6fb; color: #1a1d2e; overflow: hidden;
}

/* ---- sidebar ---- */
#sidebar {
  width: 240px; min-width: 160px; max-width: 400px;
  background: #1a1d2e; color: #c8cde8;
  display: flex; flex-direction: column; overflow: hidden;
  border-right: 1px solid #0d0f1a; flex-shrink: 0;
  resize: horizontal;
}
#sidebar-header {
  padding: 13px 14px 8px;
  font-size: 0.72em; font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase; color: #8A9BBF;
  border-bottom: 1px solid #2c3054; flex-shrink: 0;
}
#sidebar-dir {
  padding: 7px 14px 7px 12px; font-size: 0.73em; color: #8891b8;
  word-break: break-all; border-bottom: 1px solid #2c3054;
  background: #141626; flex-shrink: 0; line-height: 1.4;
}
#file-list { flex: 1; overflow-y: auto; padding: 4px 0; }
#file-list::-webkit-scrollbar { width: 4px; }
#file-list::-webkit-scrollbar-thumb { background: #2c3054; border-radius: 2px; }

.item {
  padding: 8px 14px; font-size: 0.85em; cursor: pointer;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: background 0.12s; border-left: 3px solid transparent;
  user-select: none;
}
.item:hover { background: #1E2D4A; color: #E0EEFF; }
/* ディレクトリ: 空色 (#56B4E9) — CUDO推奨、色弱でも識別可 */
.item-dir  { color: #63C5E3; }
.item-dir:hover { color: #A8E0EF; }
.item-up   { color: #8A9BBF; font-style: italic; }
.item-file { color: #C8CDE8; }
.item-file.active {
  background: #162438; color: #63C5E3;
  border-left-color: #56B4E9; font-weight: 600;
}

/* ---- main ---- */
#main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
#topbar {
  display: flex; align-items: center; gap: 8px; padding: 9px 18px;
  background: #fff; border-bottom: 1px solid #e0e4f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07); flex-shrink: 0;
}
#topbar-title {
  flex: 1; font-size: 0.9em; font-weight: 600; color: #3a3f6b;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ctrl-btn {
  padding: 4px 11px; border: 1px solid #c8cde8; border-radius: 5px;
  background: #f4f6fb; color: #3a3f6b; font-size: 0.82em;
  cursor: pointer; transition: all 0.15s; flex-shrink: 0;
}
.ctrl-btn:hover { background: #005AFF; color: #fff; border-color: #005AFF; }
#content-wrap { flex: 1; overflow-y: auto; padding: 36px 48px; position: relative; }
#content-wrap::-webkit-scrollbar { width: 6px; }
#content-wrap::-webkit-scrollbar-thumb { background: #c8cde8; border-radius: 3px; }
#content { max-width: 820px; margin: 0 auto; line-height: 1.75; font-size: 16px; }

/* ---- headings ---- */
/* h1: 青(#005AFF)→シアン(#00838F) — CUDO推奨青+ティール、紫を完全排除 */
#content h1 {
  font-size: 2em; font-weight: 800;
  background: linear-gradient(120deg, #005AFF 0%, #00838F 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 2px 4px rgba(0,90,130,0.22));
  padding-bottom: 10px; border-bottom: 2px solid #D6E8F5; margin: 1.8em 0 0.7em;
}
/* h2: CUDO推奨青 #005AFF — 高コントラスト、背景は淡い空色 */
#content h2 {
  font-size: 1.45em; font-weight: 700; color: #005AFF;
  border-left: 4px solid #005AFF; padding: 6px 14px; margin: 1.6em 0 0.6em;
  background: linear-gradient(90deg, #E8F4FF 0%, transparent 80%);
  border-radius: 0 6px 6px 0;
  box-shadow: inset 0 1px 0 rgba(0,90,255,0.07), inset 0 -1px 0 rgba(0,90,255,0.07);
}
/* h3: ティール #005F73 — h2青と明確に区別、色弱でも判別可 */
#content h3 {
  font-size: 1.18em; font-weight: 700; color: #005F73;
  padding-left: 10px; border-left: 3px solid #56B4E9; margin: 1.4em 0 0.5em;
}
#content h4, #content h5, #content h6 {
  font-size: 1em; font-weight: 700; color: #334155; margin: 1.2em 0 0.4em;
}
#content h1:first-child, #content h2:first-child { margin-top: 0; }

/* ---- body text ---- */
#content p { margin: 0.7em 0; color: #1e293b; }
#content a { color: #005AFF; text-decoration: none; }
#content a:hover { text-decoration: underline; }
#content strong { font-weight: 700; color: #111827; }
#content em { font-style: italic; }

/* ---- code ---- */
/* インラインコード: アンバー系 — マゼンタ(#c026d3)は色弱で危険、CUDO茶系に置換 */
#content code {
  background: #FFF8E6; border: 1px solid #D4A843; border-radius: 4px;
  padding: 0.15em 0.45em;
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  font-size: 0.875em; color: #7A4800;
}
#content pre {
  background: #1e293b; border-radius: 8px; padding: 18px 20px;
  overflow-x: auto; margin: 1em 0;
  box-shadow: 0 4px 16px rgba(15,23,42,0.22), 0 1px 3px rgba(0,0,0,0.12);
}
#content pre code { background: none; border: none; padding: 0; color: #e2e8f0; font-size: 0.88em; }

/* ---- blockquote ---- */
/* CUDO推奨空色(#56B4E9)で枠線 — 薄紫は色弱でグレーと混同されやすい */
#content blockquote {
  border-left: 4px solid #56B4E9; background: #E8F5FF;
  padding: 10px 16px; border-radius: 0 6px 6px 0; color: #2D4A5A; margin: 1em 0;
}
#content blockquote p { margin: 0.2em 0; color: inherit; }

/* ---- table ---- */
#content table {
  border-collapse: collapse; width: 100%; margin: 1em 0;
  font-size: 0.92em; border-radius: 8px; overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.09);
}
/* テーブルヘッダー: 青→シアン — インディゴ(#4f46e5)紫系を空色系に置換 */
#content th {
  background: linear-gradient(135deg, #005AFF, #0077AA);
  color: #fff; padding: 9px 13px; text-align: left; font-weight: 600;
}
#content td { padding: 8px 13px; border-bottom: 1px solid #D6E8F5; }
#content tr:nth-child(even) td { background: #F2FAFF; }
#content tr:hover td { background: #E0F0FF; }

/* ---- list / hr ---- */
#content ul, #content ol { padding-left: 1.8em; margin: 0.5em 0; }
#content li { margin: 0.35em 0; }
#content hr { border: none; border-top: 2px solid #e0e4f0; margin: 2em 0; }

/* ---- loading overlay ---- */
#loading-overlay {
  display: none; position: absolute; inset: 0;
  background: rgba(244,246,251,0.8);
  align-items: center; justify-content: center;
  font-size: 0.95em; color: #005AFF; z-index: 50;
}

/* ---- edit mode ---- */
#split-container {
  display: none; flex: 1; overflow: hidden;
}
#split-container.active { display: flex; }
#content-wrap.edit-hidden { display: none; }

#editor-pane {
  flex: 0 0 50%; display: flex; flex-direction: column;
  overflow: hidden; background: #1E2433;
}
#editor-toolbar {
  display: flex; align-items: center; gap: 8px; padding: 6px 12px;
  background: #161C2A; border-bottom: 1px solid #2C3550; flex-shrink: 0;
  font-size: 0.8em;
}
#save-status {
  margin-left: auto; font-size: 0.85em; padding: 2px 8px;
  border-radius: 4px; transition: all 0.3s;
}
#save-status.saving { color: #F6AA00; }
#save-status.saved  { color: #03AF7A; }
#save-status.error  { color: #FF4B00; }
#md-editor {
  flex: 1; resize: none; border: none; outline: none;
  background: #1E2433; color: #CDD6F4;
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  font-size: 0.9em; line-height: 1.7; padding: 20px 24px;
  tab-size: 2; overflow-y: auto;
}
#md-editor::-webkit-scrollbar { width: 6px; }
#md-editor::-webkit-scrollbar-thumb { background: #2C3550; border-radius: 3px; }

#split-divider {
  width: 5px; background: #2C3550; cursor: col-resize; flex-shrink: 0;
  transition: background 0.15s;
}
#split-divider:hover, #split-divider.dragging { background: #56B4E9; }

#preview-pane {
  flex: 1; overflow-y: auto; padding: 36px 48px; position: relative;
  background: #f4f6fb;
}
#preview-pane::-webkit-scrollbar { width: 6px; }
#preview-pane::-webkit-scrollbar-thumb { background: #c8cde8; border-radius: 3px; }
#preview-content { max-width: 820px; margin: 0 auto; line-height: 1.75; font-size: 16px; }

/* edit mode topbar extras */
#btn-edit  { background: #f4f6fb; }
#btn-edit.active { background: #005AFF; color: #fff; border-color: #005AFF; }
"""

# currentPath は HTML 側で var 宣言済み → JS 内で再宣言しない
JS = r"""
var fontSize = 16;

function buildSidebar(dirs, files, dir, parent) {
  document.getElementById('sidebar-dir').textContent = dir;
  var list = document.getElementById('file-list');
  list.innerHTML = '';

  // 上の階層へ
  if (parent) {
    var up = document.createElement('div');
    up.className = 'item item-up';
    up.textContent = '↑ 上の階層へ';
    up.title = parent;
    up.onclick = function() { loadDir(parent); };
    list.appendChild(up);
  }

  // サブディレクトリ
  dirs.forEach(function(d) {
    var el = document.createElement('div');
    el.className = 'item item-dir';
    el.textContent = '📁 ' + d.name;
    el.title = d.path;
    el.onclick = function() { loadDir(d.path); };
    list.appendChild(el);
  });

  // md ファイル
  files.forEach(function(f) {
    var el = document.createElement('div');
    el.className = 'item item-file' + (f.path === currentPath ? ' active' : '');
    el.textContent = '📄 ' + f.name;
    el.title = f.path;
    el.dataset.path = f.path;
    el.onclick = function() { loadFile(f.path); };
    list.appendChild(el);
  });
}

function setActive(path) {
  document.querySelectorAll('.item-file').forEach(function(el) {
    el.classList.toggle('active', el.dataset.path === path);
  });
}

async function loadDir(dirPath) {
  var r = await fetch('/api/files?dir=' + encodeURIComponent(dirPath));
  if (!r.ok) return;
  var d = await r.json();
  if (d.error) { alert(d.error); return; }
  buildSidebar(d.dirs, d.files, d.dir, d.parent);
}

async function loadFile(path) {
  var overlay = document.getElementById('loading-overlay');
  overlay.style.display = 'flex';
  try {
    var r = await fetch('/api/content?path=' + encodeURIComponent(path));
    if (!r.ok) { alert('サーバーエラー: ' + r.status); return; }
    var d = await r.json();
    if (d.error) { alert('読み込みエラー:\n' + d.error); return; }
    document.getElementById('content').innerHTML = d.html;
    document.getElementById('topbar-title').textContent = d.title;
    document.title = d.title;
    currentPath = d.path;
    buildSidebar(d.dirs, d.files, d.dir, d.parent);
    document.getElementById('content-wrap').scrollTop = 0;
  } catch(e) {
    alert('通信エラー:\n' + e.message);
  } finally {
    overlay.style.display = 'none';
  }
}

function changeFontSize(delta) {
  fontSize = Math.max(11, Math.min(26, fontSize + delta));
  document.getElementById('content').style.fontSize = fontSize + 'px';
}

document.getElementById('btn-smaller').onclick = function() { changeFontSize(-1); };
document.getElementById('btn-larger' ).onclick = function() { changeFontSize(+1); };

// ---------------------------------------------------------------- edit mode --
var editMode = false;
var saveTimer = null;
var renderTimer = null;

function enterEdit() {
  if (editMode) return;
  editMode = true;
  // 現在のMarkdownソースを取得してエディタに流す
  fetch('/api/source?path=' + encodeURIComponent(currentPath))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      document.getElementById('md-editor').value = d.source || '';
      // プレビューペインに現在のHTMLをコピー
      document.getElementById('preview-content').innerHTML =
        document.getElementById('content').innerHTML;
    });
  document.getElementById('content-wrap').classList.add('edit-hidden');
  document.getElementById('split-container').classList.add('active');
  document.getElementById('btn-edit').classList.add('active');
  document.getElementById('btn-edit').textContent = '閲覧に戻る';
  document.getElementById('md-editor').focus();
}

function exitEdit() {
  if (!editMode) return;
  editMode = false;
  // 保存してからビューに戻る
  doSave().then(function() {
    // 最新のレンダリングをメインコンテンツに反映
    document.getElementById('content').innerHTML =
      document.getElementById('preview-content').innerHTML;
  });
  document.getElementById('split-container').classList.remove('active');
  document.getElementById('content-wrap').classList.remove('edit-hidden');
  document.getElementById('btn-edit').classList.remove('active');
  document.getElementById('btn-edit').textContent = '✏️ 編集';
}

document.getElementById('btn-edit').onclick = function() {
  editMode ? exitEdit() : enterEdit();
};

// エディタ入力 → ライブプレビュー + 自動保存
document.getElementById('md-editor').addEventListener('input', function() {
  setSaveStatus('');

  // ライブプレビュー（300ms debounce）
  clearTimeout(renderTimer);
  renderTimer = setTimeout(function() {
    var text = document.getElementById('md-editor').value;
    fetch('/api/render', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content: text})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.html) document.getElementById('preview-content').innerHTML = d.html;
    });
  }, 300);

  // 自動保存（1500ms debounce）
  clearTimeout(saveTimer);
  saveTimer = setTimeout(function() { doSave(); }, 1500);
});

// Ctrl+S で即時保存
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    if (editMode) doSave();
  }
});

async function doSave() {
  var text = document.getElementById('md-editor').value;
  setSaveStatus('saving');
  try {
    var r = await fetch('/api/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: currentPath, content: text})
    });
    var d = await r.json();
    if (d.error) { setSaveStatus('error'); return; }
    setSaveStatus('saved');
    setTimeout(function() { setSaveStatus(''); }, 2500);
  } catch(e) {
    setSaveStatus('error');
  }
}

function setSaveStatus(status) {
  var el = document.getElementById('save-status');
  el.className = status;
  el.textContent = status === 'saving' ? '保存中…'
                 : status === 'saved'  ? '✓ 保存済'
                 : status === 'error'  ? '✗ 保存失敗'
                 : '';
}

// ---- 分割線ドラッグ ----
(function() {
  var divider = document.getElementById('split-divider');
  var container = document.getElementById('split-container');
  var editorPane = document.getElementById('editor-pane');
  var dragging = false;

  divider.addEventListener('mousedown', function(e) {
    dragging = true;
    divider.classList.add('dragging');
    e.preventDefault();
  });
  document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    var rect = container.getBoundingClientRect();
    var pct = Math.max(20, Math.min(80,
      (e.clientX - rect.left) / rect.width * 100));
    editorPane.style.flex = '0 0 ' + pct + '%';
  });
  document.addEventListener('mouseup', function() {
    if (dragging) { dragging = false; divider.classList.remove('dragging'); }
  });
})();

// 初期サイドバーを JS で描画（INIT データを使用）
buildSidebar(window.__INIT__.dirs, window.__INIT__.files,
             window.__INIT__.dir,  window.__INIT__.parent);
setActive(currentPath);
"""

PAGE_TMPL = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%%TITLE%%</title>
<style>%%CSS%%</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-header">📁 ファイル一覧</div>
  <div id="sidebar-dir"></div>
  <div id="file-list"></div>
</div>

<div id="main">
  <div id="topbar">
    <span id="topbar-title">%%TITLE%%</span>
    <span id="save-status"></span>
    <button class="ctrl-btn" id="btn-edit">✏️ 編集</button>
    <button class="ctrl-btn" id="btn-smaller">A－</button>
    <button class="ctrl-btn" id="btn-larger" >A＋</button>
  </div>

  <!-- 閲覧ビュー -->
  <div id="content-wrap">
    <div id="loading-overlay">読み込み中…</div>
    <div id="content">%%CONTENT%%</div>
  </div>

  <!-- 編集ビュー（左テキストエリア + 右プレビュー） -->
  <div id="split-container">
    <div id="editor-pane">
      <div id="editor-toolbar">
        <span style="color:#8891b8">Markdown</span>
        <span style="color:#556080;margin-left:auto;font-size:0.9em">Ctrl+S で保存</span>
      </div>
      <textarea id="md-editor" spellcheck="false"></textarea>
    </div>
    <div id="split-divider"></div>
    <div id="preview-pane">
      <div id="preview-content"></div>
    </div>
  </div>
</div>

<script>
var currentPath = %%PATH_JSON%%;
window.__INIT__ = %%INIT_JSON%%;
%%JS%%
</script>
</body>
</html>
"""

def build_page(path):
    abs_path = os.path.abspath(path).replace("\\", "/")
    directory = os.path.dirname(abs_path)

    try:
        with open(abs_path, encoding="utf-8") as f:
            text = f.read()
        content_html = render_md(text)
        title = os.path.basename(abs_path)
    except Exception as e:
        content_html = f"<p style='color:red'>エラー: {e}</p>"
        title = "エラー"

    dirs, files = scan_dir(directory)
    init = {"dirs": dirs, "files": files, "dir": directory, "parent": parent_of(directory)}

    return (
        PAGE_TMPL
        .replace("%%TITLE%%",     title, 2)
        .replace("%%CSS%%",       CSS)
        .replace("%%CONTENT%%",   content_html)
        .replace("%%PATH_JSON%%", json.dumps(abs_path))
        .replace("%%INIT_JSON%%", json.dumps(init, ensure_ascii=False))
        .replace("%%JS%%",        JS)
    )

# ------------------------------------------------------------------ handler --

class Handler(BaseHTTPRequestHandler):
    initial_file = ""
    port = 0

    # --- セキュリティ: localhost 限定 + クロスオリジン書き込み遮断 ---
    def _host_ok(self):
        """Host ヘッダが自分の localhost:port か検証 (DNS リバインディング対策)。"""
        host = self.headers.get("Host", "")
        return host in (f"localhost:{self.port}",
                        f"127.0.0.1:{self.port}",
                        f"[::1]:{self.port}")

    def _origin_ok(self):
        """POST の Origin が同一オリジンか検証 (クロスオリジン書き込み遮断)。
        自分のページからの fetch は必ず Origin を送るため、欠落・不一致は拒否。"""
        origin = self.headers.get("Origin", "")
        return origin in (f"http://localhost:{self.port}",
                          f"http://127.0.0.1:{self.port}",
                          f"http://[::1]:{self.port}")

    @staticmethod
    def _is_md(path):
        """読み書き対象を Markdown に限定 (機微ファイルの読取・上書きを防ぐ)。"""
        return path.lower().endswith((".md", ".markdown"))

    def do_GET(self):
        if not self._host_ok():
            self.send_error(403); return
        p  = urlparse(self.path)
        qs = parse_qs(p.query)

        if p.path == "/":
            html = build_page(self.initial_file)
            self._write(200, "text/html", html.encode("utf-8"))

        elif p.path == "/api/content":
            self._serve_content(unquote(qs.get("path", [""])[0]))

        elif p.path == "/api/files":
            self._serve_files(unquote(qs.get("dir", [""])[0]))

        elif p.path == "/api/source":
            path = os.path.abspath(unquote(qs.get("path", [""])[0]))
            if not self._is_md(path):
                self._json({"error": "対応していないファイル形式です (.md / .markdown のみ)"}); return
            try:
                with open(path, encoding="utf-8") as f:
                    source = f.read()
                self._json({"source": source})
            except Exception as e:
                self._json({"error": str(e)})

        else:
            self.send_error(404)

    def do_POST(self):
        # ボディを先に読み切ってから判定 (403 時の接続リセットを防ぐ)
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        if not self._host_ok() or not self._origin_ok():
            self.send_error(403); return
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json({"error": "invalid JSON"}); return

        if self.path == "/api/save":
            path    = os.path.abspath(data.get("path", ""))
            content = data.get("content", "")
            if not self._is_md(path):
                self._json({"error": "対応していないファイル形式です (.md / .markdown のみ)"}); return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._json({"ok": True})
            except Exception as e:
                self._json({"error": str(e)})

        elif self.path == "/api/render":
            content = data.get("content", "")
            self._json({"html": render_md(content)})

        else:
            self.send_error(404)

    def _serve_content(self, path):
        abs_path = os.path.abspath(path).replace("\\", "/")
        if not self._is_md(abs_path):
            self._json({"error": "対応していないファイル形式です (.md / .markdown のみ)"}); return
        directory = os.path.dirname(abs_path)
        try:
            with open(abs_path, encoding="utf-8") as f:
                text = f.read()
            dirs, files = scan_dir(directory)
            data = {
                "html":  render_md(text),
                "title": os.path.basename(abs_path),
                "path":  abs_path,
                "dir":   directory,
                "dirs":  dirs,
                "files": files,
                "parent": parent_of(directory),
            }
        except Exception as e:
            data = {"error": str(e)}
        self._json(data)

    def _serve_files(self, directory):
        directory = os.path.abspath(directory).replace("\\", "/")
        dirs, files = scan_dir(directory)
        self._json({
            "dir":    directory,
            "dirs":   dirs,
            "files":  files,
            "parent": parent_of(directory),
        })

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._write(200, "application/json", body)

    def _write(self, status, ctype, body):
        self.send_response(status)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass

# --------------------------------------------------------------------- main --

def pick_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Markdownファイルを選択",
            filetypes=[("Markdown", "*.md *.markdown"), ("すべて", "*.*")],
        )
        root.destroy()
        return path or None
    except Exception:
        return None

def free_port():
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def main():
    path = os.path.abspath(sys.argv[1]) if len(sys.argv) >= 2 else pick_file()
    if not path or not os.path.exists(path):
        sys.exit(0 if not path else 1)

    Handler.initial_file = path
    port = free_port()
    Handler.port = port
    server = HTTPServer(("localhost", port), Handler)

    threading.Thread(
        target=lambda: (time.sleep(0.3), webbrowser.open(f"http://localhost:{port}/")),
        daemon=True,
    ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
