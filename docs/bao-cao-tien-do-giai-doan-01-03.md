# BÁO CÁO TIẾN ĐỘ GIAI ĐOẠN 01–03

## HỆ THỐNG PHIÊN ÂM, TÓM TẮT VÀ HỎI ĐÁP NỘI DUNG CUỘC HỌP

- **Sinh viên:** Nguyễn Phương Linh — MSSV: 20224871 — Lớp: IT1-02
- **Giảng viên hướng dẫn:** TS. Cao Tuấn Dũng
- **Phạm vi:** Yêu cầu nghiệp vụ, nghiên cứu công nghệ và thiết kế kiến trúc hệ thống.

## 1. Mục tiêu hệ thống

Meeting Voice Assistant tự động hóa quy trình lập biên bản cuộc họp tiếng Việt:

- Thu âm trực tiếp hoặc tiếp nhận tệp âm thanh có sẵn.
- Chuyển giọng nói thành transcript có timestamp và nhãn người nói.
- Sinh tóm tắt, quyết định chính và danh sách công việc cần làm.
- Cho phép hỏi đáp nội dung cuộc họp, kèm trích dẫn để nghe lại đúng đoạn audio.
- Hỗ trợ chỉnh sửa, xuất biên bản và chia sẻ theo quyền Owner/Editor/Viewer.

## 2. Kết quả giai đoạn 01–03

| Giai đoạn | Kết quả chính |
|---|---|
| **01 — Requirements** | Đặc tả bài toán, 7 Use Case, nhóm quyền Owner/Editor/Viewer và luồng nghiệp vụ chính. |
| **02 — Research Tech** | Chốt pipeline ASR hai lượt, nghiên cứu Diarization, RAG, Embedding và Cloud LLM. |
| **03 — Architecture** | Hoàn thiện sơ đồ C4, luồng runtime, phân rã hệ thống và các nguyên tắc bảo mật. |

## 3. Mô hình Use Case và phân quyền

~~~plantuml
@startuml
scale max 875 width
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam shadowing false
skinparam roundcorner 6
skinparam wrapWidth 110
skinparam packageStyle rectangle
left to right direction

actor "Chủ cuộc họp\n(Owner)" as Owner
actor "Người sửa\n(Editor)" as Editor
actor "Người xem\n(Viewer)" as Viewer
actor "AI Service" as AIService <<System>>
actor "Cloud LLM" as LLMService <<System>>

rectangle "Meeting Voice Assistant" {
    usecase "UC-01\nGhi âm & phiên âm trực tiếp" as UC01
    usecase "UC-02\nTải tệp & tách người nói" as UC02
    usecase "UC-03\nBiên tập biên bản" as UC03
    usecase "UC-04\nTóm tắt & việc cần làm" as UC04
    usecase "UC-05\nHỏi đáp có trích dẫn" as UC05
    usecase "UC-06\nXuất biên bản" as UC06
    usecase "UC-07\nChia sẻ & phân quyền" as UC07
    usecase "Xác thực & phân quyền" as Auth

    UC01 ..> Auth : <<include>>
    UC02 ..> Auth : <<include>>
    UC03 ..> Auth : <<include>>
    UC04 ..> Auth : <<include>>
    UC05 ..> Auth : <<include>>
    UC07 ..> Auth : <<include>>
}

Owner --> UC01
Owner --> UC02
Owner --> UC03
Owner --> UC04
Owner --> UC05
Owner --> UC06
Owner --> UC07

Editor --> UC03
Editor --> UC04
Editor --> UC05
Editor --> UC06

Viewer --> UC05
Viewer --> UC06

UC01 --> AIService
UC02 --> AIService
UC04 --> LLMService
UC05 --> LLMService
@enduml
~~~

## 4. Kiến trúc hệ thống tổng thể

~~~plantuml
@startuml
scale max 875 width
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam shadowing false
skinparam roundcorner 6
skinparam componentStyle uml2
skinparam linetype ortho

skinparam package {
    BackgroundColor #FAFAFA
    BorderColor #888888
}
skinparam component {
    BackgroundColor #FFFFFF
    BorderColor #333333
    ArrowColor #333333
}
skinparam database {
    BackgroundColor #FFFFFF
    BorderColor #333333
}

package "Client" {
    [Next.js Frontend] as FE
    [AudioWorklet] as AW
}

package "Web Layer" {
    [Reverse Proxy] as Proxy
    [Backend API\n(FastAPI)] as API
    [SSE Gateway] as SSE
}

package "AI Layer" {
    [Live ASR\n(Zipformer-vi)] as LiveASR
    [AI Worker\n(PhoWhisper + Diarization + Embedding)] as AIWorker
}

package "Data Layer" {
    database "PostgreSQL\n+ pgvector" as DB
    database "Redis\nQueue & Streams" as Redis
    database "Audio Storage" as Storage
}

cloud "Cloud LLM API" as LLM

FE --> Proxy : HTTPS
AW --> Proxy : WebSocket
Proxy --> API : REST
Proxy --> SSE : SSE
Proxy --> LiveASR : Live audio

API --> DB : Meeting data\n& hybrid search
API --> Redis : Task / events
API --> Storage : Audio files
API --> LLM : Summary / RAG

LiveASR --> Redis : Draft transcript
AIWorker --> Redis : Progress
AIWorker --> Storage : Read audio
AIWorker --> DB : Segments / vectors
@enduml
~~~

## 5. Quy trình xử lý âm thanh hai lượt

~~~plantuml
@startuml
scale max 875 width
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam shadowing false
skinparam roundcorner 6
skinparam linetype ortho
skinparam nodesep 20
skinparam ranksep 25
left to right direction

rectangle "1. Tiếp nhận\nUpload / thu trực tiếp" as Input
rectangle "2. Chuẩn hóa\nWAV Mono 16 kHz" as Normalize
rectangle "3. Pass 1 - Live ASR\nVAD + Zipformer-vi" as LiveASR
rectangle "4. Transcript nháp\nHiển thị trong cuộc họp" as Draft
rectangle "5. Pass 2 - Batch\nVAD + PhoWhisper" as Batch
rectangle "6. Diarization\n+ Word-to-Speaker Alignment" as Speaker
rectangle "7. Transcript chính thức\nEmbedding + lưu chỉ mục" as Official
rectangle "8. Transcript Studio\nTra cứu và biên tập" as Studio

Input -right-> Normalize
Normalize -right-> LiveASR : Đang họp
LiveASR -right-> Draft
Draft -down-> Batch : Audio hoàn chỉnh
Normalize -down-> Batch : Không họp
Batch -right-> Speaker
Speaker -right-> Official
Official -right-> Studio
@enduml
~~~

- **Pass 1:** ưu tiên tốc độ để hiển thị chữ trong lúc họp.
- **Pass 2:** ưu tiên transcript chính thức, timestamp, speaker và dữ liệu cho RAG.

## 6. Quy trình hỏi đáp có trích dẫn

~~~plantuml
@startuml
scale max 875 width
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam shadowing false
skinparam roundcorner 6
skinparam linetype ortho
skinparam nodesep 20
skinparam ranksep 25
left to right direction

rectangle "1. Người dùng\nđặt câu hỏi" as Question
rectangle "2. Chuyển câu hỏi\nthành vector" as Embed
rectangle "3. Hybrid Search\nDense + Lexical Search" as Search
rectangle "4. Hợp nhất kết quả\nbằng RRF" as RRF
rectangle "5. Chọn context liên quan\nĐưa vào Cloud LLM" as Context
rectangle "6. Sinh câu trả lời\nkèm mã citation" as Answer
rectangle "7. Ánh xạ citation\nSpeaker + timestamp" as Citation
rectangle "8. Bấm citation\nNghe lại audio" as Playback

Question -right-> Embed
Embed -right-> Search
Search -right-> RRF
RRF -down-> Context
Context -right-> Answer
Answer -right-> Citation
Citation -right-> Playback
@enduml
~~~

## 7. Kết luận và bước tiếp theo

Giai đoạn 01–03 đã hoàn thành phần yêu cầu, nghiên cứu và thiết kế kiến trúc cho hệ thống. Sản phẩm tiếp theo cần thực hiện là:

1. Cập nhật sản phẩm kỳ vọng, kế hoạch thực hiện và thời gian viết quyển đồ án.
2. Nghiên cứu speaker embedding/diarization và nguyên lý các mô hình, thư viện sẽ sử dụng.
3. Thiết kế chi tiết API, database, giao diện và tham khảo chức năng lọc nội dung không đưa vào biên bản.
4. Cài đặt AI Service, Backend API, Frontend và tích hợp pipeline audio với Transcript Studio.
5. Kiểm thử ASR, diarization, RAG, phân quyền; cân nhắc xử lý nói chồng và lựa chọn nền tảng triển khai.

