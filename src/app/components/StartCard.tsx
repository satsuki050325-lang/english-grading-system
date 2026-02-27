type Props = {
  onZip: () => void;
  onStep1: () => void;
  onResume: () => void;
};

declare global {
  interface Window {
    pywebview: {
      api: {
        extract_zip: (path: string) => Promise<boolean>;
        run_step1: () => Promise<boolean>;
        get_pairs: () => Promise<{ pdf: string; txt: string; filename: string }[]>;
        get_pdf_image: (path: string, page: number, zoom: number) => Promise<{ image_data: string } | { error: string }>;
        read_text: (path: string) => Promise<string>;
        save_text: (path: string, content: string) => Promise<boolean>;
      };
    };
  }
}

export function StartCard({ onZip, onStep1, onResume }: Props) {
  const handleZip = async () => {
    // pywebviewのファイル選択ダイアログは現状未対応のため
    // パスを直接入力する形にします（後で改善可能）
    const path = prompt("ZIPファイルのパスを入力してください");
    if (!path) return;
    const ok = await window.pywebview.api.extract_zip(path);
    if (ok) alert("ZIP展開完了！");
  };

  const handleStep1 = async () => {
    const ok = await window.pywebview.api.run_step1();
    if (ok) onStep1();
  };

  const handleResume = async () => {
    const pairs = await window.pywebview.api.get_pairs();
    if (pairs.length === 0) {
      alert("PDFが見つかりません。先にZIPを展開してください。");
      return;
    }
    onResume();
  };

  return (
    <div className="h-full flex items-center justify-center">
      <div
        className="w-[480px] rounded-2xl p-10 flex flex-col gap-4"
        style={{
          background: "linear-gradient(135deg, rgba(30, 35, 50, 0.85) 0%, rgba(20, 25, 40, 0.85) 100%)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        }}
      >
        <h1 className="text-gray-100 text-2xl font-bold text-center">作業を始めましょう</h1>
        <p className="text-gray-400 text-sm text-center">答案PDFを読み込んでOCR処理を開始してください</p>

        <div className="flex flex-col gap-3 mt-2">
          <button
            onClick={handleZip}
            className="w-full px-4 py-3 rounded-xl text-gray-200 text-sm flex items-center gap-3 transition-all hover:text-gray-100"
            style={{
              background: "linear-gradient(135deg, rgba(45, 50, 65, 0.8) 0%, rgba(30, 35, 50, 0.8) 100%)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span className="text-lg">📦</span>
            <span>① ZIPを展開してPDFを追加</span>
          </button>

          <button
            onClick={handleStep1}
            className="w-full px-4 py-4 rounded-xl text-white text-sm font-bold flex items-center justify-center gap-3 transition-all"
            style={{
              background: "linear-gradient(135deg, #c0392b 0%, #96281b 100%)",
              boxShadow: "0 4px 16px rgba(192,57,43,0.4)",
            }}
          >
            <span className="text-lg">▶</span>
            <span>Step1：テキスト抽出を実行</span>
          </button>

          <div className="w-full h-px my-1" style={{ background: "rgba(255,255,255,0.06)" }} />

          <button
            onClick={handleResume}
            className="w-full px-4 py-3 rounded-xl text-gray-400 text-sm flex items-center gap-3 transition-all hover:text-gray-300"
            style={{
              background: "linear-gradient(135deg, rgba(45, 50, 65, 0.8) 0%, rgba(30, 35, 50, 0.8) 100%)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span className="text-lg">🔄</span>
            <span>抽出済みファイルを確認する（Step1スキップ）</span>
          </button>
        </div>
      </div>
    </div>
  );
}