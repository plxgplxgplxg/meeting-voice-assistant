# Biên bản họp báo cáo tiến độ đồ án tốt nghiệp

- **Ngày họp:** [điền ngày]
- **Thành phần:** Thầy hướng dẫn, Em (sinh viên)
- **Đề tài:** Hệ thống ghi âm / chuyển giọng nói thành văn bản cuộc họp, tự động nhận diện và gán nhãn người nói
- **Ghi chú về nguồn:** Transcript gốc được tạo tự động (speech-to-text) nên có nhiều lỗi nghe nhầm. Bản dưới đây đã sửa lỗi chính tả, thêm dấu câu, gán người nói. Chỗ nào suy đoán từ ngữ cảnh được đánh dấu **[?]**.

---

## Phần 1. Tổng hợp nhanh

### 1.1. Những điều quan trọng Thầy nói

**A. Yêu cầu chức năng cho hệ thống**

1. **Phát hiện và phân tách người nói (speaker diarization).** Khi upload hoặc thu âm một cuộc họp, hệ thống phải tự phân tích xem file âm thanh có bao nhiêu giọng khác nhau, rồi đánh nhãn Người 1, Người 2, ..., Người N. Không chỉ chuyển giọng nói thành chữ.
2. **Gán tên một lần, nhận diện lại các lần sau.** Người dùng chỉ gán tên cho một người ở lần họ nói đầu tiên. Những lần sau (ví dụ 5 phút sau) hệ thống phải tự nhận ra đó là cùng một người, không tách thành người khác.
3. **Gán nhãn bằng giọng nói.** Người dùng có thể ra lệnh bằng mic (kiểu agent), ví dụ "người 1 là anh A, người 2 là chị B". Trải nghiệm mong muốn: cả cuộc họp chỉ cần tương tác với máy tính hoặc điện thoại, không phải ngồi gõ tay từng tên.
4. **Hỗ trợ cả hai chế độ đầu vào:** upload file âm thanh có sẵn, và hệ thống tự thu âm trực tiếp trong cuộc họp. Hệ thống nên tương tác được bằng cả giọng nói lẫn giao diện.
5. **Sinh transcript đầy đủ theo người nói** (người A nói gì, người B nói gì). Sau đó có phần **hỏi đáp trên nội dung cuộc họp**. Phần này đã có sẵn mô hình và thư viện nên không phải trọng tâm.
6. **Lọc nội dung không đưa vào biên bản.** Trong cuộc họp, chủ tọa hoặc người chỉ đạo có thể nói "đoạn này không đưa vào biên bản" hoặc "đoạn này không ghi âm". Cũng có lúc là nội dung nhạy cảm, nói ngoài lề, hoặc chuyện vui để đổi không khí. Hệ thống phải có tính năng cắt, bỏ hoặc xóa các đoạn đó, **không phải thu được gì là đưa vào hết**. Nếu nhận dạng được câu lệnh kiểu "đoạn này không đưa vào biên bản" thì hệ thống nên tự cắt, tùy năng lực của em.
7. **Giao diện** phải thân thiện và bố cục khoa học. Các tính năng phụ đều cần làm kỹ.

**B. Các bài toán mở rộng (làm đến đâu tùy năng lực)**

- **Nói chen nhau, tranh luận sôi nổi:** nhiều người nói cùng lúc, âm thanh chồng lên nhau, hệ thống có tách được không? Thầy nhấn mạnh tình huống này vẫn xảy ra thường xuyên trong cuộc họp thật, vì chủ tọa không thể bắt từng người phát biểu lần lượt.
- Thầy chỉ nêu vấn đề để em cân nhắc, không bắt buộc phải giải quyết hết.

**C. Cảnh báo về kiến thức khi bảo vệ**

- Thầy phê bình thẳng: nhiều sinh viên hiện nay chỉ **lắp ghép các thư viện A, B, C, D** mà không hiểu bản chất. Hỏi ra thì kiến thức rất yếu, bảo vệ chỉ được khoảng 2 điểm.
- **Nếu em trả lời "so sánh vector âm thanh" một cách chung chung thì là sai** và hội đồng sẽ đánh giá kém. Lý do: người nói nội dung khác nhau thì tín hiệu âm thanh khác nhau, nên không thể so sánh trực tiếp. Phải có phương pháp trích xuất **đặc trưng riêng của giọng từng người**, không phụ thuộc nội dung câu nói.
- Em phải **nghiên cứu cách nhận dạng người nói bằng đặc trưng giọng**. Nếu chưa nắm được thì nói rõ là dùng API hoặc thư viện nào, **đừng nói sai**.
- Dùng thư viện thì được, nhưng **tối thiểu phải hiểu về mặt cơ bản** từng thành phần làm gì và hoạt động theo phương pháp nào.

**D. Nền tảng triển khai**

- Em đang nghiêng về **web**: thu âm ngay trên web, hoặc upload file. Thầy đặt vấn đề: nếu ghi âm sẵn trên điện thoại thì phải chuyển file ra máy tính rồi mới upload lên web, có bất tiện không? Còn khi họp thì phải mở web lên để thu.
- Có thể cân nhắc chạy web trên điện thoại hoặc làm app.
- **Chưa cần chốt bây giờ**, để khi thiết kế giao diện sẽ quyết định.

**E. Yêu cầu về phiếu giao nhiệm vụ đồ án**

- Mục **quan trọng nhất là "Sản phẩm kỳ vọng"**. Phải ghi các **tính năng chính, tính năng tối thiểu** mà đồ án bắt buộc đạt được. Đây là **căn cứ để giảng viên phản biện** đọc và đánh giá: làm được những mục này là qua.
- Những tính năng không bắt buộc thì **không cần ghi 100%, ghi khoảng 85% thôi**. Phần 100% chỉ là mong muốn, có thể không làm được nên không nhất thiết ghi hết.
- Những gì **bắt buộc theo tiêu đề đồ án** (một hệ thống như vậy tối thiểu phải làm được gì) thì phải ghi đầy đủ.
- Trong kế hoạch phải ghi **thời gian viết quyển** (nhiều bạn chỉ ghi phần làm sản phẩm). **Trước ngày bảo vệ 2 tháng phải bắt đầu viết dần** (Thầy đã ghi trong nhóm).

**F. Cách nộp bản chỉnh sửa**

- Sửa trực tiếp vào **bài post gốc** (edit, update lên post), **không viết comment**.

### 1.2. Việc em cần làm (Action items)

| # | Việc cần làm | Ưu tiên | Hạn |
|---|---|---|---|
| 1 | Cập nhật **Phiếu giao nhiệm vụ đồ án tốt nghiệp**, phần **Sản phẩm kỳ vọng**: ghi rõ các tính năng chính và tính năng tối thiểu bắt buộc phải đạt (xem danh sách gợi ý bên dưới) | Cao | Cuối tuần |
| 2 | Chỉ ghi khoảng 85% tính năng làm chắc chắn được, phần mong muốn (100%) không bắt buộc ghi hết | Cao | Cuối tuần |
| 3 | Bổ sung vào kế hoạch **thời gian viết quyển** (bắt đầu viết dần trước bảo vệ 2 tháng) | Cao | Cuối tuần |
| 4 | **Edit trực tiếp vào bài post gốc**, không comment, rồi **báo lại cho Thầy** | Cao | Cuối tuần |
| 5 | **Nghiên cứu cách nhận dạng người nói**: speaker diarization, speaker embedding (d-vector, x-vector), cách so khớp giọng giữa các đoạn. Chuẩn bị câu trả lời đúng bản chất khi bảo vệ | Cao | Trước khi bảo vệ |
| 6 | Tìm hiểu bản chất từng thư viện, mô hình sẽ dùng (ASR, diarization, hỏi đáp), ít nhất nắm nguyên lý cơ bản và lý do chọn | Trung bình | Trong quá trình làm |
| 7 | Thiết kế **tính năng lọc/cắt nội dung không đưa vào biên bản** (bỏ đoạn, xóa đoạn, nhận lệnh "không đưa vào biên bản") | Trung bình | Khi thiết kế tính năng |
| 8 | Cân nhắc cách xử lý **nói chen nhau (overlapping speech)**, quyết định làm ở mức nào | Thấp (mở rộng) | Sau khi xong tính năng lõi |
| 9 | Chốt **nền tảng (web, web trên điện thoại hay app)** và luồng đầu vào (upload hay thu trực tiếp) khi thiết kế giao diện | Trung bình | Giai đoạn thiết kế giao diện |
| 10 | Thiết kế giao diện thân thiện, khoa học, kể cả gán nhãn người nói bằng lệnh giọng nói | Trung bình | Giai đoạn thiết kế giao diện |

**Gợi ý nội dung "Sản phẩm kỳ vọng" (tính năng tối thiểu, để em chỉnh lại cho khớp):**

1. Nhận file âm thanh cuộc họp (upload) và/hoặc thu âm trực tiếp.
2. Chuyển giọng nói thành văn bản (transcript).
3. Phát hiện số người nói và gán nhãn Người 1..N cho từng đoạn.
4. Gán tên người nói một lần, tự động nhận lại các lần sau theo đặc trưng giọng.
5. Xuất transcript đầy đủ theo từng người nói.
6. Hỏi đáp trên nội dung cuộc họp.
7. Cắt, bỏ hoặc xóa nội dung không đưa vào biên bản.
8. Giao diện web thân thiện.

**Phần mở rộng (mong muốn, không bắt buộc):** gán nhãn bằng lệnh giọng nói, tự nhận lệnh "đoạn này không đưa vào biên bản", xử lý nói chen nhau, hỗ trợ điện thoại hoặc app.

---

## Phần 2. Transcript chuẩn hóa

> Quy ước: **Thầy** là giảng viên hướng dẫn, **Em** là sinh viên. Việc gán người nói dựa vào ngữ cảnh nên có thể sai ở một vài lượt ngắn. Phần mở đầu trong bản gốc nghe như Thầy đang nhắc lại lời Em giải thích cho người khác nghe, nên tôi giữ nguyên theo mạch nội dung.

**Thầy:** Cái âm thanh em ghi vào cuộc hội thoại đấy, khi upload lên không phải chỉ một phát chuyển thành chữ nhỉ. Đồng thời nó phải phân tích xem trong file âm thanh đó có bao nhiêu giọng, có bao nhiêu người khác nhau, đúng không?

Đấy, em ghi vào đi nhé. Thầy chỉ hướng dẫn em duy nhất lần này thôi, vì thầy bận.

**Em:** Dạ vâng ạ.

**Thầy:** Tức là trong một cuộc hội thoại, hệ thống phát hiện giọng và đánh số: người 1, người 2, người 3, ..., người N. Sau đó những người đó là những cái nhãn như vậy, và người ta sẽ gán tên vào, nhưng không phải làm thủ công. Nói cho hay hơn là nó phải nhận dạng được. Tức là người 1 nói câu 1, đến 5 phút sau người 1 nói thì nó phải nhận ra đó là người 1. Đấy, và em chỉ cần gán một lần thôi.

**Em:** À vâng, em cũng làm như thế ạ.

**Thầy:** Ý thầy là, ví dụ người A đang nói ở phút này, xong rồi người B nói, thì mình chỉ gán ở lần đầu tiên người đó nói: người đó tên là gì. Thế thì hệ thống nó sẽ không biết, đúng không?

**Em:** Vâng.

**Thầy:** Nếu hệ thống của em làm tốt, thì mặc dù là âm thanh nhưng hệ thống nó tương tác được bằng tiếng nói, nó hỗ trợ cả hai thì là tốt nhất. Giao diện web thế nhé: em upload âm thanh, hoặc hệ thống tự thu âm. Hoặc nó upload âm thanh xong, em ra lệnh giống như agent bây giờ ấy. Nó có cái mic, em nói, ví dụ "người 1 này là tên này, người kia là tên kia", thì mới tiện. Không phải ngồi gõ tên người này người kia. Em có thể ra lệnh như thế luôn.

Quá trình để trải nghiệm một cuộc họp chỉ là đơn giản tiếp xúc với máy tính và điện thoại thôi, thì cái quá trình gắn nhãn đó có thể ra lệnh bằng giọng nói. Sau đó nó sẽ sinh ra được người A nói gì, người B nói gì. Về bản chất đó là xong cái transcript thôi.

Còn sau đó thì hỏi đáp: một cuộc hội thoại có nội dung chữ dài mấy trang. Hỏi đáp cái gì trong đấy thì hiện tại các mô hình, các thư viện giải quyết hết rồi. Sau đó có những tính năng phụ, nhưng mình phải làm kỹ hơn.

Sau khi ra transcript đầy đủ thì phải xem tính chất của cuộc họp. Trong app, giao diện phải thân thiện và phải khoa học về bố cục. Ví dụ có những nội dung người ta họp, xong rồi người chỉ đạo, chủ tịch, người ta nói: "đoạn này không đưa vào biên bản nhé", hoặc "đoạn này không ghi âm", chẳng hạn. Có lúc người ta phải nói thế: đoạn này nhạy cảm, nói ngoài cuộc họp. Hoặc trong cuộc họp có lúc người ta nói việc chính thống, nhưng có lúc người ta nói chuyện vui để thay đổi không khí. Cho nên có những nội dung phải đưa ra ngoài, và tính năng của mình phải có cái đó. Chứ không phải thu âm được gì là đưa vào hết.

**Em:** Dạ, cái gán nhãn thì em cũng chỉ gán một lần đầu. Những lần sau thì nó sẽ so sánh với **tơ số [?]** của đoạn người nói sau đó, nếu gần nhất thì gán luôn là người đó, chứ không gán thành người khác ạ.

**Thầy:** Nhưng cái đó nó có nhận ra được giọng không đã? Tức là nó phải biết, ví dụ một cuộc họp này có bao nhiêu người nói. Lần đầu người đó phát âm thì gán. Thế còn các lần sau, nó phải tự nhận dạng là giọng của người đó. Em xử lý được thì nó có nhận dạng chính xác không?

**Em:** Thì những lần sau em so sánh vector của lần sau so với những lần trước, nếu giống thì gán cái đó ạ.

**Thầy:** Không phải so sánh vector kiểu đó. Nội dung âm thanh nó khác nhau mà, người ta nói nội dung khác nhau mà.

**Em:** Hồi em làm thì em làm phần **RAG [?]**, nhưng hồi đó bạn ấy làm... Em cũng có chia sẻ với bạn ấy là em đang tốt nghiệp, thì bạn ấy bảo lúc đó bạn ấy so sánh vector âm thanh của...

**Thầy:** Thế đấy. Em học, các bạn bây giờ có cái dở đấy. Thầy nói thật, hỏi ra là thấy các bạn kiến thức rất hỏng, chẳng hiểu cái gì, trả lời như thế thì bảo vệ được 2 điểm. Chắc là bạn ấy so sánh các đặc trưng của giọng nói. Cái file âm thanh mà thầy nói lúc trước là làm việc A, xong thầy nói câu sau là "đi nghỉ", thì làm sao so sánh được hai cái đó? Nếu mà âm thanh nó khác nhau, thì cái vector đó là người ta phải trích những cái giọng, phải xác định câu nào ứng với đặc trưng âm thanh riêng biệt của một người. Thì em phải nghiên cứu cái đó. Hoặc nếu không thì em bảo không biết, em gọi API, em dùng thư viện. Chứ em đừng nói so sánh kiểu thế là sai. Hội đồng người ta sẽ đánh giá kém mình.

**Em:** Dạ vâng ạ.

**Thầy:** Bây giờ rất dở là cái gì người ta cũng có thư viện làm cho hết. Phần mềm bây giờ dễ hơn ngày xưa, ngày xưa làm mất công hơn, nhưng người ta phải đòi hỏi kiến thức, phải hiểu rõ hơn. Chứ bây giờ các bạn không hiểu, các bạn cứ lắp ghép A, B, C, D, nhưng các bạn không hiểu bản chất A, B, D nó làm việc gì thì cũng được. Bảo vệ đâu có chỉ việc em chạy được cái chương trình. Em phải hiểu cái thành phần của nó được làm bởi cái gì, phương pháp như thế nào, ít nhất là về mặt cơ bản.

Còn thầy nói thêm một cái nữa là phần nội dung đó phải có tính năng để người ta bỏ hoặc xóa đi những nội dung mà người ta không muốn. Có những đoạn người ta nói nhưng chỗ này không đưa vào biên bản họp. Ví dụ em nhận dạng được đoạn nói có nội dung đó thì em phải tự cắt đi. Tùy năng lực của em làm được đến đâu thì em làm.

Ngoài ra còn có những trường hợp nói chen nhau, em có nhận được không? Bài toán mở rộng thì có rất nhiều, nhưng vẫn là năng lực của em làm đến đâu. Ví dụ không phải lúc nào trong một cuộc họp cũng lý tưởng là người này nói xong dừng, người kia nói xong dừng, phát biểu lần lượt. Có những lúc tranh luận kiểu sôi nổi mà nhiều người cùng nói. Thế thì nó sẽ lẫn vào nhau. Có xử lý được vấn đề đó không? Nó vẫn xảy ra. Nhiều lúc chủ tọa người ta vẫn không thể để từng người phát biểu một theo kiểu lên mục phát biểu, vì nó không hợp.

Xong rồi đặt ra một vấn đề, thì sau đó nhiều người nói, hỏi trả lẫn nhau, có thể là nó chùm nhau một phần, hoặc có phần nó đè lên nhau. Âm thanh đó thì phải xem xét là có tách được ra không. Thầy nêu vài vấn đề đó thôi. Còn loại tính năng các thứ thì em cũng đã đề xuất rồi, thầy cũng không có ý kiến gì thêm, vì thời gian không còn nhiều.

**Em:** Dạ vâng ạ.

**Thầy:** Nhưng thực ra làm thì các bạn cứ làm theo cái tiện. Cái này nó phải làm trên app chứ: đã thu âm cuộc họp, nó đang trên điện thoại thì em đẩy luôn vào app điện thoại.

**Em:** Hôm nay thì em phải upload, lấy file từ điện thoại ra máy tính để gửi lên web à?

**Thầy:** Đấy là hai trường hợp. Còn một trường hợp nữa thì...

**Em:** Ý là em thấy mọi người vẫn ghi âm trên web bình thường à? Người ta cũng không tải app bao giờ nữa.

**Thầy:** Thế lúc đó không phải bật cái web đó lên đúng không?

**Em:** Vâng. Lúc họp thì phải bật lên. Hoặc nó không phải chạy web trên điện thoại.

**Thầy:** Nhé, thôi đợi khi nào em thiết kế giao diện thì tính sau.

**Em:** Dạ vâng ạ.

**Thầy:** Thì đấy, để xem. Còn từ nội dung góp ý của thầy thì em sửa, cập nhật vào trong phiếu giao nhiệm vụ đồ án tốt nghiệp. Chú ý: phiếu giao nhiệm vụ đồ án tốt nghiệp, mục quan trọng nhất là **sản phẩm kỳ vọng**. Cái đó mình phải ghi là những tính năng chính, những tính năng tối thiểu mà đồ án phải đạt được, thì em phải ghi vào. Vì đó là căn cứ để người phản biện đọc: thầy giao cho em những cái đó, mà em làm được thì em qua.

Thế còn những cái không bắt buộc thì không phải ghi 100%, em ghi 85% thôi. Phần 100% là những cái mà em mong muốn đạt được, nhưng cũng có thể em không làm được, thì không nhất thiết ghi hết vào. Nhưng những cái bắt buộc theo tiêu đề của đồ án, một hệ thống sản phẩm như vậy nó đạt được cái gì thì mình cũng phải ghi vào. Đấy, thế thôi.

Và ngoài ra trong kế hoạch thì phải ghi cái **thời gian viết quyển** nữa, chứ không phải nhiều bạn chỉ viết "làm" thôi. Thời gian viết quyển thầy ghi trong nhóm rồi: trước 2 tháng trước khi bảo vệ là phải bắt đầu viết dần.

**Em:** Dạ vâng.

**Thầy:** Đấy, thế thôi. Em làm rồi sửa đi. Xong rồi gửi, thì phải gửi **post lên trên cái post** đó nhé, chứ đừng viết comment.

**Em:** Dạ vâng.

**Thầy:** Tức là viết lên trên, update, edit lên rồi gửi.

**Em:** Vâng.

**Thầy:** Cuối tuần em làm xong rồi update, rồi báo cho thầy.

**Em:** Dạ vâng.

---

## Phần 3. Các từ nghe nhầm đã sửa / cần kiểm tra lại

| Trong transcript gốc | Đã sửa thành | Mức chắc chắn |
|---|---|---|
| cửa hỏi / khỏi thoại | cuộc hội thoại | Cao |
| chuyển thành cách | chuyển thành chữ | Cao |
| nhận rộng | nhận dạng | Cao |
| viên bản | biên bản | Cao |
| phiếu giao nhiệm hữu | phiếu giao nhiệm vụ | Cao |
| viết quyển | viết quyển (quyển đồ án) | Cao |
| bỏ / xóa đi những cái nội dung | giữ nguyên ý | Cao |
| tơ số | tơ số **[?]** (có thể là "tham số" hoặc "tần số", cần nhớ lại em nói gì) | Thấp |
| phần rap | RAG **[?]** (có thể là RAG, hoặc một đề tài khác) | Thấp |
| ông Minh ở chỗ | đã lược bỏ, không rõ nghĩa | Thấp |
| hỏi tre lẫn nhau | hỏi trả lẫn nhau | Trung bình |
| "Các bạn nhớ đăng kí kênh nhé" (cuối file) | Đã bỏ: đây là câu lạc của phần phụ đề tự động, không thuộc nội dung cuộc họp | Cao |

> Nếu bạn nhớ lại được các chỗ đánh dấu **[?]** thì sửa trực tiếp trong file để biên bản chính xác hơn.
