import { FunctionPanel } from "./components/FunctionPanel";
import { WorkspacePanel } from "./components/WorkspacePanel";
import { Terminal } from "./components/Terminal";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import type { Pair, DoneDate, Step23State } from "./types";
// types.tsのdeclare globalを読み込むためのimport（型のみ）


function SpinnerIcon({ onClick }: { onClick?: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick?.(); }}
      className="relative w-8 h-8 flex items-center justify-center hover:scale-110 transition-transform"
      title="クリックでキャンセル"
    >
      <svg className="animate-spin absolute inset-0" width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2"
          strokeDasharray="50" strokeDashoffset="12" opacity="0.7" />
      </svg>
      <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" className="relative z-10 opacity-80">
        <rect x="1" y="1" width="10" height="10" rx="1.5" />
      </svg>
    </button>
  );
}

function CheckIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
      <path d="M7 12L10.5 15.5L17 9" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState(0);
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [current, setCurrent] = useState(0);
  const [jumpTrigger, setJumpTrigger] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [step23State, setStep23State] = useState<Step23State>("idle");
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [doneDates, setDoneDates] = useState<DoneDate[]>([]);
  const [spellCheck, setSpellCheck] = useState(true);
  const [direction, setDirection] = useState(1);
  const currentTextRef = useRef<string>("");

  useEffect(() => {
    if (currentScreen === 3) setStep23State("idle");
  }, [currentScreen]);

  const saveCurrentText = useCallback(async () => {
    const txtPath = pairs[current]?.txt;
    if (txtPath && currentTextRef.current) {
      await window.pywebview.api.save_text(txtPath, currentTextRef.current);
    }
  }, [pairs, current]);

  const nextScreen = useCallback(async () => {
    if (currentScreen === 1 || currentScreen === 2) {
      await saveCurrentText();
      setDirection(1);
      if (current < pairs.length - 1) {
        setCurrent(current + 1);
      } else {
        setCurrentScreen(3);
      }
    }
  }, [currentScreen, current, pairs, saveCurrentText]);

  const prevScreen = useCallback(async () => {
    if (currentScreen === 1 || currentScreen === 2) {
      await saveCurrentText();
      setDirection(-1);
      if (current > 0) {
        setCurrent(current - 1);
      } else {
        setCurrentScreen(0);
      }
    } else if (currentScreen === 3) {
      setDirection(-1);
      setCurrentScreen(1);
      setCurrent(pairs.length - 1);
    }
  }, [currentScreen, current, pairs, saveCurrentText]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "Enter") {
        e.preventDefault();
        nextScreen();
      }
      if (e.ctrlKey && e.key === "g") {
        e.preventDefault();
        if (currentScreen === 1 || currentScreen === 2) {
          setJumpTrigger((t: number) => t + 1);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [nextScreen, currentScreen]);

  const handleManualSave = useCallback(async () => {
    await saveCurrentText();
  }, [saveCurrentText]);

  const handleNewCorrection = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      const filePath = await window.pywebview.api.open_file_dialog();
      if (!filePath) return;

      const isZip = filePath.toLowerCase().endsWith(".zip");
      const isPdf = filePath.toLowerCase().endsWith(".pdf");

      if (isZip) {
        const extracted = await window.pywebview.api.extract_zip(filePath);
        if (!extracted) return;
      } else if (isPdf) {
        const copied = await window.pywebview.api.copy_pdf(filePath);
        if (!copied) return;
      } else {
        return;
      }

    const ok = await window.pywebview.api.run_step1();
    if (ok) {
      const result = await window.pywebview.api.get_pairs();
      if (result.length > 0) {
        setPairs(result);
        setCurrent(0);
        setDirection(1);
        setCurrentScreen(1);
      }
    } else {
  // キャンセルまたは失敗 → StartCardのまま
}
    } finally {
      setIsProcessing(false);
    }
  };

  const handleHistory = async () => {
    const currentPairs = await window.pywebview.api.get_pairs();
    if (currentPairs.length > 0) {
      setPairs(currentPairs);
      setCurrent(0);
      setDirection(1);
      setCurrentScreen(1);
      return;
    }
    const dates = await window.pywebview.api.get_done_dates();
    if (dates.length === 0) {
      alert("過去のデータが見つかりません。");
      return;
    }
    setDoneDates(dates);
    setShowDatePicker(true);
  };

  const handleSelectDate = async (dateKey: string) => {
    setIsProcessing(true);
    try {
      const ok = await window.pywebview.api.restore_from_done(dateKey);
      if (!ok) { alert("復元に失敗しました。"); return; }
      const result = await window.pywebview.api.get_pairs();
      if (result.length > 0) {
        setPairs(result);
        setCurrent(0);
        setDirection(1);
        setCurrentScreen(1);
        setShowDatePicker(false);
      } else {
        alert("PDFが見つかりません。");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRunStep23 = async () => {
  if (step23State !== "idle") return;
  setStep23State("running");
  try {
    const ok = await window.pywebview.api.run_step23();
    setStep23State(ok ? "done" : "idle");
  } catch {
    setStep23State("idle");
  }
};

const handleCancelStep1 = async () => {
  await window.pywebview.api.cancel_step1();
  setIsProcessing(false);
  // StartCard画面のまま（何もない状態）
};

const handleCancelStep23 = async () => {
  await window.pywebview.api.cancel_step23();
  setStep23State("idle");
  // レビュー画面に戻る
  setDirection(-1);
  setCurrentScreen(1);
  setCurrent(pairs.length - 1);
};

  const isReviewScreen = currentScreen === 1 || currentScreen === 2;
  const isDoneScreen = currentScreen === 3;
  const showLeftButton = isReviewScreen || isDoneScreen;
  const showRightButton = isReviewScreen;

  const enterX = direction === 1 ? "100%" : "-100%";
  const exitX  = direction === 1 ? "-100%" : "100%";

  const baseCard: React.CSSProperties = {
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.18)",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)",
  };
  const activeCard:  React.CSSProperties = { ...baseCard, background: "rgba(255,255,255,0.05)" };
  const dimmedCard:  React.CSSProperties = { ...baseCard, background: "rgba(255,255,255,0.02)", opacity: 0.45, cursor: "not-allowed" };
  const doneCard:    React.CSSProperties = { ...baseCard, background: "rgba(255,255,255,0.02)", opacity: 0.5,  cursor: "default" };
  const navBtn:      React.CSSProperties = {
    background: "rgba(30,35,45,0.3)",
    boxShadow: "0 1px 4px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset",
  };

  return (
    <div style={{ height: "100vh", background: "linear-gradient(135deg, #1a1f2e 0%, #0f141f 100%)" }} className="p-6">
      <div className="h-full flex gap-5">
        <div className="flex-1 flex flex-col gap-5 min-h-0">
          <div className="flex-1 min-h-0">
            <div
              className="h-full rounded-2xl p-12 relative overflow-hidden"
              style={{
                backgroundImage: "radial-gradient(circle, rgba(148,163,184,0.15) 1px, transparent 1px)",
                backgroundSize: "20px 20px",
                backgroundColor: "rgba(71,85,105,0.2)",
                backdropFilter: "blur(4px)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.3), 0 16px 48px rgba(0,0,0,0.2)",
              }}
            >
              {showLeftButton && (
                <button
                  className="absolute left-2 top-1/2 -translate-y-1/2 h-24 w-9 backdrop-blur-sm rounded-lg flex items-center justify-center text-gray-600 hover:text-gray-300 transition-all z-10"
                  style={navBtn} onClick={prevScreen}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              {showRightButton && (
                <button
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-24 w-9 backdrop-blur-sm rounded-lg flex items-center justify-center text-gray-600 hover:text-gray-300 transition-all z-10"
                  style={navBtn} onClick={nextScreen}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}

              <AnimatePresence mode="wait" initial={false}>

                {/* ── startcard ── */}
                {currentScreen === 0 && (
                  <motion.div key="start"
                    initial={{ x: enterX, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: exitX, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    className="absolute inset-12 flex items-start justify-center pt-20"
                  >
                    <div className="w-full max-w-2xl space-y-6">
                      <h2 className="text-2xl text-gray-100 text-center mb-8">添削を始めましょう</h2>
                      <AnimatePresence>
                        {showDatePicker && (
                          <motion.div
                            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.2 }}
                            className="rounded-2xl p-5 mb-4"
                            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
                          >
                            <div className="flex items-center justify-between mb-4">
                              <span className="text-gray-300 text-sm font-medium">復元する日付を選択</span>
                              <button onClick={() => setShowDatePicker(false)} className="text-gray-500 hover:text-gray-300 text-xs transition-colors">キャンセル</button>
                            </div>
                            <p className="text-gray-600 text-xs mb-3">選択するとPDF・テキストがinputs/step1_textsに復元されます</p>
                            <div className="space-y-2 max-h-48 overflow-y-auto">
                              {doneDates.map((d) => (
                                <button key={d.key} onClick={() => handleSelectDate(d.key)}
                                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-left transition-all hover:bg-white/5"
                                  style={{ border: "1px solid rgba(255,255,255,0.08)" }}
                                  disabled={isProcessing}
                                >
                                  <span className="text-gray-200 text-sm">{d.label}</span>
                                  <div className="flex items-center gap-2">
                                    <span className="text-gray-500 text-xs">{d.count}枚</span>
                                    {isProcessing && (
                                      <svg className="animate-spin w-3 h-3 text-gray-400" viewBox="0 0 24 24" fill="none">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="40" strokeDashoffset="10"/>
                                      </svg>
                                    )}
                                  </div>
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                      <div className="space-y-4">
                        <button className="w-full rounded-2xl p-6 text-left flex items-center justify-between transition-all group"
                          style={{ ...activeCard, opacity: isProcessing ? 0.6 : 1, cursor: isProcessing ? "not-allowed" : "pointer" }}
                          onClick={handleNewCorrection} disabled={isProcessing}
                        >
                          <div className="flex-1">
                            <div className="text-gray-100 text-lg mb-2">{isProcessing ? "処理中..." : "新規添削を開始"}</div>
                            <div className="text-gray-400 text-sm">
                              {isProcessing ? "ZIPの展開とテキスト抽出を実行中です（ターミナルで進捗を確認できます）" : "ZIPファイルを選択して、テキスト抽出から開始します"}
                            </div>
                          </div>
                          <div className="text-gray-400 group-hover:text-gray-100 transition-colors">
                            {isProcessing ? <SpinnerIcon onClick={handleCancelStep1} /> : (
                              <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                                <path d="M10 14V6M10 6L7 9M10 6L13 9M4 16H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                            )}
                          </div>
                        </button>
                        <button className="w-full rounded-2xl p-6 text-left flex items-center justify-between transition-all group"
                          style={activeCard} onClick={handleHistory}
                        >
                          <div className="flex-1">
                            <div className="text-gray-100 text-lg mb-2">確認・修正を再開</div>
                            <div className="text-gray-400 text-sm">テキスト抽出済みの答案を確認・修正します</div>
                          </div>
                          <div className="text-gray-400 group-hover:text-gray-100 transition-colors">
                            <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                              <path d="M4 7H16M4 10H16M4 13H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              <rect x="3" y="4" width="14" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                            </svg>
                          </div>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ── レビュー画面 ── */}
                {isReviewScreen && (
                  <motion.div key={`review-${current}`}
                    initial={{ x: enterX, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: exitX, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    className="absolute inset-4"
                  >
                    <div className="w-full h-full backdrop-blur-sm rounded-xl p-4 flex flex-col"
                      style={{
                        background: "linear-gradient(135deg, rgba(30,35,50,0.85) 0%, rgba(20,25,40,0.85) 100%)",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.08)",
                      }}
                    >
                      <div className="flex-1 min-h-0">
                        <PanelGroup direction="horizontal">
                          <Panel defaultSize={80} minSize={30}>
                            <WorkspacePanel
                              type="pdf" pdfPath={pairs[current]?.pdf}
                              currentPair={current} totalPairs={pairs.length}
                              onJumpTo={(idx: number) => {
                                setDirection(idx > current ? 1 : -1);
                                setCurrent(idx);
                              }}
                              jumpTrigger={jumpTrigger}
                            />
                          </Panel>
                          <PanelResizeHandle className="w-1 mx-2 relative">
                            <div className="absolute inset-0 w-1 rounded-full" style={{ background: "rgba(148,163,184,0.2)" }}/>
                          </PanelResizeHandle>
                          <Panel defaultSize={20} minSize={15}>
                            <WorkspacePanel
                              type="text" txtPath={pairs[current]?.txt}
                              spellCheck={spellCheck}
                              onTextChange={(t: string) => { currentTextRef.current = t; }}
                            />
                          </Panel>
                        </PanelGroup>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ── donecard ── */}
                {isDoneScreen && (
                  <motion.div key="done"
                    initial={{ x: enterX, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: exitX, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    className="absolute inset-12 flex items-start justify-center pt-20"
                  >
                    <div className="w-full max-w-2xl space-y-6">
                      <h2 className="text-2xl text-gray-100 text-center mb-8">確認が完了しました</h2>
                      <div className="space-y-4">

                        <button className="w-full rounded-2xl p-6 text-left flex items-center justify-between transition-all group"
                          style={step23State === "idle" ? activeCard : doneCard}
                          onClick={handleRunStep23} disabled={step23State !== "idle"}
                        >
                          <div className="flex-1">
                            <div className="text-gray-100 text-lg mb-2">
                              {step23State === "idle"    && "採点・PDF印字を実行"}
                              {step23State === "running" && "処理中..."}
                              {step23State === "done"    && "採点・PDF印字 完了"}
                            </div>
                            <div className="text-gray-400 text-sm">
                              {step23State === "idle"    && "AIによる採点と採点結果のPDF印字を行います"}
                              {step23State === "running" && "採点とPDF印字を実行中です（ターミナルで進捗を確認できます）"}
                              {step23State === "done"    && "採点済みPDFが出力フォルダに保存されました"}
                            </div>
                          </div>
                          <div className="text-gray-400 transition-colors">
                            {step23State === "idle"    && <svg width="24" height="24" viewBox="0 0 20 20" fill="none" className="group-hover:text-gray-100"><path d="M10 5V15M5 10H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                            {step23State === "running" && <SpinnerIcon onClick={handleCancelStep23} />}
                            {step23State === "done"    && <CheckIcon />}
                          </div>
                        </button>

                        <button className="w-full rounded-2xl p-6 text-left flex items-center justify-between transition-all group"
                          style={step23State === "done" ? activeCard : dimmedCard}
                          onClick={() => step23State === "done" && window.pywebview.api.open_with_pdfxchange()}
                          disabled={step23State !== "done"}
                        >
                          <div className="flex-1">
                            <div className="text-gray-100 text-lg mb-2">PDF XChange Editorで開く</div>
                            <div className="text-gray-400 text-sm">
                              {step23State === "done" ? "採点済みPDFをEditorで開いて確認・編集できます" : "採点・PDF印字の完了後に使用できます"}
                            </div>
                          </div>
                          <div className="text-gray-400 group-hover:text-gray-100 transition-colors">
                            <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                              <path d="M4 4H10V10H4V4Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              <path d="M10 10L16 16M10 16H16V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          </div>
                        </button>

                        <button className="w-full rounded-2xl p-6 text-left flex items-center justify-between transition-all group"
                          style={step23State === "done" ? activeCard : dimmedCard}
                          onClick={() => {
                            if (step23State === "done") {
                              setDirection(-1);
                              setCurrentScreen(0);
                            }
                          }}
                          disabled={step23State !== "done"}
                        >
                          <div className="flex-1">
                            <div className="text-gray-100 text-lg mb-2">最初の画面に戻る</div>
                            <div className="text-gray-400 text-sm">
                              {step23State === "done" ? "新しいZIPファイルの添削を開始します" : "採点・PDF印字の完了後に使用できます"}
                            </div>
                          </div>
                          <div className="text-gray-400 group-hover:text-gray-100 transition-colors">
                            <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
                              <path d="M3 10H17M3 10L7 6M3 10L7 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          </div>
                        </button>

                      </div>
                    </div>
                  </motion.div>
                )}

              </AnimatePresence>
            </div>
          </div>

          <div className="h-48">
            <Terminal />
          </div>
        </div>

        <div style={{ width: "200px", flexShrink: 0, height: "100%" }}>
          <FunctionPanel
            currentFilename={isReviewScreen ? pairs[current]?.filename : undefined}
            currentIndex={isReviewScreen ? current : undefined}
            totalCount={isReviewScreen ? pairs.length : undefined}
            txtPath={isReviewScreen ? pairs[current]?.txt : undefined}
            onSave={handleManualSave}
            spellCheck={spellCheck}
            onSpellCheckToggle={() => setSpellCheck((v: boolean) => !v)}
          />
        </div>
      </div>
    </div>
  );
}