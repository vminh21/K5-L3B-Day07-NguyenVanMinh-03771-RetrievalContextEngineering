"""Benchmark for the advanced (multimodal) challenge: NASA FY 2024 Agency Financial Report (127 pages).

Written by reading the ORIGINAL pages (rendered at 100-110 dpi and checked by eye), BEFORE any index or
pipeline experiment. Pages are PDF page numbers (printed page = PDF page - 1).
Every `quote` is asserted to occur in that page's PDF text layer; visual-only evidence (bar heights, colours,
dotted lines, positions in a diagram) has `visual_only: true` and a `locator` describing the region.

    python -m src.mm.build_benchmark          # -> data/advanced/benchmark/{dev,test}.json
"""
import json
import re
from pathlib import Path

PDF = Path("data/advanced/raw/nasa_afr_fy2024.pdf")
OUT = Path("data/advanced/benchmark")
GROUPS = ("table", "image", "chart", "multihop", "text")


def ev(page, kind, locator, quote=None, visual_only=False):
    return {"page": page, "printed_page": page - 1, "kind": kind, "locator": locator,
            "quote": quote, "visual_only": visual_only}


def Q(id, group, question, answer, evidence, reason, scoring=None):
    return {"id": id, "group": group, "question": question, "expected_answer": answer, "evidence": evidence,
            "reason": reason, "scoring": scoring or "Đạt khi đúng và đủ mọi phần, đúng đơn vị; citation đúng trang chứa evidence."}


def N(id, question, absence_reason, grep):
    return {"id": id, "group": "no_evidence", "question": question, "expected_behavior": "abstain",
            "absence_reason": absence_reason, "grep_checked": grep}


TEST = [
    # ---------------- table (6)
    Q("T-TB1", "table", "In the FY 2024 budget table by Strategic Objective, what were the requested FY 2024 amount and the Operating Plan (OP) FY 2024 amount for Objective 2.1 'Explore the surface of the Moon and deep space', and how much lower was the OP?",
      "Requested $7,971 million; OP $7,648 million; the OP was $323 million lower.",
      [ev(17, "table", "Strategic Goals and Objectives table, row 2.1, columns Requested FY 2024 / OP FY 2024 (millions)", "7,971")],
      "Tra đúng hàng 2.1 và hai cột, tính hiệu 7,971 − 7,648 = 323 (đơn vị triệu USD)."),
    Q("T-TB2", "table", "Which Strategic Objective has the smallest Operating Plan (OP) amount for FY 2024 in the budget table, and what are its requested and OP amounts?",
      "Objective 4.1 'Attract and develop a talented and diverse workforce': requested $112 million, OP $102 million.",
      [ev(17, "table", "Strategic Goals and Objectives table, row 4.1", "Attract and develop a talented and diverse workforce.")],
      "So sánh cả cột OP FY 2024 để tìm giá trị nhỏ nhất (102)."),
    Q("T-TB3", "table", "In the heritage assets table (in physical units), how many 'NASA Locations' were there in 2023 and in 2024, and what was the change in Total Heritage Assets?",
      "NASA Locations went from 9 (2023) to 8 (2024) after 1 withdrawal; Total Heritage Assets went from 12 to 11.",
      [ev(63, "table", "Heritage Assets (in physical units) table, row NASA Locations and Total row", "NASA Locations")],
      "Đọc hàng Non-Collection-type / NASA Locations và hàng tổng (2023, Withdrawals, 2024)."),
    Q("T-TB4", "table", "According to the land acreage table as of September 30, 2024, how many acres were in the Conservation and Preservation category, and what was the total estimated acreage at the end of the current year?",
      "101,198 acres in Conservation and Preservation; total estimated acreage 135,315 acres.",
      [ev(83, "table", "Land acreage table (in acres), row End of Current Year, columns Conservation and Preservation / Total Estimated Acreage", "101,198")],
      "Đúng hàng End of Current Year, đúng đơn vị acre."),
    Q("T-TB5", "table", "In the table of contract/instrument types by percentage of total obligations, which instrument type has the largest share, and what share does Cost-Plus-Award-Fee have?",
      "Firm-Fixed-Price is largest at 31%; Cost-Plus-Award-Fee is 28%.",
      [ev(110, "table", "Instrument Type / Percentage of Total Obligations table", "Firm-Fixed-Price")],
      "So sánh cột phần trăm; hai giá trị cần đúng."),
    Q("T-TB6", "table", "For expired grants with undisbursed balances, how many grants and what total undisbursed amount were reported for fiscal year 2024, compared with 2023?",
      "2024: 975 grants with $12,936 thousand undisbursed; 2023: 663 grants with $8,126 thousand.",
      [ev(114, "table", "Undisbursed Balances in Expired Grant Accounts table, rows 2024 and 2023", "12,936")],
      "Hai hàng × hai cột; đơn vị nghìn USD."),
    # ---------------- chart (5)
    Q("T-CH1", "chart", "In the FY 2024 Performance Assessment chart, how many Strategic Goal 3 performance goals were rated 'Complete or On Target to Complete' in FY 2023 and in FY 2024?",
      "7 in FY 2023 and 10 in FY 2024.",
      [ev(22, "chart", "Stacked 100% bar chart, Strategic Goal 3, green segments of FY 2023 and FY 2024 bars", visual_only=True)],
      "Đọc nhãn số trên phần màu xanh lá của hai cột Goal 3 theo chú giải."),
    Q("T-CH2", "chart", "According to the 'Assets by Type Comparison' chart, what was the value of the 'Other' asset category in FY 2023 and in FY 2024?",
      "$106 million in FY 2023 and $987 million in FY 2024.",
      [ev(30, "chart", "Assets by Type Comparison stacked bars, purple 'Other' segment", "$106")],
      "Giá trị FY 2023 chỉ có trong biểu đồ; cần đúng màu/chú giải 'Other'."),
    Q("T-CH3", "chart", "In the 'Liabilities by Type Comparison' chart, what were Federal Employee Salary, Leave and Benefits Payable in FY 2023 and FY 2024?",
      "$288 million in FY 2023 and $348 million in FY 2024.",
      [ev(31, "chart", "Liabilities by Type Comparison stacked bars, orange segment", "$288")],
      "Ghép đúng màu cam với chú giải; giá trị FY 2023 không có trong text."),
    Q("T-CH4", "chart", "In the Comparative Gross Cost of Operations chart, what was the gross cost of the Human Landing System in FY 2024 and FY 2023, and did it increase or decrease?",
      "$1,144 million in FY 2024 vs $1,463 million in FY 2023 — a decrease of $319 million.",
      [ev(33, "chart", "Horizontal bar chart, Strategic Goal 2, Human Landing System (orange = 2024, purple = 2023)", "Human Landing System")],
      "Phải gán đúng năm theo chú giải màu (text layer liệt kê 2023 trước 2024)."),
    Q("T-CH5", "chart", "According to the Sources of Funding Comparison chart, how much Spending Authority from Offsetting Collections did NASA have in FY 2023, and how much in FY 2024?",
      "$2,108 million in FY 2023 and $1,840 million in FY 2024.",
      [ev(34, "chart", "Sources of Funding Comparison stacked bars, purple top segment", "$2,108")],
      "Giá trị FY 2023 chỉ có trong biểu đồ."),
    # ---------------- image / diagram (5)
    Q("T-IM1", "image", "In NASA's organizational structure chart, which organizations are connected to the Administrator's office by dotted lines, and what do the dotted lines indicate?",
      "The Advisory Groups (NASA Advisory Council and Aerospace Safety Advisory Panel) and the Inspector General; dotted lines indicate independent advisory or oversight organizations.",
      [ev(11, "diagram", "Organizational Structure chart, top-left boxes with dashed connectors + legend", "Dotted lines indicate independent advisory or oversight organizations"),
       ev(11, "diagram", "dashed connectors to 'Advisory Groups—NAC & ASAP' and 'Inspector General'", visual_only=True)],
      "Phải nhận ra đường nét đứt trong sơ đồ (không có trong text) và đọc chú giải."),
    Q("T-IM2", "image", "On the NASA Centers and Facilities map, which NASA center manages the Wallops Flight Facility, and which other facilities on the map are managed by that same center?",
      "Goddard Space Flight Center (GSFC); it also manages the Katherine Johnson Verification and Validation Facility and the Goddard Institute for Space Studies.",
      [ev(12, "map", "US map (raster image), label 'Wallops Flight Facility (managed by GSFC)' at the Virginia coast", visual_only=True)],
      "Đọc nhãn '(managed by GSFC)' trên bản đồ."),
    Q("T-IM3", "image", "In the Strategic Plan Framework diagram, what time horizon is shown for Performance Goals and for Priority Questions, and which framework in the legend do Priority Questions belong to?",
      "Performance Goals: 2-5 years; Priority Questions: 4 years; Priority Questions belong to the Evidence Act (blue).",
      [ev(15, "diagram", "Strategic Plan Framework flow diagram, boxes and colour legend (GPRAMA / Evidence Act / PMA Priorities)", "Priority Questions"),
       ev(15, "diagram", "blue colour of Priority Questions box = Evidence Act in legend", visual_only=True)],
      "Liên kết màu ô với chú giải là thông tin chỉ có trong hình."),
    Q("T-IM4", "image", "In Figure 2 (NASA's UNICORN enterprise risk management framework), which five risk categories are shown?",
      "Political and Reputational Risk, Programmatic Risk, Financial Risk, Strategic Risk, Operational Risk.",
      [ev(39, "diagram", "Figure 2 NASA's UNICORN, coloured risk bar in lower half", visual_only=True)],
      "Năm nhãn rủi ro nằm trong ảnh raster của hình, không có trong text layer."),
    Q("T-IM5", "image", "In Figure 3 (ERM Sources), which source circle is associated with 'GAO, OIG, Audit Reports, Fraud Risk Assessments'?",
      "Audits and Assessments.",
      [ev(40, "diagram", "Figure 3 ERM Sources (raster image), upper-left circle 'Audits and Assessments' with outer label", visual_only=True)],
      "Ghép nhãn bên ngoài với vòng tròn tương ứng trong sơ đồ."),
    # ---------------- multi-hop (4)
    Q("T-MH1", "multihop", "Which Strategic Goal had the largest net cost of operations in FY 2024, how much was it, and how many of that goal's performance goals were rated 'Complete or On Target to Complete' in FY 2024?",
      "Strategic Goal 2 — $10,920 million (44% of net cost); 8 of its performance goals were rated complete or on target in FY 2024.",
      [ev(32, "chart", "Net Cost of Operations by Strategic Goal donut", "$10,920"),
       ev(22, "chart", "Performance Assessment chart, Strategic Goal 2 FY 2024 green segment", visual_only=True)],
      "Cần hai biểu đồ ở hai trang khác nhau.", "Đạt khi đúng cả goal, số tiền và số 8."),
    Q("T-MH2", "multihop", "How many civil service employees does Johnson Space Center have, and which NASA supporting facility in New Mexico does Johnson manage?",
      "3,229 employees (18% of the workforce); it manages the White Sands Test Facility.",
      [ev(13, "infographic", "NASA by the Numbers, civil service workforce by center", "3,229"),
       ev(12, "map", "map (raster image) label 'White Sands Test Facility (managed by JSC)' in New Mexico", visual_only=True)],
      "Infographic trang 13 + bản đồ trang 12."),
    Q("T-MH3", "multihop", "The report shows technicians lifting a Liquid Oxygen Tank for SLS at a facility in New Orleans. Which NASA center manages that facility, and what was the Space Launch System's gross cost in FY 2024?",
      "Michoud Assembly Facility, managed by Marshall Space Flight Center (MSFC); SLS gross cost was $2,719 million in FY 2024.",
      [ev(12, "photo+map", "photo caption about Michoud + map label 'Michoud Assembly Facility (managed by MSFC)'", "Michoud Assembly Facility"),
       ev(33, "chart", "Gross Cost chart, Strategic Goal 2, Space Launch System 2024 bar", "Space Launch System")],
      "Ba bước: chú thích ảnh → bản đồ → biểu đồ chi phí."),
    Q("T-MH4", "multihop", "Strategic Objective 4.1 is 'Attract and develop a talented and diverse workforce'. What was its FY 2024 Operating Plan amount, and how did the related FEVS DEIA index result for Performance Goal 4.1.2 compare with the target?",
      "OP FY 2024 was $102 million (requested $112 million); the FEVS DEIA index was 84.1 percent versus a target of 88 percent or above, so the goal was rated Red.",
      [ev(17, "table", "budget table row 4.1", "Attract and develop a talented and diverse workforce."),
       ev(23, "text", "Performance Goal 4.1.2 paragraph", "84.1 percent")],
      "Bảng trang 17 + text trang 23."),
    # ---------------- text (4)
    Q("T-TX1", "text", "For how many consecutive years has NASA received an unmodified ('clean') audit opinion as of FY 2024, and what weakness did the independent auditors identify?",
      "14th consecutive year; one material weakness in internal control related to financial reporting oversight (financial controls designed appropriately but not operating effectively).",
      [ev(6, "text", "Message from the Administrator", "14th consecutive year"),
       ev(85, "text", "OIG transmittal of the audit", "one material weakness in internal control related to financial reporting oversight")],
      "Tổng hợp hai ý."),
    Q("T-TX2", "text", "Of the funds available to NASA in FY 2024, how much did the Agency obligate, and what can happen to the remainder?",
      "NASA obligated $27 billion of the $30 billion available; the remaining $3 billion may be obligated until the funds' periods of availability expire.",
      [ev(34, "text", "Sources of Funding text", "The remaining $3 billion may be obligated until the funds’ periods of availability expire")],
      "Điều kiện về thời hạn khả dụng của quỹ."),
    Q("T-TX3", "text", "Which Artemis II milestones does the report say were reached in FY 2024 regarding the SLS booster segments and the Crew Module/Service Module testing?",
      "The Artemis II SLS Booster Segments were delivered to Kennedy Space Center, and the Artemis II Crew Module/Service Module Vacuum Performance Testing was completed in July 2024.",
      [ev(25, "text", "Strategic Goal 2 overview", "Vacuum Performance Testing completed in July 2024")],
      "Hai mốc."),
    Q("T-TX4", "text", "Why did NASA's 'Other Liabilities' increase in FY 2024, and by how much?",
      "They rose by $744 million (to about $1 billion), primarily due to implementing SFFAS 54 (leases) in FY 2024, which requires additional financial reporting for leases.",
      [ev(31, "text", "Total Liabilities text", "an increase of $744 million")],
      "Nguyên nhân + số tiền."),
]
TEST_NO = [
    N("T-NE1", "How much did NASA spend on the Mars Sample Return mission in FY 2024?",
      "Mars Sample Return chỉ được nhắc tên (p102 OIG challenges, p124 acronym); không có số chi tiêu.", [r"Mars Sample Return.{0,120}\$", r"\$.{0,60}Mars Sample Return"]),
    N("T-NE2", "What is NASA's enacted FY 2025 appropriation?",
      "Không có số ngân sách FY 2025 nào (grep 'FY 2025 … $' = 0).", [r"FY 2025.{0,60}\$"]),
    N("T-NE3", "How many people work at the Jet Propulsion Laboratory?",
      "JPL là FFRDC do Caltech quản lý; p73 chỉ nói nhân sự JPL là nhân viên Caltech và nhà thầu, không có số; infographic p13 không có JPL.", [r"JPL.{0,80}\d[\d,]{2,} (employees|staff|people)", r"\d[\d,]{2,} (employees|staff|people).{0,60}JPL"]),
    N("T-NE4", "What was the net cost of operations of the Human Landing System program in FY 2024?",
      "Chỉ có gross cost theo chương trình (p33); net cost chỉ theo strategic goal (p32). Bẫy: dễ lấy 1,144 (gross).", ["Human Landing System.{0,80}net cost"]),
    N("T-NE5", "How many acres of land does Kennedy Space Center occupy?",
      "Bảng diện tích (p83) chỉ theo loại sử dụng, không theo trung tâm.", ["Kennedy.{0,60}acre", "acre.{0,60}Kennedy"]),
    N("T-NE6", "On what date is the Artemis II mission scheduled to launch?",
      "Artemis II được nhắc nhiều lần (p2, p6, p19, p25, p44) nhưng không có ngày phóng.", [r"Artemis II.{0,80}(launch date|scheduled)"]),
]

DEV = [
    Q("D-TB1", "table", "In the FY 2024 budget table, what were the requested and OP FY 2024 amounts for Objective 1.2 'Understand the Sun, solar system, and universe'?",
      "Requested $5,788 million; OP $5,138 million.", [ev(17, "table", "row 1.2", "5,788")], "Tra hàng."),
    Q("D-TB2", "table", "For grants/cooperative agreements that expired 2-3 years ago, how many had undisbursed balances and what was the total undisbursed amount?",
      "2 grants/cooperative agreements, $183 thousand.", [ev(115, "table", "Grants Programs Information table, column 2-3 years", "$ 183")], "Đúng cột 2-3 years."),
    Q("D-TB3", "table", "In the land acreage table, how many Operational acres were there at the start of the prior year and at the end of the current year?",
      "29,898 acres at the start of the prior year and 29,900 acres at the end of the current year.", [ev(83, "table", "Operational column", "29,898")], "Hai hàng."),
    Q("D-CH1", "chart", "According to the Balance Sheet Components chart, what was NASA's net position in FY 2023?",
      "$19,416 million.", [ev(29, "chart", "Balance Sheet Components, FY 2023 dark segment", "$19,416")], "Đúng màu Net Position."),
    Q("D-CH2", "chart", "In the Net Cost of Operations by Strategic Goal donut for FY 2024, what were Strategic Goal 1's net cost and share?",
      "$8,038 million, 32%.", [ev(32, "chart", "donut, Goal 1 segment", "$8,038")], "Đọc nhãn."),
    Q("D-CH3", "chart", "In the 'Liabilities by Type FY 2024' donut, what share and amount do Accounts Payable represent?",
      "23%, $1,775 million.", [ev(31, "chart", "donut, Accounts Payable label", "$1,775")], "Đọc nhãn."),
    Q("D-CH4", "chart", "In the gross cost chart, what was the Space Launch System's gross cost in FY 2023?",
      "$2,555 million.", [ev(33, "chart", "Strategic Goal 2, SLS purple bar", "$2,555")], "Đúng năm theo màu."),
    Q("D-IM1", "image", "In the organizational structure chart, which Mission Directorates are shown?",
      "Aeronautics Research, Exploration Systems Development, Science, Space Operations, Space Technology, and Mission Support Directorate.",
      [ev(11, "diagram", "middle column of directorate boxes", "Aeronautics Research")], "Đủ 6 mục."),
    Q("D-IM2", "image", "In Figure 1 (NASA FMFIA Annual Statement of Assurance Process), what are the levels of the pyramid from bottom to top, up to the Administrator?",
      "Annual assessment of internal controls over programs, operations, financial reporting & systems → NASA Officials-in-Charge/Center Directors/CFO assurance statements → Management System Working Group → Senior Assessment Team → Mission Support Council → Administrator.",
      [ev(38, "diagram", "Figure 1 pyramid", "SENIOR")], "Đúng thứ tự."),
    Q("D-IM3", "image", "According to the Strategic Plan Framework breakdown, how many Strategic Goals, Strategic Objectives and Performance Goals does NASA have?",
      "4 Strategic Goals, 12 Strategic Objectives, 50 Performance Goals.", [ev(15, "infographic", "framework breakdown strip", "Strategic")], "Ba số."),
    Q("D-MH1", "multihop", "What was the OP FY 2024 for Objective 1.1 'Understand the Earth system and its climate', and what was the FY 2024 gross cost of Earth Science Research?",
      "OP $1,740 million; Earth Science Research gross cost $578 million.",
      [ev(17, "table", "row 1.1", "1,740"), ev(33, "chart", "Goal 1, Earth Science Research 2024", "Earth Science Research")], "Bảng + biểu đồ."),
    Q("D-MH2", "multihop", "What were NASA's FY 2024 Congressional Appropriations in the Sources of Funding chart, and what share of the FY 2024 budget went to Research, Engineering, & Development?",
      "Congressional Appropriations $24,876 million (83% of total funding); Research, Engineering, & Development $13.3B (54% of the $24.9B budget).",
      [ev(34, "chart", "Sources of Funding donut", "$24,876"), ev(13, "infographic", "FY 2024 budget panel", "$13.3B")], "Hai trang."),
    Q("D-TX1", "text", "How many astronauts will Artemis II send around the Moon, and where will Artemis III land?",
      "Four astronauts; Artemis III will land in the lunar South Pole region.", [ev(6, "text", "Message from the Administrator", "send four astronauts around the Moon")], "Hai ý."),
    Q("D-TX2", "text", "How close did the Juno spacecraft come to Io's surface, and on what date?",
      "About 930 miles (1,500 kilometers), on Dec. 30, 2023.", [ev(38, "text", "Did You Know box", "930 miles (1,500 kilometers)")], "Hai đơn vị."),
    Q("D-TX3", "text", "When was the Artemis II core stage delivered to Kennedy Space Center?",
      "July 24, 2024.", [ev(19, "text", "Agency Priority Goals – Artemis", "delivered to Kennedy Space Center on July 24, 2024")], "Ngày."),
]
DEV_NO = [
    N("D-NE1", "How many patent licenses did NASA grant in FY 2024?", "p26 chỉ nhắc 'patent licenses' chung, không có số.", [r"patent licens.{0,60}\d", r"\d[\d,]* patent"]),
    N("D-NE2", "What was the total cost of the PACE mission?", "PACE chỉ nhắc mục tiêu phóng (p21, p24), không có chi phí.", [r"\bPACE\b.{0,100}\$"]),
    N("D-NE3", "How many employees work at the Goddard Institute for Space Studies?", "GISS chỉ có trên bản đồ p12; infographic p13 chỉ có GSFC.", [r"Goddard Institute.{0,80}employ"]),
]


# dev v2 — added after dev v1 was saturated (18/18 for every config), BEFORE any test run. Harder shapes like
# the test (visual-only cues, map -> infographic hops, chart -> chart hops) but on different elements/answers.
DEV2 = [
    Q("D2-IM1", "image", "In the graphic defining Assets, Liabilities and Net Position on the balance-sheet page, which symbol accompanies each term, and what relationship do they express?",
      "Assets has a plus (+) symbol, Liabilities a minus (−) symbol and Net Position an equals (=) symbol: Assets − Liabilities = Net Position.",
      [ev(29, "diagram", "three definition panels above the Balance Sheet Components chart, circled +, −, = icons", visual_only=True)],
      "Ký hiệu chỉ có trong hình."),
    Q("D2-IM2", "image", "In the Performance Goal rating definitions graphic, what colour is the 'Below Target' rating, and what does a grey 'Unrated' rating mean?",
      "Below Target is yellow; Unrated (grey) means the information needed to evaluate performance was not available in time for AFR publication, and a final rating will be provided in the FY 2026 VIPer.",
      [ev(21, "infographic", "four coloured rating cards", "Information needed to evaluate performance was not available")],
      "Gắn màu với nhãn."),
    Q("D2-CH1", "chart", "In the FY 2024 Performance Assessment chart, how many Strategic Goal 4 performance goals were rated 'Significantly Below Target/At Risk' in FY 2024, and how many were unrated?",
      "1 Significantly Below Target/At Risk and 1 Unrated.",
      [ev(22, "chart", "Strategic Goal 4, FY 2024 bar, red and grey segments", visual_only=True)],
      "Đọc đúng màu đỏ/xám của cột FY 2024."),
    Q("D2-CH2", "chart", "In the 'Liabilities by Type FY 2024' donut chart, which category has the largest share, and what share and amount is it?",
      "Environmental and Disposal Liabilities: 31%, $2,353 million.",
      [ev(31, "chart", "Liabilities by Type FY 2024 donut", "31%")],
      "So sánh các phần của donut."),
    Q("D2-MH1", "multihop", "Which NASA center manages the Neil A. Armstrong Test Facility, and how many civil service employees does that center have?",
      "Glenn Research Center (GRC); 1,471 employees (8% of the civil service workforce).",
      [ev(12, "map", "map (raster image) label 'Neil A. Armstrong Test Facility (managed by GRC)' in Ohio", visual_only=True),
       ev(13, "infographic", "civil service workforce by center", "1,471")],
      "Bản đồ raster → infographic."),
    Q("D2-MH2", "multihop", "Which Strategic Goal had the smallest net cost of operations in FY 2024, and what was that goal's FY 2024 gross cost of operations?",
      "Strategic Goal 4 — net cost $2,847 million (12%); its FY 2024 gross cost was $3,042 million.",
      [ev(32, "chart", "Net cost donut, Goal 4", "$2,847"), ev(33, "chart", "Gross cost chart, Goal 4 FY 2024 total", "$3,042")],
      "Hai biểu đồ, hai trang; net khác gross."),
    Q("D2-TX1", "text", "How many Performance Goals remained unrated at the time of the FY 2024 AFR's publication, and how many of them were awaiting ratings from the Science Advisory Committees?",
      "Twelve were unrated; ten of them were awaiting ratings from the Science Advisory Committees.",
      [ev(22, "text", "FY 2024 Performance Assessment text", "Twelve Performance Goals supporting Strategic Goals remained unrated")],
      "Hai số có điều kiện."),
    Q("D2-TX2", "text", "Why was Performance Goal 4.2.8 unrated in the FY 2024 AFR?",
      "Because of a lag in data availability immediately after the quarter (the goal concerns facility reliability through preventive maintenance).",
      [ev(22, "text", "FY 2024 Performance Assessment text", "unrated due to a lag of data availability immediately after the quarter")],
      "Lý do."),
]
DEV2_NO = [
    N("D2-NE1", "What was NASA's net cost of operations for Strategic Goal 2 in FY 2022?",
      "Net cost theo goal chỉ có FY 2024 (p32) và FY 2023/2024 (p51); không có FY 2022.", [r"net cost.{0,60}2022", r"2022.{0,60}net cost"]),
    N("D2-NE2", "How many civil service employees work at Stennis Space Center?",
      "Infographic p13 không liệt kê SSC riêng (gộp trong 'Other'); không có số nào khác.", [r"Stennis.{0,80}\d[\d,]{2,} (employees|staff|people)"]),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip().lower()


def main():
    import pymupdf
    doc = pymupdf.open(PDF)
    pages = {i + 1: norm(p.get_text()) for i, p in enumerate(doc)}
    for split, items, none in (("test", TEST, TEST_NO), ("dev", DEV + DEV2, DEV_NO + DEV2_NO)):
        for q in items:
            assert q["group"] in GROUPS, q["id"]
            for e in q["evidence"]:
                if e["quote"]:
                    assert norm(e["quote"]) in pages[e["page"]], f"{q['id']}: quote not on p{e['page']}: {e['quote']}"
                else:
                    assert e["visual_only"], q["id"]
            if q["group"] == "multihop":
                assert len({e["page"] for e in q["evidence"]}) >= 2, q["id"]
        for n in none:
            for pat in n["grep_checked"]:
                hits = [k for k, t in pages.items() if re.search(pat, t, re.I)]
                assert not hits, f"{n['id']}: pattern {pat!r} found on {hits}"
        recs = [{**q, "split": split} for q in items] + [{**n, "split": split} for n in none]
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{split}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts = {g: sum(q["group"] == g for q in items) for g in GROUPS}
        print(f"{split}: {len(items)} answerable {counts} + {len(none)} no-evidence = {len(recs)}")
    # dev/test must not share a question
    t, d = {q["question"] for q in TEST}, {q["question"] for q in DEV + DEV2}
    assert not (t & d)


if __name__ == "__main__":
    main()
