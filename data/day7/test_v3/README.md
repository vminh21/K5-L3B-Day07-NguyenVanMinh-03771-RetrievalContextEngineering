# Test v3 — bộ test độc lập lớn hơn và khó hơn (vòng 3)

- **Lý do:** test v2 (7 + 2 câu) quá dễ (mọi cấu hình 9/9) và mẫu nhỏ. Test v3: **20 câu có đáp án + 6 câu thiếu evidence** — gấp ~3 lần test v2.
- **Khó hơn:** paraphrase ít trùng từ khóa (5), numeric — số/ngày có trong văn bản, vài câu dễ dụ model tự tính (6), multi-hop cần **đủ mọi nhóm evidence** (3, trường `gold_groups`), conditional (4), mục danh sách bị chunk cắt rời (v12), chú thích của Engels (v14, v15); câu thiếu evidence dạng **bẫy gần đúng** (ví dụ "1888 edition" có thật nhưng không có số bản in; "3–6 năm" có thật nhưng không phải án của Marx).
- **Độc lập:** 0 chunk evidence trùng với dev, test v1, test v2, dev_hard. Viết và commit **trước** mọi thay đổi vòng 3 (rerank, kiểm tra số liệu); chạy **một lần** sau khi chốt.
- **Chấm multi-hop:** Hit@1/Hit@3 = có ít nhất một evidence bắt buộc trong top-k; Context Evidence Rate = **mọi nhóm** có trong context; câu trả lời phải đủ mọi phần mới được 2 điểm.
- Sinh lại: `python -m src.build_benchmark --round3` (đồng thời tạo `data/day7/dev_hard/`: 8 + 2 câu dev khó để chỉnh vòng 3, vì dev cũ đã bão hòa 22/22).
