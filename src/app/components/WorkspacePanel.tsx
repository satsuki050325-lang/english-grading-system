import { useEffect, useState, useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

type Props = {
  type: "pdf" | "text";
  pdfPath?: string;
  txtPath?: string;
  currentPair?: number;
  totalPairs?: number;
  onJumpTo?: (idx: number) => void;
  jumpTrigger?: number;
  spellCheck?: boolean;
  onTextChange?: (text: string) => void; // 親がテキストを把握するためのcb
};

export function WorkspacePanel({
  type, pdfPath, txtPath,
  currentPair, totalPairs, onJumpTo, jumpTrigger,
  spellCheck = true,
  onTextChange,
}: Props) {
  const [imgSrc, setImgSrc] = useState<string>("");
  const [text, setText] = useState<string>("");
  const [pageIdx, setPageIdx] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isEditing, setIsEditing] = useState(false);
  const [jumpInput, setJumpInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setPageIdx(0);
    setImgSrc("");
  }, [pdfPath]);

  useEffect(() => {
    if (type === "pdf" && pdfPath) {
      window.pywebview.api.get_pdf_image(pdfPath, pageIdx, 1.0).then((res) => {
        if ("image_data" in res) {
          setImgSrc(res.image_data);
          setTotalPages((res as any).total_pages ?? 1);
        }
      });
    }
  }, [type, pdfPath, pageIdx]);

  useEffect(() => {
    if (type === "text" && txtPath) {
      window.pywebview.api.read_text(txtPath).then((res) => {
        setText(res);
        onTextChange?.(res);
      });
    }
  }, [type, txtPath]);

  useEffect(() => {
    if (jumpTrigger && jumpTrigger > 0 && type === "pdf") {
      setJumpInput(String((currentPair ?? 0) + 1));
      setIsEditing(true);
    }
  }, [jumpTrigger]);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const handleJumpClick = () => {
    if (!onJumpTo || totalPairs === undefined) return;
    setJumpInput(String((currentPair ?? 0) + 1));
    setIsEditing(true);
  };

  const handleJumpConfirm = () => {
    if (!onJumpTo || totalPairs === undefined) return;
    const n = parseInt(jumpInput, 10);
    if (!isNaN(n) && n >= 1 && n <= totalPairs) {
      onJumpTo(n - 1);
    }
    setIsEditing(false);
  };

  const handleJumpKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleJumpConfirm();
    if (e.key === "Escape") setIsEditing(false);
  };

  const handleTextChange = (val: string) => {
    setText(val);
    onTextChange?.(val);
  };

  return (
    <div
      className="h-full flex flex-col rounded-xl overflow-hidden"
      style={{
        background: "linear-gradient(135deg, rgba(20,25,40,0.9) 0%, rgba(15,20,35,0.9) 100%)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {type === "pdf" && (
        <>
          <style>{`
            .pdf-scroll::-webkit-scrollbar { width: 6px; }
            .pdf-scroll::-webkit-scrollbar-track { background: transparent; margin: 12px; }
            .pdf-scroll::-webkit-scrollbar-thumb { background: rgba(100,116,139,0.3); border-radius: 3px; }
            .pdf-scroll::-webkit-scrollbar-thumb:hover { background: rgba(100,116,139,0.5); }
            .pdf-scroll::-webkit-scrollbar-button { display: none; }
            .jump-input::-webkit-outer-spin-button,
            .jump-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
            .jump-input { -moz-appearance: textfield; }
          `}</style>

          <div
            className="pdf-scroll flex-1 p-3 overflow-y-auto overflow-x-hidden"
            style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(100,116,139,0.3) transparent" }}
          >
            {imgSrc ? (
              <img src={imgSrc} alt="PDF" style={{ display: "block", width: "100%", maxWidth: "100%" }} />
            ) : (
              <p className="text-gray-500 text-sm">PDFを読み込んでいます...</p>
            )}
          </div>

          {/* ページナビ */}
          <div
            className="flex items-center justify-center gap-3 py-2 border-t relative"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
          >
            <button
              onClick={() => setPageIdx(p => Math.max(0, p - 1))}
              disabled={pageIdx === 0}
              className="w-24 h-8 backdrop-blur-sm rounded-lg flex items-center justify-center gap-1.5 text-gray-500 hover:text-gray-300 disabled:opacity-30 transition-all"
              style={{ background: "rgba(30,35,45,0.4)", boxShadow: "0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset" }}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span className="text-xs">前へ</span>
            </button>

            <span className="text-gray-400 text-xs">{pageIdx + 1} / {totalPages}</span>

            <button
              onClick={() => setPageIdx(p => Math.min(totalPages - 1, p + 1))}
              disabled={pageIdx === totalPages - 1}
              className="w-24 h-8 backdrop-blur-sm rounded-lg flex items-center justify-center gap-1.5 text-gray-500 hover:text-gray-300 disabled:opacity-30 transition-all"
              style={{ background: "rgba(30,35,45,0.4)", boxShadow: "0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset" }}
            >
              <span className="text-xs">次へ</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>

            {/* M枚目/N枚中 */}
            {currentPair !== undefined && totalPairs !== undefined && (
              <div className="absolute right-3">
                {isEditing ? (
                  <div
                    className="h-8 flex items-center gap-1 px-3 rounded-lg"
                    style={{ background: "rgba(30,35,45,0.6)", boxShadow: "0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(148,163,184,0.25) inset" }}
                  >
                    <input
                      ref={inputRef} type="number"
                      className="jump-input w-8 bg-transparent text-gray-100 text-xs text-center outline-none"
                      value={jumpInput}
                      onChange={(e) => setJumpInput(e.target.value)}
                      onKeyDown={handleJumpKeyDown}
                      onBlur={handleJumpConfirm}
                    />
                    <span className="text-gray-500 text-xs">枚目 / {totalPairs}枚中</span>
                  </div>
                ) : (
                  <button
                    onClick={handleJumpClick}
                    className="h-8 px-3 rounded-lg flex items-center text-gray-400 hover:text-gray-200 transition-all"
                    style={{ background: "rgba(30,35,45,0.4)", boxShadow: "0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset" }}
                  >
                    <span className="text-xs">{currentPair + 1}枚目 / {totalPairs}枚中</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {type === "text" && (
        <textarea
          className="flex-1 bg-transparent text-gray-200 text-sm resize-none outline-none p-3"
          value={text}
          spellCheck={spellCheck}
          lang="en"
          onChange={(e) => handleTextChange(e.target.value)}
          style={{ color: "rgb(226,232,240)" }}
        />
      )}
    </div>
  );
}