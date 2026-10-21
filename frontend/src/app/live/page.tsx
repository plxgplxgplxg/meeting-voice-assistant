export default function LiveMeetingPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Phòng Thu Âm Trực Tiếp</h1>
        <p className="text-sm text-slate-600 mt-1">Thu âm từ microphone và phiên âm thời gian thực</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-8 text-center space-y-6">
        <div className="h-24 flex items-center justify-center rounded-lg bg-slate-50 border border-dashed border-slate-200">
          <span className="text-sm font-medium text-slate-500">Visualizer Sóng Âm (Ready)</span>
        </div>

        <div className="flex justify-center gap-4">
          <button className="px-6 py-2.5 text-sm font-bold text-white bg-red-600 rounded-lg hover:bg-red-700 transition">
            Bắt Đầu Ghi Âm
          </button>
          <button className="px-6 py-2.5 text-sm font-semibold border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 transition">
            Tạm Dừng
          </button>
        </div>
      </div>
    </div>
  );
}
