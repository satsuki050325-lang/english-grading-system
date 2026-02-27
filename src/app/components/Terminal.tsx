import { Terminal as TerminalIcon } from "lucide-react";
import { useState, useEffect, useRef } from "react";

export function Terminal() {
  const [logs, setLogs] = useState<string[]>([
    "$ English Proofreading System v1.0.0",
    "$ Ready...",
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (window as any).updateLog = (msg: string) => {
      setLogs((prev) => [...prev, msg]);
    };

    // プログレスバー専用：最後の行がProgressなら置き換え、なければ追加
    (window as any).updateProgress = (msg: string) => {
      setLogs((prev) => {
        const last = prev[prev.length - 1] ?? "";
        if (last.startsWith("Progress:")) {
          return [...prev.slice(0, -1), msg];
        }
        return [...prev, msg];
      });
    };

    return () => {
      delete (window as any).updateLog;
      delete (window as any).updateProgress;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLogColor = (log: string) => {
    if (log.startsWith("❌")) return "text-red-400";
    if (log.startsWith("✅")) return "text-green-400";
    if (log.startsWith("💾")) return "text-blue-400";
    if (log.startsWith("📦") || log.startsWith("📁") || log.startsWith("♻️")) return "text-yellow-400";
    if (log.startsWith("▶")) return "text-cyan-400";
    if (log.startsWith("⚙️")) return "text-purple-400";
    if (log.includes("Progress") || log.includes("█") || log.includes("%")) return "text-cyan-300";
    if (log.startsWith("$")) return "text-gray-500";
    return "text-gray-400";
  };

  return (
    <div
      className="h-full backdrop-blur-sm rounded-xl flex flex-col"
      style={{
        background: "linear-gradient(135deg, rgba(30,35,50,0.85) 0%, rgba(20,25,40,0.85) 100%)",
        boxShadow: "0 4px 12px rgba(0,0,0,0.25), 0 8px 24px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-700/30">
        <div className="flex items-center gap-2 text-gray-400 font-medium text-sm">
          <TerminalIcon className="w-3.5 h-3.5" />
          <span>Terminal</span>
        </div>
        <button
          className="text-gray-600 hover:text-gray-400 text-xs transition-colors"
          onClick={() => setLogs(["$ ログをクリアしました"])}
        >
          clear
        </button>
      </div>
      <div
        className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-0.5"
        style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(100,116,139,0.3) transparent" }}
      >
        {logs.map((log, i) => (
          <div key={i} className={`leading-5 whitespace-pre-wrap break-all ${getLogColor(log)}`}>
            {log}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}