import webview
import sys
import os
import glob
import zipfile
import subprocess
import json
import base64
import shutil
from pathlib import Path
from datetime import datetime
import fitz

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_DEFAULT_CONFIG = {
    "pdfxchange_path": "",
    "grader_name":     "採点者",
    "input_dir":       "./inputs",
    "text_dir":        "./step1_texts",
    "output_dir":      "./step3_final",
    "done_dir":        "./done",
    "step23_script":   "step23_combined.py",
}

def load_config() -> dict:
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in _DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    return dict(_DEFAULT_CONFIG)

CFG = load_config()

PDFXCHANGE_CANDIDATES = [
    CFG.get("pdfxchange_path", ""),
    r"C:\Program Files\Tracker Software\PDF Editor\PDFXEdit.exe",
    r"C:\Program Files (x86)\Tracker Software\PDF Editor\PDFXEdit.exe",
    r"C:\Program Files\PDF-XChange Editor\PDFXEdit.exe",
    r"C:\Program Files (x86)\PDF-XChange Editor\PDFXEdit.exe",
]

def find_pdfxchange():
    for path in PDFXCHANGE_CANDIDATES:
        if path and os.path.exists(path):
            return path
    return None

class Api:
    def __init__(self):
        self._window = None
        self._current_proc = None
        self._cancelled = False

    def set_window(self, window):
        self._window = window

    def _log(self, msg: str):
        skip_patterns = ["./inputs", "./step1_texts", "./step3_final", "./done", "./masters", "./rubric_txts", "\\inputs", "\\step1_texts"]
        for pat in skip_patterns:
            if pat in msg:
                return
        
        # \r を含む行はプログレスバー → 専用関数で最後の行を上書き
        if '\r' in msg:
            clean = msg.replace('\r', '').strip()
            if clean:
                print(f"Progress: {clean}")
                try:
                    self._window.evaluate_js(f'window.updateProgress({json.dumps(clean)})')
                except Exception:
                    pass
        else:
            print(f"Log: {msg}")
            try:
                self._window.evaluate_js(f'window.updateLog({json.dumps(msg)})')
            except Exception:
                pass
    
    def _run_realtime(self, script_path: str, label: str) -> bool:
        try:
            self._log(f"▶ {label} 開始...")
            self._cancelled = False
            proc = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._current_proc = proc
            for line in iter(proc.stdout.readline, ""):
                if self._cancelled:
                    break
                line = line.rstrip("\n").rstrip("\r")
                if line.strip():
                    self._log(line.strip())
            proc.stdout.close()
            if self._cancelled:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                self._current_proc = None
                self._log(f"⛔ {label} をキャンセルしました")
                return False
            proc.wait()
            self._current_proc = None
            if proc.returncode != 0:
                stderr = proc.stderr.read()
                if stderr:
                    self._log(f"❌ {label} 失敗: {stderr[:300]}")
                return False
            self._log(f"✅ {label} 完了")
            return True
        except Exception as e:
            self._current_proc = None
            self._log(f"❌ {e}")
        return False            
        
        
    def run_coordinate_picker(self):
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "coordinate_picker.py")
        if not os.path.exists(path):
            self._log("❌ coordinate_picker.py が見つかりません")
            return False
        try:
            subprocess.Popen([sys.executable, path])
            self._log("🗺️ 座標取得ツールを起動しました")
            return True
        except Exception as e:
            self._log(f"❌ 座標取得ツールの起動に失敗: {e}")
            return False

    # ── 設定 ──────────────────────────────────────────

    def get_settings(self):
        """設定値を返す"""
        return {
            "grader_name": CFG.get("grader_name", "採点者"),
            "pdfxchange_path": CFG.get("pdfxchange_path", ""),
        }

    def save_settings(self, grader_name: str, pdfxchange_path: str = ""):
        """設定を保存する"""
        CFG["grader_name"] = grader_name.strip() or "採点者"
        if pdfxchange_path:
            CFG["pdfxchange_path"] = pdfxchange_path.strip()
        try:
            with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(CFG, f, ensure_ascii=False, indent=2)
            self._log(f"⚙️ 設定を保存しました（採点者名: {CFG['grader_name']}）")
            return True
        except Exception as e:
            self._log(f"❌ 設定保存エラー: {e}")
            return False

    # ── ファイルダイアログ ──────────────────────────────
    
    def open_file_dialog(self):
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('PDFまたはZIPファイル (*.pdf;*.zip)',)
            )
            if result and len(result) > 0:
                return result[0]
            return None
        except Exception as e:
            self._log(f"❌ ファイル選択エラー: {e}")
            return None


    def copy_pdf(self, pdf_path):
        if not pdf_path or not os.path.exists(pdf_path):
            return False
        os.makedirs(CFG["input_dir"], exist_ok=True)
        try:
            dst = os.path.join(CFG["input_dir"], os.path.basename(pdf_path))
            shutil.copy2(pdf_path, dst)
            self._log(f"📄 PDF取り込み完了: {os.path.basename(pdf_path)}")
            return True
        except Exception as e:
            self._log(f"❌ PDFコピーエラー: {e}")
            return False
    
    
    def open_output_dir(self):
        try:
            output_dir = os.path.abspath(CFG["output_dir"])
            os.makedirs(output_dir, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", output_dir])
            else:
                subprocess.Popen(["xdg-open", output_dir])
            return True
        except Exception as e:
            self._log(f"❌ フォルダを開けませんでした: {e}")
            return False

    def open_with_pdfxchange(self):
        output_dir = os.path.abspath(CFG["output_dir"])
        pdfs = sorted(glob.glob(os.path.join(output_dir, "*.pdf")))
        if not pdfs:
            self._log("❌ 出力フォルダにPDFが見つかりません")
            return False
        editor_path = find_pdfxchange()
        if not editor_path:
            self._log("❌ PDF XChange Editorが見つかりません。設定からパスを登録してください。")
            return False
        try:
            subprocess.Popen([editor_path] + pdfs)
            self._log(f"✅ PDF XChange Editorで {len(pdfs)}件を開きました")
            return True
        except Exception as e:
            self._log(f"❌ Editorを開けませんでした: {e}")
            return False

    # ── ペア取得 ───────────────────────────────────────

    def get_pairs(self):
        """inputsのPDF + step1_textsのtxtをペアリング"""
        pairs = []
        d = CFG["input_dir"]
        if not os.path.isdir(d):
            return pairs
        for pdf in sorted(glob.glob(os.path.join(d, "*.pdf"))):
            base = os.path.splitext(os.path.basename(pdf))[0]
            txt = os.path.join(CFG["text_dir"], f"{base}_draft.txt")
            pairs.append({"pdf": pdf, "txt": txt, "filename": os.path.basename(pdf)})
        return pairs

    def get_done_dates(self):
        done_dir = CFG["done_dir"]
        if not os.path.isdir(done_dir):
            return []
        dates = []
        for entry in sorted(os.listdir(done_dir), reverse=True):
            full_path = os.path.join(done_dir, entry)
            if os.path.isdir(full_path) and len(entry) == 8 and entry.isdigit():
                pdfs = glob.glob(os.path.join(full_path, "*.pdf"))
                if pdfs:
                    formatted = f"{entry[:4]}/{entry[4:6]}/{entry[6:]}"
                    dates.append({"key": entry, "label": formatted, "count": len(pdfs)})
        return dates

    def restore_from_done(self, date_str: str):
        """
        done/YYYYMMDD/ のPDFとtxtをinputs/とstep1_texts/にコピーして
        通常フローと同じ状態にする。既存ファイルは上書き。
        """
        folder = os.path.join(CFG["done_dir"], date_str)
        if not os.path.isdir(folder):
            self._log(f"❌ フォルダが見つかりません: done/{date_str}/")
            return False

        os.makedirs(CFG["input_dir"], exist_ok=True)
        os.makedirs(CFG["text_dir"], exist_ok=True)

        copied_pdf = 0
        copied_txt = 0

        for pdf in glob.glob(os.path.join(folder, "*.pdf")):
            dst = os.path.join(CFG["input_dir"], os.path.basename(pdf))
            shutil.copy2(pdf, dst)
            copied_pdf += 1

        for txt in glob.glob(os.path.join(folder, "*_draft.txt")):
            dst = os.path.join(CFG["text_dir"], os.path.basename(txt))
            shutil.copy2(txt, dst)
            copied_txt += 1

        self._log(f"♻️ done/{date_str}/ から復元: PDF {copied_pdf}件, テキスト {copied_txt}件")
        return True

    # ── PDF・テキスト操作 ──────────────────────────────

    def get_pdf_image(self, pdf_path, page_idx=0, zoom=1.0):
        if not pdf_path or not os.path.exists(pdf_path):
            return {"error": "PDFが見つかりません"}
        doc = fitz.open(pdf_path)
        if page_idx >= len(doc):
            page_idx = len(doc) - 1
        page = doc[page_idx]
        mat = fitz.Matrix(zoom * 150 / 72, zoom * 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        b64_str = base64.b64encode(img_data).decode("utf-8")
        return {
            "image_data": f"data:image/png;base64,{b64_str}",
            "current_page": page_idx,
            "total_pages": len(doc)
        }

    def read_text(self, txt_path):
        if os.path.exists(txt_path):
            return Path(txt_path).read_text(encoding="utf-8")
        return "（テキストなし: Step1を実行してください）"

    def save_text(self, txt_path, content):
        if not txt_path:
            return False
        os.makedirs(os.path.dirname(txt_path) if os.path.dirname(txt_path) else ".", exist_ok=True)
        try:
            Path(txt_path).write_text(content, encoding="utf-8")
            filename = os.path.basename(txt_path).replace("_draft.txt", ".pdf")
            self._log(f"💾 {filename} を保存しました")
            return True
        except Exception as e:
            self._log(f"❌ 保存エラー: {e}")
            return False

    def extract_zip(self, zip_path):
        if not zip_path or not os.path.exists(zip_path):
            return False
        os.makedirs(CFG["input_dir"], exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path) as z:
                pdfs = [n for n in z.namelist() if n.lower().endswith(".pdf")]
                for name in pdfs:
                    z.extract(name, CFG["input_dir"])
                    src = os.path.join(CFG["input_dir"], name)
                    dst = os.path.join(CFG["input_dir"], os.path.basename(name))
                    if src != dst:
                        os.replace(src, dst)
            self._log(f"📦 ZIP展開完了: {len(pdfs)}件")
            return True
        except Exception as e:
            self._log(f"❌ ZIP展開エラー: {e}")
            return False

    # ── Step実行 ───────────────────────────────────────

    def run_step1(self):
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "step1_mark_and_text_v2.py")
        if not os.path.exists(path):
            self._log("❌ step1_mark_and_text_v2.py が見つかりません")
            return False
        # 前回の出力PDFをdoneに退避
        output_dir = os.path.abspath(CFG["output_dir"])
        pdfs = glob.glob(os.path.join(output_dir, "*.pdf"))
        if pdfs:
            date_str = datetime.now().strftime("%Y%m%d")
            archive_folder = os.path.join(CFG["done_dir"], f"{date_str}_output")
            os.makedirs(archive_folder, exist_ok=True)
            for pdf in pdfs:
                shutil.move(pdf, os.path.join(archive_folder, os.path.basename(pdf)))
            self._log(f"📁 前回の出力PDF {len(pdfs)}件を done/{date_str}_output/ に退避しました")
        return self._run_realtime(path, "Step1 テキスト抽出")

    def _move_files_to_done(self):
        date_str = datetime.now().strftime("%Y%m%d")
        done_folder = os.path.join(CFG["done_dir"], date_str)
        os.makedirs(done_folder, exist_ok=True)
        moved_pdf = 0
        moved_txt = 0
        for pdf in glob.glob(os.path.join(CFG["input_dir"], "*.pdf")):
            shutil.move(pdf, os.path.join(done_folder, os.path.basename(pdf)))
            moved_pdf += 1
        for txt in glob.glob(os.path.join(CFG["text_dir"], "*_draft.txt")):
            shutil.move(txt, os.path.join(done_folder, os.path.basename(txt)))
            moved_txt += 1
        self._log(f"📁 done/{date_str}/ に移動: PDF {moved_pdf}件, テキスト {moved_txt}件")

    def run_step23(self):
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, CFG["step23_script"])
        if not os.path.exists(path):
            self._log(f"❌ {CFG['step23_script']} が見つかりません")
            return False
        ok = self._run_realtime(path, "採点・PDF印字")
        if ok:
            self._move_files_to_done()
        return ok

    def cancel_step1(self):
        """Step1をキャンセルし、inputs/とstep1_texts/をクリーンアップ"""
        self._cancelled = True
        if self._current_proc:
            try:
                self._current_proc.terminate()
            except Exception:
                pass
        # inputs/ の全PDF削除
        for f in glob.glob(os.path.join(CFG["input_dir"], "*.pdf")):
            try:
                os.remove(f)
            except Exception:
                pass
        # step1_texts/ の全txt削除
        for f in glob.glob(os.path.join(CFG["text_dir"], "*_draft.txt")):
            try:
                os.remove(f)
            except Exception:
                pass
        self._log("🗑️ inputs/ と step1_texts/ をクリーンアップしました")
        return True

    def cancel_step23(self):
        """Step2&3をキャンセルし、step3_final/をクリーンアップ（inputs/step1_textsは残す）"""
        self._cancelled = True
        if self._current_proc:
            try:
                self._current_proc.terminate()
            except Exception:
                pass
        # step3_final/ の全PDF削除
        for f in glob.glob(os.path.join(CFG["output_dir"], "*.pdf")):
            try:
                os.remove(f)
            except Exception:
                pass
        self._log("🗑️ step3_final/ をクリーンアップしました")
        return True

if __name__ == '__main__':
    api = Api()
    window = webview.create_window(
        title='東大英語添削システム',
        url='http://localhost:5173',
        js_api=api,
        width=1280,
        height=800
    )
    api.set_window(window)
    print("バックエンド起動中...")
    webview.start(debug=True)