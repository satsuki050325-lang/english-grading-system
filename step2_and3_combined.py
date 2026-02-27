"""
Step2 + Step3 統合スクリプト
JSONファイルをディスクに書かず、メモリ上でStep3に渡す
"""
import json
import os
import glob
import time
import sys
import anthropic
import fitz
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ============================
# 設定エリア
# ============================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL_NAME = "claude-sonnet-4-5-20250929"
COORD_DB_DIR = "./coord_db"
INPUT_TEXT_DIR = "./step1_texts"
MASTER_DB_DIR = "./masters"
RUBRIC_TXT_DIR = "./rubric_txts"
INPUT_PDF_DIR = "./inputs"
OUTPUT_DIR = "./step3_final"
RED = (1, 0, 0)

# config.jsonから採点者名を読み込む
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
def _get_grader_name() -> str:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("grader_name", "採点者")
    except Exception:
        return "採点者"
# ============================

COORD_DB_DIR = "./coord_db"

def load_coord(master_id):
    path = os.path.join(COORD_DB_DIR, f"{master_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
BETAS = ["prompt-caching-2024-07-31"]

SYSTEM_PROMPT = """あなたは東京大学受験専門の予備校講師です。
生徒の解答を採点し、JSONのみを出力してください。前置きや挨拶は一切不要です。

## 採点方針
- 点数計算はJSONの配点・採点要素に厳密に従う
- 解説TXTが提供されている場合、添削コメントの表現・ニュアンスの参考にする（点数計算には使わない）
- grading_processに計算式を先に書いてからscoreを確定する（例: "15 - 3 - 2 = 10"）
- 減点数の合計・score・correctionsの件数は必ず一致させる

## correctionsの記述ルール（最重要）
- 必ず全ての減点理由を個別に・具体的に記述すること。省略・まとめ禁止
- 箇条書き禁止。各項目は必ず文章で記述すること
- 語数・字数不足の場合: 「①解答がN語（字）で、指定のM〜L語（字）に対して不足しています。(-k)」の形式で記述
- スペルミス・語形ミスの場合: 誤りと正しい形を両方示すこと（例:「「inconvinient」のスペルは「inconvenient」が正しいです。(-1)」）
- 文法ミスの場合: 誤りの理由と正しい形を示すこと
- 内容の不足・誤りの場合: 何が欠けているか・なぜ必要かを具体的に示すこと
- 満点の場合は、解説にあるような点を取るために必要な要点を提示し、「～を理解して解くことが出来ています。」のようにつなげて褒めるか、あるいはさらに良くするためのポイントを優しく示すこと。細かすぎる改善点を述べるくらいなら、前者を優先すること
- 減点表記は末尾に(-1)(-2)のように数字のみで記載。「点」は不要
- 生徒解答の引用は「」で囲む
- 未回答: score=0、corrections=["解答がないため0点です。どのように考えれば解けるかのヒント: （具体的なアドバイス）"]
- correctionsの番号は、答案中の出現順（上から下、左から右）に振ること
- 減点の累計が配点を超える場合: 0点になった時点で「以下、配点を超える減点は行いません」と記載し、以降の指摘には(-N)表記を付けない
- 採点基準通りの減点が配点を超えてしまう場合（例: 4点満点に-3が2つ）: 最後の減点を調整し「(-3, 区分内上限のため-1)」のように記載する



## 出力形式
- 文体: です・ます調
- 禁止表現: 「〜してください」「高く評価できます」「評価できます」「許容範囲」。これらは絶対に使わないこと
- 推奨表現: 「〜しましょう」「〜できると良いですね」「よくできています」「素晴らしいです」「〜することができています」
- corrections の番号は、答案中の出現順（上から下、左から右）に振ること

## markの判定
- score == max → "circle"
- 0 < score < max → "triangle"
- score == 0 → "check"

## マーク式問題
- 部分点なし（正解=満点、不正解=0点）
- sub_resultsに全小問の正誤を出力: {"27": "circle", "28": "check"}
- corrections=[]、details_textに内訳: "27~32 各1点 5/6\n合計 5/12"

## comment_partsのルール
- praise: 解答内容への具体的・客観的な評価。「〜することができています」「よくできています」「素晴らしいです」の表現を使うこと。「頑張りが見られる」「高く評価できます」「評価できます」等の曖昧・上目線表現は禁止
- advice: 次回への具体的な改善点。「〜しましょう」「〜できると良いですね」の表現を使うこと。「〜してください」は禁止
- closing: 固定文「これからも頑張ってください。応援しています。」
- 満点の場合も必ずpraiseとadviceを記述すること。praiseでは具体的に良かった点を、adviceでは「さらに良くするためのポイント」を記述すること
- マーク式・未回答への言及禁止

## 出力JSONスキーマ
{"student_id":"","questions":{"設問キー":{"max":0,"grading_process":"","score":0,"mark":"","corrections":[],"details_text":"","sub_results":{}}},"comment_parts":{"praise":"","advice":"","closing":""}}"""



def print_progress_bar(iteration, total, prefix='', suffix='', length=30):
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled = int(length * iteration // total)
    bar = '█' * filled + '-' * (length - filled)
    suffix = suffix[:17] + "..." if len(suffix) > 20 else suffix
    print(f'Progress: {prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
        
        
def load_coord_db(db_dir):
    coord_db = {}
    if not os.path.exists(db_dir):
        return coord_db
    for path in glob.glob(os.path.join(db_dir, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mid = data.get("master_id")
            if mid:
                coord_db[mid] = data
        except Exception as e:
            print(f"⚠️ coord_dbロードエラー ({path}): {e}")
    return coord_db


def load_all_masters(db_dir):
    masters = []
    for path in glob.glob(os.path.join(db_dir, "*.json")):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "meta" in data and "id" in data["meta"]:
                masters.append(data)
        except Exception as e:
            print(f"⚠️ JSONロードエラー ({path}): {e}")
    return masters


def find_matching_master(student_text, masters):
    lines = student_text.strip().split('\n')
    if not lines:
        return None
    extracted_id = lines[0].strip()
    for data in masters:
        if data["meta"]["id"] == extracted_id:
            return data
    return None


def load_rubric_txt(master_id):
    if not os.path.exists(RUBRIC_TXT_DIR):
        return None
    matches = glob.glob(os.path.join(RUBRIC_TXT_DIR, f"*{master_id}*.txt"))
    if not matches:
        return None
    with open(matches[0], "r", encoding="utf-8") as f:
        return f.read()


def build_content(master_data, student_text, rubric_txt=None):
    content = []
    if rubric_txt:
        content.append({
            "type": "text",
            "text": f"【解説・解答例・添削例】\n{rubric_txt}",
            "cache_control": {"type": "ephemeral"}
        })
    criteria_text = (
        f"【共通採点基準】\n{json.dumps(master_data.get('common_criteria', []), ensure_ascii=False)}\n\n"
        f"【問題データ（配点・採点要素）】\n{json.dumps(master_data['sub_questions'], ensure_ascii=False)}"
    )
    content.append({"type": "text", "text": criteria_text, "cache_control": {"type": "ephemeral"}})
    content.append({"type": "text", "text": f"\n【生徒の解答】\n{student_text}"})
    return content


def extract_json_from_response(raw_text):
    raw_text = raw_text.strip()
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        return raw_text[start:end]
    return raw_text


def grade_answer(student_text, master_data, rubric_txt=None):
    """Step2: 採点してdictを返す（ファイルに書かない）"""
    content = build_content(master_data, student_text, rubric_txt)
    for attempt in range(3):
        try:
            response = client.beta.messages.create(
                model=MODEL_NAME,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                betas=BETAS
            )
            time.sleep(1)
            raw_text = response.content[0].text
            json_str = extract_json_from_response(raw_text)
            print("=== API RESPONSE ===")
            print(json_str[:500])
            
            return json.loads(json_str)
        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"\n⚠️ レート制限 (試行{attempt+1}/3): {wait}秒待機...")
            time.sleep(wait)
        except anthropic.APIError as e:
            print(f"\n⚠️ APIエラー (試行{attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(15)
        except json.JSONDecodeError as e:
            print(f"\n⚠️ JSONパース失敗 (試行{attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
        except Exception as e:
            print(f"\n⚠️ 予期しないエラー (試行{attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(15)
    return {"error": "Max retries exceeded"}


def add_editable_text(page, rect_coords, text, size=10, align=0):
    if not text:
        return
    x0, y0, x1, y1 = rect_coords
    dx = page.cropbox.x0
    dy = page.cropbox.y0
    correct_rect = fitz.Rect(x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    annot = page.add_freetext_annot(
        correct_rect, str(text), fontsize=size, fontname="Helv", text_color=RED, align=align
    )
    annot.update()


def write_to_pdf(data, master_id, pdf_path, coord_db):
    """Step3: dictを受け取ってPDFに書き込む"""
    coords = load_coord(master_id)
    if not coords:
        print(f"⚠️ COORD_DBに {master_id} がありません")
        return False

    doc = fitz.open(pdf_path)

    # 採点者名
    if "grader_name" in coords:
        add_editable_text(doc[coords["grader_name"][0]], coords["grader_name"][1:], _get_grader_name(), size=10, align=1)

    # 合計点
    total_score, total_max = 0, 0
    questions = data.get("questions", {})
    for q_val in questions.values():
        total_score += q_val.get("score", 0)
        total_max += int(q_val.get("max", 0))
    score_str = f"{total_score}／{total_max}"

    if "total_score" in coords:
        add_editable_text(doc[coords["total_score"][0]], coords["total_score"][1:], score_str, size=10, align=1)
    if "score_field_2" in coords:
        add_editable_text(doc[coords["score_field_2"][0]], coords["score_field_2"][1:], score_str, size=10, align=1)

    # 設問
    q_coords_map = coords.get("questions", {})
    for q_key, q_val in questions.items():
        if q_key not in q_coords_map:
            continue
        c = q_coords_map[q_key]
        text_content = q_val.get("details_text", "")
        if not text_content and "corrections" in q_val and q_val["corrections"]:
            text_content = "\n".join(q_val["corrections"])
        if "sub_results" in q_val and q_val["sub_results"]:
            kanpe_list = [f"{k}:{'〇' if v == 'circle' else '✖'}" for k, v in q_val["sub_results"].items()]
            text_content = f"{text_content}\n【確認用】{' '.join(kanpe_list)}"
        if "text" in c and c["text"] is not None and text_content:
            add_editable_text(doc[c["text"][0]], c["text"][1:], text_content, size=10, align=0)
        if "score" in c:
            s_str = f"{q_val.get('score',0)}／{q_val.get('max',0)}"
            add_editable_text(doc[c["score"][0]], c["score"][1:], s_str, size=10, align=1)

    # コメント
    if "comment_box" in coords:
        parts = data.get("comment_parts", {})
        full_comment = f"【コメント】\n{parts.get('praise','')}\n{parts.get('advice','')}\n{parts.get('closing','')}"
        add_editable_text(doc[coords["comment_box"][0]], coords["comment_box"][1:], full_comment, size=10, align=0)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
    doc.save(out_path)
    return True


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    coord_db = load_coord_db(COORD_DB_DIR)
    if not coord_db:
        print("⚠️ coord_dbが空です。coordinate_picker.pyで座標を取得してください。")
        
    masters_list = load_all_masters(MASTER_DB_DIR)
    if not masters_list:
        print("❌ マスターデータが見つかりません。./masters/ を確認してください。")
        return

    text_files = glob.glob(os.path.join(INPUT_TEXT_DIR, "*_draft.txt"))
    if not text_files:
        print("❌ step1のテキストファイルが見つかりません。")
        return

    txt_count = len(glob.glob(os.path.join(RUBRIC_TXT_DIR, "*.txt"))) if os.path.exists(RUBRIC_TXT_DIR) else 0
    print(f"📚 解説TXT: {txt_count}件 | 採点基準JSON: {len(masters_list)}件")
    print(f"🚀 {len(text_files)}件の答案を処理します（モデル: {MODEL_NAME}）...")
    print_progress_bar(0, len(text_files), prefix='Progress:', suffix='Start', length=30)

    start_time = time.time()
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, txt_path in enumerate(text_files):
        filename = os.path.basename(txt_path)
        base_name = filename.replace("_draft.txt", "")

        with open(txt_path, 'r', encoding='utf-8') as f:
            student_text = f.read()

        matched_master = find_matching_master(student_text, masters_list)
        # find_matching_master が None だった場合
        if not matched_master:
            first_line = student_text.strip().split('\n')[0].strip() if student_text.strip() else "(空)"
            available_ids = [m['meta']['id'] for m in masters_list]
            skip_count += 1
            print(f"\n⚠️ スキップ: {filename}")
            print(f"   → 1行目: \"{first_line}\"")
            print(f"   → 登録済みマスターID: {', '.join(available_ids)}")
            print_progress_bar(i + 1, len(text_files), prefix='Progress:', suffix=f'Skip ({filename})', length=30)
            continue
            

        master_id = matched_master['meta']['id']
        rubric_txt = load_rubric_txt(master_id)

        # Step2: 採点（メモリ上のdictとして受け取る）
        result_data = grade_answer(student_text, matched_master, rubric_txt)

        if "error" in result_data:
            error_count += 1
            print_progress_bar(i + 1, len(text_files), prefix='Progress:', suffix=f'Error ({filename})', length=30)
            continue

        result_data["master_id"] = master_id

        # Step3: PDFに直接書き込む
        pdf_path = os.path.join(INPUT_PDF_DIR, f"{base_name}.pdf")
        if not os.path.exists(pdf_path):
            print(f"\n⚠️ PDFが見つかりません: {pdf_path}")
            error_count += 1
        else:
            ok = write_to_pdf(result_data, master_id, pdf_path, coord_db)
            if ok:
                success_count += 1
            else:
                error_count += 1

        print_progress_bar(i + 1, len(text_files), prefix='Progress:', suffix=f'Done ({base_name})', length=30)

        elapsed = time.time() - start_time
        print(f"\n✨ 完了！ 成功:{success_count}件 スキップ:{skip_count}件 エラー:{error_count}件 | 所要時間: {elapsed:.1f}秒")
        
        if success_count == 0:
            print(f"❌ 成功件数が0件のため、ファイルの移動を行いません。スキップ理由を確認してください。")
            sys.exit(1)
            
            
if __name__ == "__main__":
    main()