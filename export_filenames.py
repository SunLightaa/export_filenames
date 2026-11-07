"""
将指定文件夹中的文件导出为 HTML 列表。
打开 HTML 后可按文件名称模糊搜索，并按文件名称升序/降序排序。
每行显示：文件名称 + 创建时间。
"""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
import webbrowser
from ctypes import windll
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk


def collect_files(folder: Path, recursive: bool = False) -> list[dict[str, str]]:
    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在：{folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"路径不是文件夹：{folder}")

    items: list[dict[str, str]] = []
    if recursive:
        walker = os.walk(folder)
        for dirpath, _, filenames in walker:
            for filename in filenames:
                path = Path(dirpath) / filename
                items.append(_file_item(path, path.stat().st_ctime))
    else:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_file():
                    items.append(_file_item(Path(entry.path), entry.stat().st_ctime))

    items.sort(key=lambda item: item["name"])
    return items


def _file_item(path: Path, ctime: float) -> dict[str, str]:
    return {
        "name": path.stem,
        "time": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S"),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>文件列表</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --card: #fff;
      --line: #e5e7eb;
      --text: #1f2937;
      --muted: #6b7280;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    .wrap { max-width: 980px; margin: 0 auto; padding: 24px 16px 40px; }
    h1 { font-size: 22px; margin: 0 0 16px; }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: end;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
    }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
    input, select {
      width: 100%;
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 10px;
      font-size: 14px;
    }
    .field-name { flex: 1 1 280px; }
    .field-sort { flex: 0 1 200px; }
    .field-export { flex: 0 0 auto; }
    button.export-btn {
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0 14px;
      font-size: 14px;
      background: #111827;
      color: #fff;
      cursor: pointer;
    }
    button.export-btn:hover { background: #374151; }
    .meta { color: var(--muted); font-size: 13px; margin: 0 0 10px; }
    .list { background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
    .head, .row {
      display: grid;
      grid-template-columns: 1fr 200px;
      gap: 16px;
      align-items: center;
      padding: 12px 14px;
    }
    .head {
      font-size: 13px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      background: #f9fafb;
    }
    .row { border-bottom: 1px solid var(--line); }
    .row:last-child { border-bottom: 0; }
    .name { font-size: 16px; word-break: break-all; }
    .time { color: var(--muted); font-size: 13px; }
    .empty { padding: 40px 16px; text-align: center; color: var(--muted); }
    @media (max-width: 720px) {
      .head, .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>文件列表</h1>
    <div class="toolbar">
      <div class="field-name">
        <label for="keyword">文件名称（模糊搜索）</label>
        <input id="keyword" type="search" placeholder="输入文件名称关键字" />
      </div>
      <div class="field-sort">
        <label for="sort">排序字段</label>
        <select id="sort">
          <option value="asc">文件名称升序</option>
          <option value="desc">文件名称降序</option>
        </select>
      </div>
      <div class="field-export">
        <label>&nbsp;</label>
        <button type="button" class="export-btn" id="exportBtn">导出 TXT</button>
      </div>
    </div>
    <p class="meta" id="meta"></p>
    <div class="list" id="list"></div>
  </div>
  <script>
    const ITEMS = __DATA__;

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function fuzzyMatch(text, query) {
      const q = (query || "").trim().toLowerCase();
      if (!q) return true;
      const t = (text || "").toLowerCase();
      if (t.includes(q)) return true;
      let i = 0;
      for (const ch of t) {
        if (ch === q[i]) i += 1;
        if (i === q.length) return true;
      }
      return false;
    }

    function getVisibleRows() {
      const keyword = document.getElementById("keyword").value;
      const sort = document.getElementById("sort").value;
      return ITEMS.filter((item) => fuzzyMatch(item.name, keyword)).sort((a, b) => {
        const cmp = a.name.localeCompare(b.name, "zh", { numeric: true, sensitivity: "base" });
        return sort === "desc" ? -cmp : cmp;
      });
    }

    function render() {
      const rows = getVisibleRows();

      document.getElementById("meta").textContent =
        "共 " + ITEMS.length + " 个文件，当前显示 " + rows.length + " 个";

      const list = document.getElementById("list");
      if (!rows.length) {
        list.innerHTML = '<div class="empty">没有匹配的文件</div>';
        return;
      }

      list.innerHTML =
        '<div class="head"><div>文件名称</div><div>创建时间</div></div>' +
        rows.map((item) => {
          return (
            '<div class="row">' +
              '<div class="name">' + escapeHtml(item.name) + "</div>" +
              '<div class="time">' + escapeHtml(item.time) + "</div>" +
            "</div>"
          );
        }).join("");
    }

    function exportTxt() {
      const rows = getVisibleRows();
      const content = rows.map((item) => item.name).join("\\n");
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "文件列表.txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }

    document.getElementById("keyword").addEventListener("input", render);
    document.getElementById("sort").addEventListener("change", render);
    document.getElementById("exportBtn").addEventListener("click", exportTxt);
    render();
  </script>
</body>
</html>
"""


def save_to_html(files: list[dict[str, str]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(files, ensure_ascii=False).replace("<", "\\u003c")
    output_file.write_text(
        HTML_TEMPLATE.replace("__DATA__", payload),
        encoding="utf-8",
    )


def open_in_browser(path: Path) -> None:
    resolved = path.resolve()
    if os.name == "nt":
        os.startfile(str(resolved))
        return
    webbrowser.open(resolved.as_uri())


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("文件名称导出")
        self.geometry("640x280")
        self.minsize(520, 260)
        self.resizable(True, True)

        self.folder_var = tk.StringVar()
        self._running = False

        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="要扫描的文件夹路径").grid(
            row=0, column=0, columnspan=3, sticky=tk.W
        )

        entry = ttk.Entry(root, textvariable=self.folder_var)
        entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(6, 12), padx=(0, 8))
        ttk.Button(root, text="浏览", command=self._browse_folder).grid(
            row=1, column=2, pady=(6, 12), sticky=tk.E
        )

        self.run_btn = ttk.Button(root, text="运行", command=self._on_run)
        self.run_btn.grid(row=2, column=0, columnspan=3, pady=(0, 16), ipadx=24)

        ttk.Label(root, text="输出结果").grid(row=3, column=0, columnspan=3, sticky=tk.W)

        self.result = tk.Text(root, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.result.grid(row=4, column=0, columnspan=3, sticky=tk.NSEW, pady=(6, 0))
        root.rowconfigure(4, weight=1)

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory(title="选择要扫描的文件夹")
        if selected:
            self.folder_var.set(selected)

    def _set_result(self, text: str) -> None:
        self.result.configure(state=tk.NORMAL)
        self.result.delete("1.0", tk.END)
        self.result.insert(tk.END, text)
        self.result.configure(state=tk.DISABLED)

    def _on_run(self) -> None:
        if self._running:
            return

        folder_text = self.folder_var.get().strip().strip('"')
        if not folder_text:
            self._set_result("请先填写要扫描的文件夹路径。")
            return

        self._running = True
        self.run_btn.configure(state=tk.DISABLED)
        self._set_result("正在导出，请稍候…")

        threading.Thread(target=self._run_export, args=(folder_text,), daemon=True).start()

    def _run_export(self, folder_text: str) -> None:
        try:
            folder = Path(folder_text).resolve()
            parent = folder.parent
            output_dir = parent if parent != folder else folder
            output_file = output_dir / "文件列表.html"
            files = collect_files(folder, recursive=False)
            save_to_html(files, output_file)
            open_in_browser(output_file)
            message = (
                f"输出成功\n"
                f"共导出{len(files)}个文件名称\n"
                f"已保存到：{output_file}"
            )
        except Exception as exc:
            message = f"导出失败：{exc}"

        self.after(0, lambda: self._finish(message))

    def _finish(self, message: str) -> None:
        self._running = False
        self.run_btn.configure(state=tk.NORMAL)
        self._set_result(message)


def main() -> None:
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
