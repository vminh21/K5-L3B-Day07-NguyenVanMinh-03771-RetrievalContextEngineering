# Bổ sung đáp án chuẩn (gold) sau khi chạy test — vòng 3, 2026-11-16

Các preface lặp lại nội dung, nên một số câu có **câu tương đương ở trang khác** mà gold ban đầu chưa liệt kê. Phát hiện khi chấm tay; bổ sung **dưới dạng gold thay thế** (một trong các gold là đủ). Không chạy lại agent; nhãn chấm tay không đổi (citation p41 vốn đã được chấm là hỗ trợ). Retrieval được **chấm lại từ trace đã lưu** (`python -m src.rescore_retrieval …`), không chạy lại.

| Câu | Gold ban đầu | Bổ sung (trang 41, preface 1890) |
|---|---|---|
| t06 (test v1) | p37 "The International, on its breaking in 1874, left the workers quite different men from what it found them in 1864." | "The working class of 1874, at the dissolution of the International, was altogether different from that of 1864, at its foundation." |
| u06 (test v2) | p38 "Thus, in 1847, socialism was a middle-class movement, communism a working-class movement." | "Socialism in 1847 signified a bourgeois movement, communism a working-class movement." |

## Retrieval trước → sau khi bổ sung gold

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate |
|---|---|---|---|---|
| M1 Dense | test v1 | 3/6 → 3/6 | 5/6 → 5/6 | 6/6 → 6/6 |
| Hybrid + neighbours k5 (A2) | test v1 | 4/6 → 4/6 | 5/6 → 5/6 | 5/6 → 5/6 (t06 vẫn miss: cả p37 lẫn p41 …b1a3da đều không vào context) |
| M1 Dense | test v2 | 5/7 → **6/7** | 7/7 → 7/7 | 7/7 → 7/7 |
| Hybrid + neighbours k5 (A2) | test v2 | 6/7 → **7/7** | 7/7 → 7/7 | 7/7 → 7/7 |
| Hybrid + neighbours + dedup k8 (A3b) | test v2 | 6/7 → **7/7** | 7/7 → 7/7 | 7/7 → 7/7 |

Agent: không đổi (A0/A2 test v1, A0/A2/A3b test v2 giữ nguyên nhãn và số liệu). MRR@10 không chấm lại được (trace chỉ lưu top-3).
