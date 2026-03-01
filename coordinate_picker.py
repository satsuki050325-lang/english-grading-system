import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import fitz
from PIL import Image, ImageTk
import json
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COORD_DB_DIR = "./coord_db"

BG_DARK    = "#0f141f"
BG_CARD    = "#1e2332"
BG_CARD2   = "#141928"
BLUE       = "#1a56db"
BLUE_HOVER = "#1648b8"
RED        = "#c0392b"
RED_HOVER  = "#96281b"
GRAY_BTN   = "#2d3245"
GRAY_HOVER = "#363b52"
TEXT_1     = "#f1f5f9"
TEXT_2     = "#94a3b8"
TEXT_3     = "#64748b"
BORDER     = "#2a3050"
FONT_JP    = "Yu Gothic UI"


def jp(size=12, weight="normal"):
    return ctk.CTkFont(family=FONT_JP, size=size, weight=weight)


# ============================================================
# セットアップ画面
# ============================================================
class SetupDialog:
    def __init__(self, root):
        self.root = root
        self.result = None
        self.question_rows = []

        self.root.title("セットアップ — 座標取得ツール")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG_DARK)

        w, h = 500, 580
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        # タイトルバー
        title_bar = ctk.CTkFrame(self.root, fg_color=BG_CARD, corner_radius=0, height=52)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        ctk.CTkLabel(title_bar, text="座標取得ツール  セットアップ",
                     font=jp(14, "bold"), text_color=TEXT_1).pack(side="left", padx=20)

        # OKボタン（最下部固定）
        btn_frame = ctk.CTkFrame(self.root, fg_color=BG_DARK)
        btn_frame.pack(fill="x", side="bottom", padx=24, pady=16)
        ctk.CTkButton(btn_frame, text="OK  →  PDFを選択", height=48, corner_radius=12,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      text_color="white", font=jp(13, "bold"),
                      command=self._on_ok).pack(fill="x")

        # スクロール可能コンテンツ
        outer = ctk.CTkScrollableFrame(self.root, fg_color=BG_DARK,
                                       scrollbar_button_color=GRAY_BTN)
        outer.pack(fill="both", expand=True, padx=24, pady=(12, 0))

        self._label(outer, "マスターID")
        ctk.CTkLabel(outer, text="例: 2024_4_2", text_color=TEXT_3, font=jp(11)).pack(anchor="w")
        self.id_var = tk.StringVar()
        ctk.CTkEntry(outer, textvariable=self.id_var, width=260, height=38,
                     fg_color=BG_CARD2, border_color=BORDER, border_width=1,
                     text_color=TEXT_1, font=jp(12),
                     placeholder_text="例: 2024_4_2").pack(anchor="w", pady=(4, 12))
        self._divider(outer)

        self._label(outer, "オプション")
        self.score2_var = tk.BooleanVar()
        ctk.CTkCheckBox(outer, text="score_field_2（2枚目の得点欄）あり",
                        variable=self.score2_var, fg_color=BLUE, hover_color=BLUE_HOVER,
                        text_color=TEXT_2, font=jp(12),
                        border_color=TEXT_3).pack(anchor="w", pady=(4, 12))
        self._divider(outer)

        self._label(outer, "設問数")
        num_frame = ctk.CTkFrame(outer, fg_color="transparent")
        num_frame.pack(anchor="w", pady=(4, 8))
        self.num_var = tk.StringVar(value="1")
        ctk.CTkEntry(num_frame, textvariable=self.num_var, width=64, height=36,
                     fg_color=BG_CARD2, border_color=BORDER, border_width=1,
                     text_color=TEXT_1, font=jp(12), justify="center").pack(side="left")
        ctk.CTkButton(num_frame, text="確定", width=80, height=36,
                      fg_color=GRAY_BTN, hover_color=GRAY_HOVER,
                      text_color=TEXT_1, font=jp(12),
                      command=self._build_question_rows,
                      corner_radius=8).pack(side="left", padx=(10, 0))
        self._divider(outer)

        self._label(outer, "各設問のキーと種別")
        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.pack(fill="x", anchor="w", pady=(2, 0))
        ctk.CTkLabel(hdr, text="設問キー", width=100, text_color=TEXT_3,
                     font=jp(11), anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="種別", text_color=TEXT_3,
                     font=jp(11), anchor="w").pack(side="left", padx=(16, 0))

        self.rows_frame = ctk.CTkFrame(outer, fg_color="transparent")
        self.rows_frame.pack(fill="x", anchor="w")
        self._build_question_rows()

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=TEXT_1,
                     font=jp(12, "bold"), anchor="w").pack(anchor="w", pady=(6, 0))

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(fill="x", pady=8)

    def _build_question_rows(self):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        self.question_rows.clear()
        try:
            n = max(1, min(int(self.num_var.get()), 10))
        except ValueError:
            n = 1
        for _ in range(n):
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
            row.pack(fill="x", pady=3, anchor="w")
            key_var = tk.StringVar()
            ctk.CTkEntry(row, textvariable=key_var, width=100, height=34,
                         fg_color=BG_CARD2, border_color=BORDER, border_width=1,
                         text_color=TEXT_1, font=jp(12)).pack(side="left")
            type_var = tk.StringVar(value="記述式")
            for val in ["記述式", "マーク式"]:
                ctk.CTkRadioButton(row, text=val, variable=type_var, value=val,
                                   fg_color=BLUE, hover_color=BLUE_HOVER,
                                   text_color=TEXT_2, font=jp(12),
                                   border_color=TEXT_3).pack(side="left", padx=(16, 0))
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
        self.root.quit()


# ============================================================
# 座標取得ウィンドウ
# ============================================================
class CoordinatePicker:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.master_id = config["master_id"]

        self.root.title(f"座標取得ツール — {self.master_id}")
        self.root.configure(bg=BG_DARK)

        # まず大きめに開いてからzoomed
        self.root.geometry("1400x900")
        self.root.update()
        try:
            self.root.state("zoomed")
        except Exception:
            pass

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
        self.root.after(400, self._load_pdf)

    def _build_steps(self):
        steps = [
            ("合計点欄をドラッグしてください", "total_score"),
            ("採点者名欄をドラッグしてください", "grader_name"),
        ]
        for key, qtype in self.config["questions"].items():
            if qtype == "記述式":
                steps.append((f"設問 {key} の小計欄 (score) をドラッグしてください", f"q:{key}:score"))
                steps.append((f"設問 {key} のテキスト欄 (text) をドラッグしてください", f"q:{key}:text"))
            else:
                steps.append((f"設問 {key} の配点テキスト欄 (score) をドラッグしてください", f"q:{key}:score"))
        steps.append(("コメント欄 (comment_box) をドラッグしてください", "comment_box"))
        if self.config["score_field_2"]:
            steps.append(("2枚目の得点欄 (score_field_2) をドラッグしてください", "score_field_2"))
        return steps
    
    def _build_ui(self):
        # ── ガイドバー（上部・高さ72px）──
        guide_bar = tk.Frame(self.root, bg=BG_CARD, height=72)
        guide_bar.pack(fill="x", side="top")
        guide_bar.pack_propagate(False)

        # 左側：STEPバッジ＋ガイドテキスト
        left_frame = tk.Frame(guide_bar, bg=BG_CARD)
        left_frame.pack(side="left", padx=20, pady=14)

        self.step_badge = tk.Label(
            left_frame, text="STEP 1", bg=BLUE, fg="white",
            font=(FONT_JP, 13, "bold"), padx=16, pady=6, relief="flat"
        )
        self.step_badge.pack(side="left")

        self.guide_label = tk.Label(
            left_frame, text="", bg=BG_CARD,
            fg=TEXT_1, font=(FONT_JP, 16, "bold"), anchor="w"
        )
        self.guide_label.pack(side="left", padx=(16, 0))

        # 右側：ステップカウンター＋ボタン
        right_frame = tk.Frame(guide_bar, bg=BG_CARD)
        right_frame.pack(side="right", padx=20, pady=14)

        self.step_counter = tk.Label(
            right_frame, text="", bg=BG_CARD,
            fg=TEXT_3, font=(FONT_JP, 13), anchor="e"
        )
        self.step_counter.pack(side="left", padx=(0, 16))

        self._bar_button(right_frame, "やり直し", RED, RED_HOVER, self._redo_step).pack(side="left", padx=6)
        self._bar_button(right_frame, "スキップ", GRAY_BTN, GRAY_HOVER, self._skip_step).pack(side="left", padx=6)

        # ── メインエリア ──
        main_frame = tk.Frame(self.root, bg=BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        self.canvas = tk.Canvas(main_frame, cursor="cross", bg="#1a1f2e", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas.yview,
                            bg=BG_CARD, troughcolor=BG_DARK)
        vbar.grid(row=0, column=1, sticky="ns")
        hbar = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview,
                            bg=BG_CARD, troughcolor=BG_DARK)
        hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # ── ナビバー（下部・中央配置）──
        nav_bar = tk.Frame(self.root, bg=BG_CARD, height=64)
        nav_bar.pack(fill="x", side=tk.BOTTOM)
        nav_bar.pack_propagate(False)

        nav_center = tk.Frame(nav_bar, bg=BG_CARD)
        nav_center.place(relx=0.5, rely=0.5, anchor="center")

        self._nav_button(nav_center, "◀  前のページ", self._prev_page).pack(side="left", padx=10)
        self.page_label = tk.Label(
            nav_center, text="ページ: - / -", bg=BG_CARD,
            fg=TEXT_2, font=(FONT_JP, 13), width=14, anchor="center"
        )
        self.page_label.pack(side="left", padx=20)
        self._nav_button(nav_center, "次のページ  ▶", self._next_page).pack(side="left", padx=10)

        # バインド
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self._update_guide()

    def _bar_button(self, parent, text, bg, hover, cmd):
        btn = tk.Button(
            parent, text=text, bg=bg, fg="white",
            font=(FONT_JP, 13), relief="flat",
            padx=20, pady=10, cursor="hand2",
            activebackground=hover, activeforeground="white", bd=0, command=cmd
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _nav_button(self, parent, text, cmd):
        btn = tk.Button(
            parent, text=text, bg=GRAY_BTN, fg=TEXT_2,
            font=(FONT_JP, 13), relief="flat",
            padx=24, pady=10, cursor="hand2",
            activebackground=GRAY_HOVER, activeforeground=TEXT_1,
            bd=0, command=cmd
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=GRAY_HOVER, fg=TEXT_1))
        btn.bind("<Leave>", lambda e: btn.config(bg=GRAY_BTN, fg=TEXT_2))
        return btn

    def _update_guide(self):
        if self.step_index < len(self.steps):
            label, _ = self.steps[self.step_index]
            self.guide_label.config(text=label)
            self.step_counter.config(text=f"ステップ {self.step_index + 1} / {len(self.steps)}")
            self.step_badge.config(text=f"STEP {self.step_index + 1}", bg=BLUE)
        else:
            self.guide_label.config(text="全ステップ完了！保存しています...")
            self.step_counter.config(text="")
            self.step_badge.config(text="DONE", bg="#16a34a")

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
        cw = self.canvas.winfo_width() or 1200
        ch = self.canvas.winfo_height() or 800

        zoom_x = (cw * 0.92) / page.rect.width
        zoom_y = (ch * 0.92) / page.rect.height
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
            outline="#ef4444", width=2, dash=(4, 2))

    def _on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y,
                           self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def _on_release(self, event):
        if self.step_index >= len(self.steps):
            return
        if self.start_x is None or self.start_y is None:  # ← 追加
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
    setup_root = ctk.CTk()
    setup = SetupDialog(setup_root)
    setup_root.mainloop()

    result = setup.result
    setup_root.destroy()

    if not result:
        exit()

    picker_root = ctk.CTk()
    CoordinatePicker(picker_root, result)
    picker_root.mainloop()