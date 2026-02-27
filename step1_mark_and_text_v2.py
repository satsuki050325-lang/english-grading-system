
import os
import glob
import time
import sys
import json
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageStat  # 変更点①: ImageStatを追加
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

# ============================
# 設定エリア
# ============================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
INPUT_DIR = "./inputs"
OUTPUT_DIR = "./step1_texts"
MASTER_DB_DIR = "./masters"  # ★変更点: マスターDBのディレクトリ設定を追加
MODEL_NAME = "gemini-2.5-flash" 
# ============================

client = genai.Client(api_key=GOOGLE_API_KEY)

def print_progress_bar(iteration, total, prefix='', suffix='', length=30):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    if len(suffix) > 20: suffix = suffix[:17] + "..."
    print(f'Progress: {prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()

def call_gemini_safe(contents_list, response_mime_type="text/plain"):
    max_retries = 3
    retry_delay = 20
    normal_delay = 5 

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents_list,
                config=types.GenerateContentConfig(response_mime_type=response_mime_type)
            )
            time.sleep(normal_delay)
            return response.text

        except KeyboardInterrupt:
            print("\nユーザーによる中断を検知しました。終了します。")
            sys.exit(1)
        except Exception as e:
            print(f"\nエラー発生 (試行 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"⏳ {retry_delay}秒待機してリトライします...")
                time.sleep(retry_delay)
            else:
                return f"ERROR: {e}"
    return "ERROR: Max retries exceeded"

def pdf_to_images(pdf_path, dpi=300):
    """PDFの全ページを画像化してリストで返す"""
    doc = fitz.open(pdf_path)
    img_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        img_path = f"temp_{os.path.basename(pdf_path)}_p{page_num}.png"
        pix.save(img_path)
        
        # --- 【変更点②: 自動コントラスト調整ロジックの追加】 ---
        img = Image.open(img_path)
        # 画像をグレースケールに変換して明るさの平均値を計算
        gray_img = img.convert("L")
        stat = ImageStat.Stat(gray_img)
        mean_brightness = stat.mean[0]  # 0(真っ黒) 〜 255(真っ白)
        
        # 平均の明るさ（白っぽさ）に応じてコントラストの強調度合いを分岐
        if mean_brightness > 245:
            # かなり白っぽい（文字が非常に薄い）場合
            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(2.5)
            img_enhanced.save(img_path)
        elif mean_brightness > 230:
            # 少し白っぽい（文字が少し薄い）場合
            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(1.5)
            img_enhanced.save(img_path)
        # 230以下の場合は十分な濃さがあると判断し、上書き保存をスキップ（何もしない）
        # --------------------------------------------------------
        
        img_paths.append(img_path)
    doc.close()
    return img_paths

def crop_image(img_path, box):
    img = Image.open(img_path)
    width, height = img.size
    ymin, xmin, ymax, xmax = box
    
    if max(box) > 1.0:
        ymin = ymin / 1000.0
        xmin = xmin / 1000.0
        ymax = ymax / 1000.0
        xmax = xmax / 1000.0
    
    left = int(xmin * width)
    upper = int(ymin * height)
    right = int(xmax * width)
    lower = int(ymax * height)
    
    left, right = min(left, right), max(left, right)
    upper, lower = min(upper, lower), max(upper, lower)
    
    padding = 20
    left = max(0, left - padding)
    upper = max(0, upper - padding)
    right = min(width, right + padding)
    lower = min(height, lower + padding)
    
    cropped_img = img.crop((left, upper, right, lower))
    cropped_path = f"cropped_{os.path.basename(img_path)}"
    cropped_img.save(cropped_path)
    return cropped_path

def find_mark_sheet_box(upload_file):
    prompt = """
    この画像の中に、丸（楕円）を黒く塗りつぶす形式の「マークシート解答欄の表」はありますか？
    ある場合は、その表全体を囲む座標（Bounding Box）をJSON形式で出力してください。
    ない場合は、空のリストを返してください。

    出力形式:
    [
      {"box_2d": [ymin, xmin, ymax, xmax], "label": "mark_sheet"}
    ]
    """
    result = call_gemini_safe([upload_file, prompt], response_mime_type="application/json")
    if result and "ERROR" not in result:
        try:
            data = json.loads(result)
            if data and len(data) > 0 and "box_2d" in data[0]:
                return data[0]["box_2d"]
        except:
            pass
    return None

def extract_text_with_ai(pdf_path, master_ids_str):  # ★変更点: 引数に master_ids_str を追加
    filename = os.path.basename(pdf_path)
    img_paths = []
    cropped_img_path = None
    uploaded_pages = []
    
    try:
        # 1. 全ページを画像化
        img_paths = pdf_to_images(pdf_path, dpi=300)
        
        # 2. 全ページをGeminiにアップロード
        for p in img_paths:
            uf = client.files.upload(
                file=p,
                config=types.UploadFileConfig(mime_type="image/png")
            )
            while uf.state.name == "PROCESSING":
                time.sleep(1)
                uf = client.files.get(name=uf.name)
            uploaded_pages.append(uf)
            
        # --- 【タスク1: 記述式とヘッダーの読み取り（全ページ対象）】 ---
        # ★変更点: プロンプトをf-string化し、master_ids_str を動的に埋め込み
        prompt_text = f"""
        提供されたすべての画像から「生徒の答案（記述式）」をテキストデータ化してください。

        以下の【抽出要素①】〜【抽出要素③】をすべて必ず実行してください。

        【抽出要素①：対象問題の特定（完全一致ルールの厳守）】
        画像の上部にある年度や大問番号から、この答案が以下のどれに該当するかを判定し、
        テキストの 1行目 に必ず指定の「マスターID」をそのまま書き出してください。
        (選択肢以外の文字は1行目に絶対に含めないこと)

        [マスターIDの選択肢]
        {master_ids_str}

        ※厳守：上記リストにある指定のID以外の文字列は、いかなる理由があっても1行目に出力してはならない。もし画像が不鮮明でどれにも該当しないと判断した場合は、推測せずに必ず「UNKNOWN」と出力せよ。

        【抽出要素②：生徒番号の抽出】
        答案用紙の上部や隅に書かれている「生徒番号（8桁の数字など）」を読み取り、
        テキストの 2行目 に出力してください。
        例: 55615210

        【抽出要素③：記述式の解答文章（超重要）】
        画像内に手書きで書かれている「日本語や英語の文章（記述式の解答）」をすべて漏らさず書き起こしてください。
        (A)、(B)、(C)などの設問番号を先頭につけ、生徒が書いた文字をそのままテキスト化してください。

        【注意事項】
        ・マークシート部分（丸が並んでいる箇所）は完全に無視して構いません（別途処理します）。
        ・余計な挨拶や解説は不要です。マスターID、生徒番号、記述式解答のみを順番に出力してください。
        """
        # アップロードした全ページを渡す
        result_text = call_gemini_safe(uploaded_pages + [prompt_text])

        # --- 【タスク2: マークシートの読み取り（該当ページのみ切り抜き）】 ---
        result_marks = ""
        for i, uf in enumerate(uploaded_pages):
            box = find_mark_sheet_box(uf)
            if box:
                # マークシートが見つかったページ(i)の画像を切り抜く
                cropped_img_path = crop_image(img_paths[i], box)
                upload_cropped = client.files.upload(
                    file=cropped_img_path,
                    config=types.UploadFileConfig(mime_type="image/png")
                )
                while upload_cropped.state.name == "PROCESSING":
                    time.sleep(1)
                    upload_cropped = client.files.get(name=upload_cropped.name)
                    
                prompt_marks = """
                提供されたマークシートの拡大画像から事実だけを読み取ってください。

                【最重要ルール：マークシートの読み取り】
                マークシートの選択肢は「a」から「i」や「j」まで（9〜10個など）多く並んでいる場合があります。
                以下の手順で、絶対に推測せず、画像にある事実だけを読み取ってください。

                手順1: 左側にある設問番号（27, 28...）を見つける。
                手順2: その行を横に見て、中が鉛筆で塗られている（一番色が濃い）丸を1つ特定する。
                手順3: その塗られた丸の「すぐそば（中や横など）」に印字されている小さなアルファベットの文字を直接読み取って記号とする。
                手順4: もし文字が潰れて読めない場合は、その丸が左から何番目にあるかを数えてアルファベットに変換する。（1番目=a, 2番目=b, 3番目=c, 4番目=d, 5番目=e, 6番目=f, 7番目=g...）

                出力形式: (問題番号) 選択した記号
                例: (27) a, (28) c

                【注意事項】
                ・薄い鉛筆でも、他の丸より色が濃ければそれを選択してください。
                ・すべての行が同じ記号になることはあり得ません。前の問題に引きずられず、1行ずつ独立して観察してください。
                ・余計な挨拶は不要です。
                """
                result_marks = call_gemini_safe([upload_cropped, prompt_marks])
                break  # マークシートを1つ見つけて処理したらループを抜ける

        # 2つの結果を合体させて返す
        final_text = result_text
        if result_marks and "ERROR" not in result_marks:
            final_text += "\n\n" + result_marks
            
        return filename, final_text

    except Exception as e:
        return filename, f"ERROR: {e}"
        
    finally:
        # ゴミファイルの削除
        for p in img_paths:
            if os.path.exists(p):
                os.remove(p)
        if cropped_img_path and os.path.exists(cropped_img_path):
            os.remove(cropped_img_path)

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # ★変更点: マスターDBフォルダからJSONを読み込み、IDのリストを動的に生成する
    master_ids_str = ""
    if os.path.exists(MASTER_DB_DIR):
        ids = []
        for path in glob.glob(os.path.join(MASTER_DB_DIR, "*.json")):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "meta" in data and "id" in data["meta"]:
                    ids.append(f"- {data['meta']['id']}")
            except Exception:
                pass
        if ids:
            master_ids_str = "\n".join(ids)
            
    if not master_ids_str:
        print("⚠️ マスターIDが取得できませんでした。")
        print("   → ./masters/ フォルダにJSONファイルが存在するか確認してください。")
        print("   → JSONには {'meta': {'id': '...'}} の形式でIDが含まれている必要があります。")
        print("   → ファイルを追加後、再実行してください。")
        return
    
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    total_files = len(pdf_files)
    
    if not pdf_files:
        print("PDFが見つかりません。")
        return

    print(f"📄 {total_files}件のファイルを処理します（モデル: {MODEL_NAME}）...")
    print_progress_bar(0, total_files, prefix='Progress:', suffix='Start', length=30)
    
    start_time = time.time()

    for i, pdf_path in enumerate(pdf_files):
        # ★変更点: 動的に生成した master_ids_str を関数に渡す
        filename, text = extract_text_with_ai(pdf_path, master_ids_str)
        
        base_name = filename.replace('.pdf', '')
        txt_path = os.path.join(OUTPUT_DIR, f"{base_name}_draft.txt")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        print_progress_bar(i + 1, total_files, prefix='Progress:', suffix=f'Done ({base_name})', length=30)

    end_time = time.time()
    print(f"\n🎉 全処理完了！ 所要時間: {end_time - start_time:.1f}秒")

if __name__ == "__main__":
    main()