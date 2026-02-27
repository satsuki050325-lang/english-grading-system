import { useState, useEffect } from "react";
import type { Settings } from "../types";

type Props = {
  currentFilename?: string;
  currentIndex?: number;
  totalCount?: number;
  txtPath?: string;
  onSave?: () => void;
  spellCheck: boolean;
  onSpellCheckToggle: () => void;
};

export function FunctionPanel({
  currentFilename,
  currentIndex,
  totalCount,
  txtPath,
  onSave,
  spellCheck,
  onSpellCheckToggle,
}: Props) {
  const isReview = currentFilename !== undefined;
  const [showSettings, setShowSettings] = useState(false);
  const [graderName, setGraderName] = useState("");
  const [pdfxchangePath, setPdfxchangePath] = useState("");
  const [saving, setSaving] = useState(false);
  const [studentId, setStudentId] = useState<string | null>(null);

  // txtPathが変わるたびにテキスト2行目（生徒番号）を取得
  useEffect(() => {
    setStudentId(null);
    if (!txtPath || !window.pywebview) return;
    window.pywebview.api.read_text(txtPath).then((text: string) => {
      const lines = text.split("\n");
      // 2行目（index=1）に生徒番号がある想定
      const id = lines[1]?.trim();
      setStudentId(id || null);
    });
  }, [txtPath]);

  // 設定モーダルを開いたとき現在値を取得
  useEffect(() => {
    if (showSettings && window.pywebview) {
      window.pywebview.api.get_settings().then((s: Settings) => {
        setGraderName(s.grader_name ?? "");
        setPdfxchangePath(s.pdfxchange_path ?? "");
      });
    }
  }, [showSettings]);

  const handleSaveSettings = async () => {
    setSaving(true);
    await window.pywebview.api.save_settings(graderName, pdfxchangePath);
    setSaving(false);
    setShowSettings(false);
  };

  const panelBase: React.CSSProperties = {
    background: "linear-gradient(135deg, rgba(30,35,50,0.85) 0%, rgba(20,25,40,0.85) 100%)",
    border: "1px solid rgba(255,255,255,0.08)",
    boxShadow: "0 4px 12px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.05)",
  };
  const btnBase: React.CSSProperties = {
    background: "rgba(30,35,45,0.5)",
    border: "1px solid rgba(255,255,255,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
  };
  const btnActive: React.CSSProperties = {
    background: "rgba(99,130,220,0.25)",
    border: "1px solid rgba(99,130,220,0.4)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
  };
  const inputStyle: React.CSSProperties = {
    background: "rgba(0,0,0,0.3)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "8px",
    color: "rgb(226,232,240)",
    padding: "6px 10px",
    fontSize: "12px",
    width: "100%",
    outline: "none",
  };

  return (
    <div className="h-full rounded-2xl p-3 flex flex-col gap-3" style={panelBase}>

      {/* ── ステータス ── */}
      <div className="rounded-xl p-3" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)" }}>
        <p className="text-gray-500 text-xs mb-2 tracking-wide">ステータス</p>
        {isReview ? (
          <>
            {/* ファイル名 */}
            <p className="text-gray-500 text-xs truncate mb-1.5" title={currentFilename}>
              {currentFilename}
            </p>
            {/* 生徒番号（テキスト2行目） */}
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="text-gray-600 text-xs">ID:</span>
              <span className={`text-xs font-medium ${studentId ? "text-gray-200" : "text-gray-600"}`}>
                {studentId ?? "読込中..."}
              </span>
            </div>
            {/* 枚数 */}
            <p className="text-gray-500 text-xs">
              {(currentIndex ?? 0) + 1} / {totalCount ?? 1} 枚
            </p>
          </>
        ) : (
          <p className="text-gray-600 text-xs">添削画面で表示されます</p>
        )}
      </div>

      {/* ── 手動保存 ── */}
      <button
        className="w-full rounded-xl py-2.5 px-3 flex items-center gap-2.5 transition-all"
        style={isReview ? btnBase : { ...btnBase, opacity: 0.35, cursor: "not-allowed" }}
        onClick={() => isReview && onSave?.()}
        disabled={!isReview}
        title="テキストを手動保存"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
          <path d="M4 4H13L16 7V16C16 16.6 15.6 17 15 17H5C4.4 17 4 16.6 4 16V4Z" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 17V12H12V17" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 4V7H13" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-gray-400 text-xs">手動保存</span>
      </button>

      {/* ── 校閲モード ── */}
      <button
        className="w-full rounded-xl py-2.5 px-3 flex items-center gap-2.5 transition-all"
        style={spellCheck ? btnActive : btnBase}
        onClick={onSpellCheckToggle}
        title="スペルチェック（校閲モード）のオン/オフ"
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
          <text x="2" y="13" fontSize="10" fontFamily="monospace"
            fill={spellCheck ? "rgba(99,130,220,0.9)" : "rgba(148,163,184,0.8)"}
          >ABC</text>
          <path d="M2 16 Q4 14 6 16 Q8 18 10 16 Q12 14 14 16 Q16 18 18 16"
            stroke={spellCheck ? "rgba(220,80,80,0.9)" : "rgba(148,163,184,0.4)"}
            strokeWidth="1.5" fill="none" strokeLinecap="round"
          />
        </svg>
        <div className="flex-1 text-left">
          <span className={`text-xs ${spellCheck ? "text-blue-300" : "text-gray-400"}`}>校閲モード</span>
          <span className={`block text-xs ${spellCheck ? "text-blue-400/70" : "text-gray-600"}`}>{spellCheck ? "ON" : "OFF"}</span>
        </div>
        <div className="w-8 h-4 rounded-full relative flex-shrink-0 transition-all"
          style={{ background: spellCheck ? "rgba(99,130,220,0.5)" : "rgba(255,255,255,0.1)" }}>
          <div className="absolute top-0.5 w-3 h-3 rounded-full transition-all"
            style={{
              left: spellCheck ? "calc(100% - 14px)" : "2px",
              background: spellCheck ? "rgb(147,197,253)" : "rgba(148,163,184,0.6)",
            }}
          />
        </div>
      </button>

      <div className="flex-1" />

      {/* ── 将来機能 ── */}
      <div className="rounded-xl p-3 text-center" style={{ background: "rgba(0,0,0,0.15)", border: "1px solid rgba(255,255,255,0.04)" }}>
    <p className="text-gray-700 text-xs">機能追加予定</p>
    <p className="text-gray-700 text-xs mt-0.5">解説テキスト作成</p>
    <p className="text-gray-700 text-xs">点数データ管理</p>
  </div>

  <button
    className="w-full rounded-xl py-2.5 px-3 flex items-center gap-2.5 transition-all"
    style={btnBase}
    onClick={() => window.pywebview?.api.run_coordinate_picker()}
    title="座標取得ツールを起動"
  >
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
      <circle cx="10" cy="10" r="2" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5"/>
      <path d="M10 2V5M10 15V18M2 10H5M15 10H18" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
    <span className="text-gray-400 text-xs">座標取得ツール</span>
  </button>

      {/* ── 設定ボタン ── */}
      <button
        className="w-full rounded-xl py-2.5 px-3 flex items-center gap-2.5 transition-all"
        style={btnBase}
        onClick={() => setShowSettings(true)}
      >
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
          <circle cx="10" cy="10" r="2.5" stroke="rgba(148,163,184,0.8)" strokeWidth="1.5"/>
          <path d="M10 3V5M10 15V17M3 10H5M15 10H17M5.05 5.05L6.46 6.46M13.54 13.54L14.95 14.95M14.95 5.05L13.54 6.46M6.46 13.54L5.05 14.95"
            stroke="rgba(148,163,184,0.8)" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <span className="text-gray-400 text-xs">設定</span>
      </button>

      {/* ── 設定モーダル ── */}
      {showSettings && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
          onClick={(e) => e.target === e.currentTarget && setShowSettings(false)}
        >
          <div className="rounded-2xl p-6 w-80 flex flex-col gap-4"
            style={{
              background: "linear-gradient(135deg, rgba(30,35,50,0.98) 0%, rgba(20,25,40,0.98) 100%)",
              border: "1px solid rgba(255,255,255,0.12)",
              boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
            }}
          >
            <h3 className="text-gray-100 text-base font-medium">設定</h3>
            <div className="flex flex-col gap-1.5">
              <label className="text-gray-400 text-xs">採点者名</label>
              <input type="text" value={graderName} onChange={(e) => setGraderName(e.target.value)}
                placeholder="例：太田" style={inputStyle} />
              <p className="text-gray-600 text-xs">PDF印字に使用されます</p>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-gray-400 text-xs">PDF XChange Editor パス（任意）</label>
              <input type="text" value={pdfxchangePath} onChange={(e) => setPdfxchangePath(e.target.value)}
                placeholder="C:\Program Files\..." style={inputStyle} />
              <p className="text-gray-600 text-xs">空欄の場合は自動検索します</p>
            </div>
            <div className="flex gap-2 mt-1">
              <button className="flex-1 rounded-xl py-2 text-xs text-gray-400 transition-all"
                style={btnBase} onClick={() => setShowSettings(false)}>キャンセル</button>
              <button className="flex-1 rounded-xl py-2 text-xs text-gray-100 transition-all"
                style={{ background: "rgba(99,130,220,0.4)", border: "1px solid rgba(99,130,220,0.5)" }}
                onClick={handleSaveSettings} disabled={saving}>
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}