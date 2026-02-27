type Props = {
  onSave: () => void;
  onStep23: () => void;
};

export function DoneCard({ onSave, onStep23 }: Props) {
  return (
    <div className="h-full flex items-center justify-center">
      <div
        className="w-[500px] rounded-2xl p-10 flex flex-col gap-4"
        style={{
          background: "linear-gradient(135deg, rgba(30, 35, 50, 0.85) 0%, rgba(20, 25, 40, 0.85) 100%)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        }}
      >
        <h1 className="text-green-400 text-2xl font-bold text-center">✅ 全答案の確認完了</h1>
        <p className="text-gray-400 text-sm text-center">採点処理を実行して完了してください</p>

        <div className="flex flex-col gap-3 mt-2">
          <button
            onClick={onSave}
            className="w-full px-4 py-3 rounded-xl text-gray-200 text-sm flex items-center gap-3 transition-all hover:text-gray-100"
            style={{
              background: "linear-gradient(135deg, rgba(45, 50, 65, 0.8) 0%, rgba(30, 35, 50, 0.8) 100%)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span className="text-lg">💾</span>
            <span>全テキストを一括保存</span>
          </button>

          <button
            onClick={onStep23}
            className="w-full px-4 py-4 rounded-xl text-white text-sm font-bold flex items-center justify-center gap-3 transition-all"
            style={{
              background: "linear-gradient(135deg, #c0392b 0%, #96281b 100%)",
              boxShadow: "0 4px 16px rgba(192,57,43,0.4)",
            }}
          >
            <span className="text-lg">🚀</span>
            <span>Step2 & Step3 実行（採点・PDF印字）</span>
          </button>
        </div>
      </div>
    </div>
  );
}