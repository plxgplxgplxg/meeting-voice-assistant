interface MeetingDetailProps {
  params: {
    id: string;
  };
}

export default function MeetingDetailPage({ params }: MeetingDetailProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <span className="text-xs font-semibold text-slate-500">ID: {params.id}</span>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Chi Tiết Cuộc Họp & Biên Bản</h1>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 text-xs font-semibold border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50">
            Xuất Text
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-3">
            Biên Bản Phiên Âm Đồng Bộ
          </h2>
          <div className="space-y-4 text-sm text-slate-800">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span className="font-bold text-slate-700">Speaker 1</span>
                <span>00:00 - 00:25</span>
              </div>
              <p>Chào các bạn, hôm nay chúng ta họp tổng kết tiến độ Đồ án tốt nghiệp tuần 6.</p>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span className="font-bold text-slate-700">Speaker 2</span>
                <span>00:26 - 01:10</span>
              </div>
              <p>Về phần kiến trúc RAG, chúng ta sử dụng pgvector với chỉ mục HNSW trên PostgreSQL 16.</p>
            </div>
          </div>
        </div>

        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">
              Tóm Tắt & Việc Cần Làm
            </h2>
            <div className="text-sm text-slate-700">
              <p className="font-semibold text-slate-900 mb-1">Điểm chính:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Hoàn thành khảo sát ASR và Diarization.</li>
                <li>Thiết lập khung mã nguồn Docker Compose.</li>
              </ul>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">
              Trợ Lý Hỏi Đáp (RAG)
            </h2>
            <div className="h-40 rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs text-slate-600 overflow-y-auto">
              Nhập câu hỏi để tra cứu nội dung cuộc họp có trích dẫn.
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Hỏi về nội dung cuộc họp..."
                className="flex-1 text-sm px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-slate-400"
              />
              <button className="px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800">
                Gửi
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
