import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz
from PIL import Image, ImageTk
import json
import os

COORD_DB_DIR = "./coord_db"


# ============================================================
# セットアップダイアログ
# ============================================================
class SetupDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("セットアップ")
        self.resizable(False, False)
        self.result = None

        w, h = 480, 520
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.question_rows = []  # (key_var, type_var) のリスト

        self._build_ui()
        self.grab_set()
        self.wait_window()

    def _build_ui(self):
        outer = tk.Frame(self, padx=20, pady=16)
        outer.pack(fill="both", expand=True)

        # マスターID
        tk.Label(outer, text="マスターID", font=("", 10, "bold")).pack(anchor="w")
        tk.Label(outer, text="例: 2024_4_2", fg="gray", font=("", 9)).pack(anchor="w")
        self.id_var = tk.StringVar()
        tk.Entry(outer, textvariable=self.id_var, width=28, font=("", 10)).pack(anchor="w", pady=(2, 10))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=4)

        # オプション
        tk.Label(outer, text="オプション項目", font=("", 10, "bold")).pack(anchor="w", pady=(6, 2))
        self.score2_var = tk.BooleanVar()
        tk.Checkbutton(outer, text="score_field_2（2枚目の得点欄）あり",
                       variable=self.score2_var, font=("", 9)).pack(anchor="w")

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=8)

        # 設問数
        tk.Label(outer, text="設問数", font=("", 10, "bold")).pack(anchor="w")
        num_frame = tk.Frame(outer)
        num_frame.pack(anchor="w", pady=(2, 6))
        self.num_var = tk.StringVar(value="1")
        tk.Entry(num_frame, textvariable=self.num_var, width=5, font=("", 10)).pack(side="left")
        tk.Button(num_frame, text="確定", command=self._build_question_rows,
                  font=("", 9), padx=8).pack(side="left", padx=8)

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=4)

        # 設問キー入力エリア（動的生成）
        tk.Label(outer, text="各設問のキーと種別", font=("", 10, "bold")).pack(anchor="w", pady=(6, 2))

        # ヘッダー行
        hdr = tk.Frame(outer)
        hdr.pack(fill="x", anchor="w")
        tk.Label(hdr, text="設問キー", width=10, font=("", 9, "bold"), anchor="w").pack(side="left")
        tk.Label(hdr, text="種別", font=("", 9, "bold"), anchor="w").pack(side="left", padx=(12, 0))

        self.rows_frame = tk.Frame(outer)
        self.rows_frame.pack(fill="x", anchor="w")

        # OKボタン
        tk.Button(outer, text="OK  →  PDFを選択", bg="#1a56db", fg="white",
                  font=("", 11, "bold"), command=self._on_ok,
                  relief="flat", cursor="hand2").pack(pady=(16, 0), ipadx=16, ipady=6)

        # 初期1行表示
        self._build_question_rows()

    def _build_question_rows(self):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.question_rows.clear()

        try:
            n = int(self.num_var.get())
            n = max(1, min(n, 10))
        except ValueError:
            n = 1

        for i in range(n):
            row = tk.Frame(self.rows_frame)
            row.pack(fill="x", pady=3, anchor="w")

            key_var = tk.StringVar()
            tk.Entry(row, textvariable=key_var, width=10, font=("", 10)).pack(side="left")

            type_var = tk.StringVar(value="記述式")
            tk.Radiobutton(row, text="記述式", variable=type_var,
                           value="記述式", font=("", 9)).pack(side="left", padx=(12, 0))
            tk.Radiobutton(row, text="マーク式", variable=type_var,
                           value="マーク式", font=("", 9)).pack(side="left", padx=(4, 0))

            self.question_rows.append((key_var, type_var))

    def _on_ok(self):
        master_id = self.id_var.get().strip()
        if not master_id:
            messagebox.showerror("エラー", "マスターIDを入力してください")
            return

        questions = {}
        for key_var, type_var in self.question_rows:
            k = key_var.get().strip()
            if not k:
                messagebox.showerror("エラー", "設問キーが空です。すべて入力してください")
                return
            questions[k] = type_var.get()

        self.result = {
            "master_id": master_id,
            "score_field_2": self.score2_var.get(),
            "questions": questions,
        }
        self.destroy()


# ============================================================
# メイン座標取得ウィンドウ
# ============================================================
class CoordinatePicker:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.master_id = config["master_id"]

        self.root.title(f"座標取得ツール — {self.master_id}")
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1200x900")

        self.pdf_doc = None
        self.current_page_idx = 0
        self.img_tk = None
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.rect_id = None
        self.start_x = None
        self.start_y = None

        self.coord_data = {}
        self.steps = self._build_steps()
        self.step_index = 0

        self._build_ui()
        self.root.after(100, self._load_pdf)

    def _build_steps(self):
        steps = []
        steps.append(("【合計点欄】をドラッグしてください", "total_score"))
        steps.append(("【採点者名欄】をドラッグしてください", "grader_name"))

        if self.config["score_field_2"]:
            steps.append(("【2枚目の得点欄 (score_field_2)】をドラッグしてください", "score_field_2"))

        for key, qtype in self.config["questions"].items():
            if qtype == "記述式":
                steps.append((f"【設問 {key} の小計欄 (score)】をドラッグしてください", f"q:{key}:score"))
                steps.append((f"【設問 {key} のテキスト欄 (text)】をドラッグしてください", f"q:{key}:text"))
            else:
                steps.append((f"【設問 {key} の配点テキスト欄 (score)】をドラッグしてください", f"q:{key}:score"))

        steps.append(("【コメント欄 (comment_box)】をドラッグしてください", "comment_box"))
        return steps

    def _build_ui(self):
        self.guide_bar = tk.Frame(self.root, bg="#1a56db")
        self.guide_bar.pack(fill="x", side="top")

        self.guide_label = tk.Label(
            self.guide_bar, text="", fg="white", bg="#1a56db",
            font=("", 12, "bold"), anchor="w"
        )
        self.guide_label.pack(side="left", padx=16, pady=10)

        self.step_counter = tk.Label(
            self.guide_bar, text="", fg="#cce0ff", bg="#1a56db", font=("", 10)
        )
        self.step_counter.pack(side="right", padx=16)

        btn_frame = tk.Frame(self.guide_bar, bg="#1a56db")
        btn_frame.pack(side="right", padx=8)
        tk.Button(btn_frame, text="やり直し", command=self._redo_step,
                  bg="#c0392b", fg="white", relief="flat", padx=8,
                  cursor="hand2").pack(side="left", padx=4, pady=6)
        tk.Button(btn_frame, text="スキップ", command=self._skip_step,
                  bg="#555", fg="white", relief="flat", padx=8,
                  cursor="hand2").pack(side="left", padx=4, pady=6)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame, cursor="cross", bg="grey")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vbar = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        vbar.grid(row=0, column=1, sticky="ns")
        hbar = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        ctrl = tk.Frame(self.root)
        ctrl.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        tk.Button(ctrl, text="◀ 前のページ", command=self._prev_page).pack(side="left", padx=5)
        self.page_label = tk.Label(ctrl, text="ページ: - / -")
        self.page_label.pack(side="left", padx=20)
        tk.Button(ctrl, text="次のページ ▶", command=self._next_page).pack(side="left", padx=5)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self._update_guide()

    def _update_guide(self):
        if self.step_index < len(self.steps):
            label, _ = self.steps[self.step_index]
            self.guide_label.config(text=label)
            self.step_counter.config(text=f"ステップ {self.step_index + 1} / {len(self.steps)}")
        else:
            self.guide_label.config(text="✅ 全ステップ完了！保存しています...")
            self.step_counter.config(text="")

    def _load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            self.root.destroy()
            return
        self.pdf_doc = fitz.open(path)
        self.current_page_idx = 0
        self._render_page()

    def _render_page(self):
        if not self.pdf_doc:
            return
        page = self.pdf_doc[self.current_page_idx]
        self.page_label.config(text=f"ページ: {self.current_page_idx + 1} / {len(self.pdf_doc)}")

        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width() or 900
        ch = self.canvas.winfo_height() or 900

        zoom_x = (cw * 0.95) / page.rect.width
        zoom_y = (ch * 0.95) / page.rect.height
        self.zoom_factor = min(zoom_x, zoom_y)

        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.img_tk = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.offset_x = max(0, (cw - pix.width) / 2)
        self.offset_y = max(0, (ch - pix.height) / 2)
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.img_tk)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.rect_id = None

    def _prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self._render_page()

    def _next_page(self):
        if self.pdf_doc and self.current_page_idx < len(self.pdf_doc) - 1:
            self.current_page_idx += 1
            self._render_page()

    def _on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )

    def _on_drag(self, event):
        self.canvas.coords(
            self.rect_id,
            self.start_x, self.start_y,
            self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        )

    def _on_release(self, event):
        if self.step_index >= len(self.steps):
            return

        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        x0 = max(0, (min(self.start_x, end_x) - self.offset_x) / self.zoom_factor)
        y0 = max(0, (min(self.start_y, end_y) - self.offset_y) / self.zoom_factor)
        x1 = max(0, (max(self.start_x, end_x) - self.offset_x) / self.zoom_factor)
        y1 = max(0, (max(self.start_y, end_y) - self.offset_y) / self.zoom_factor)

        coord = [self.current_page_idx, round(x0), round(y0), round(x1), round(y1)]
        _, key_path = self.steps[self.step_index]
        self._store(key_path, coord)

        self.step_index += 1
        self._update_guide()

        if self.step_index >= len(self.steps):
            self._save_json()

    def _store(self, key_path, coord):
        if key_path.startswith("q:"):
            _, q_key, field = key_path.split(":")
            self.coord_data.setdefault("questions", {}).setdefault(q_key, {})[field] = coord
        else:
            self.coord_data[key_path] = coord

    def _redo_step(self):
        if self.step_index == 0:
            return
        self.step_index -= 1
        _, key_path = self.steps[self.step_index]
        if key_path.startswith("q:"):
            _, q_key, field = key_path.split(":")
            qs = self.coord_data.get("questions", {})
            if q_key in qs and field in qs[q_key]:
                del qs[q_key][field]
        else:
            self.coord_data.pop(key_path, None)
        self._update_guide()

    def _skip_step(self):
        if self.step_index >= len(self.steps):
            return
        self.step_index += 1
        self._update_guide()
        if self.step_index >= len(self.steps):
            self._save_json()

    def _save_json(self):
        os.makedirs(COORD_DB_DIR, exist_ok=True)
        out_path = os.path.join(COORD_DB_DIR, f"{self.master_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.coord_data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("保存完了", f"座標データを保存しました:\n{out_path}")
        self.root.destroy()


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    dialog = SetupDialog(root)
    if dialog.result is None:
        root.destroy()
    else:
        root.deiconify()
        app = CoordinatePicker(root, dialog.result)
        root.mainloop()