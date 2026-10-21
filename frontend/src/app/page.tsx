import Link from "next/link";

interface MeetingItem {
  id: string;
  title: string;
  status: "completed" | "processing" | "created";
  duration: string;
  date: string;
  segmentsCount: number;
}

const mockMeetings: MeetingItem[] = [
  {
    id: "550e8400-e29b-41d4-a716-446655440001",
    title: "Họp Báo Cáo Tiến Độ ĐATN Tuần 6",
    status: "completed",
    duration: "45:20",
    date: "2024-10-21",
    segmentsCount: 84,
  },
  {
    id: "550e8400-e29b-41d4-a716-446655440002",
    title: "Thảo Luận Kiến Trúc RAG & pgvector",
    status: "processing",
    duration: "30:15",
    date: "2024-10-20",
    segmentsCount: 52,
  },
];

export default function MeetingsDashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Danh Sách Cuộc Họp</h1>
          <p className="text-sm text-slate-600 mt-1">Quản lý và tra cứu biên bản các phiên làm việc</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/live"
            className="px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition"
          >
            Tạo Cuộc Họp Mới
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockMeetings.map((item) => (
          <Link
            key={item.id}
            href={`/meetings/${item.id}`}
            className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 hover:shadow-sm transition block"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                {item.date}
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  item.status === "completed"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {item.status === "completed" ? "Đã Xử Lý" : "Đang Xử Lý"}
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">{item.title}</h3>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-500 mt-4 pt-3 border-t border-slate-100">
              <span>Thời lượng: {item.duration}</span>
              <span>{item.segmentsCount} lượt nói</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
