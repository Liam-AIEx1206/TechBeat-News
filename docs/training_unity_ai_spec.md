# SPEC: Training Unity AI — "Làm việc với AI như một tech lead"

> **Cách dùng file này:**
> - Đưa toàn bộ file này vào AI (Claude/ChatGPT/Gemini/Gamma) và yêu cầu: *"Tạo slide PowerPoint/Google Slides theo spec này. Mỗi đề mục `## Slide X.Y` là 1 slide riêng."*
> - Hoặc đưa cho designer làm thủ công — mỗi `## Slide X.Y` là 1 slide, đã có sẵn tiêu đề, nội dung, ghi chú trình bày.
> - File này tự đầy đủ — không cần đọc tài liệu khác.

---

## 0. METADATA — Đọc trước khi tạo slide

### Người nghe
- Đối tượng: team dev hỗn hợp (junior + mid + senior), một số non-dev có thể có mặt
- Trình độ AI: mới tiếp xúc Cursor, Antigravity, Claude Code — chưa thành thạo
- Đau hiện tại: AI tạo bug, AI sửa file ngoài scope, mất thời gian fix bug AI, không biết "điều khiển" AI

### Định dạng buổi
- Thời lượng: **2 giờ**
- Hình thức: **thuyết trình, không thực hành**
- Tổng số slide: **21 slide nội dung + 1 title + 1 closing = 23 slide**
- Phân bổ: 5 khối nội dung (15 / 35 / 30 / 30 / 10 phút)

### Spine (ý xuyên suốt)
> **"AI là junior dev rất giỏi. Bạn là tech lead."**
>
> Spine này phải xuất hiện ở: slide mở đầu, giữa mỗi khối, và slide tổng kết. Tối thiểu 3 lần.

### Mục tiêu sau buổi
1. Team đổi mindset: AI cần được brief và quản lý, không phải hỏi rồi tin
2. Team nhớ được 3 quy tắc cốt lõi (xem slide 5.2)
3. Team có cheatsheet 1 trang mang về áp dụng tuần đó

### Nguyên tắc thiết kế slide
- **1 slide = 1 ý.** Không nhồi bullet.
- **Ngôn ngữ của dev**, không phải ngôn ngữ giảng dạy. Dùng "AI sửa file lung tung" thay vì "scope không kiểm soát".
- **Code block và bảng được phép**, vì người nghe là dev — họ đọc được.
- **Mọi câu Vietnamese phải có dấu đầy đủ.** Tránh font không hỗ trợ dấu tiếng Việt.
- **Sentence case** cho tiêu đề (không ALL CAPS).
- **Tông màu**: dùng cam (#F97316 hoặc tương tự) làm màu nhấn — match brand "XGAME STUDIO" trên slide gốc.
- **Logo XGAME STUDIO** ở góc trên trái mỗi slide.
- **Số slide + tên section** ở footer.

### Quy ước trong file này
- `**ND:**` = nội dung hiển thị trên slide
- `**GHI CHÚ:**` = ghi chú dành cho speaker, KHÔNG hiển thị
- `**LAYOUT:**` = gợi ý bố cục slide
- Code block là code/prompt thật, hiển thị trên slide nguyên văn

---

# KHỐI 1 — MỞ ĐẦU (15 phút, 5 slide)

## Slide 1.1 — Title slide

**LAYOUT:** Slide bìa, tiêu đề lớn giữa slide, subtitle nhỏ phía dưới.

**ND tiêu đề:**
Training Unity AI

**ND subtitle:**
Làm việc với AI như một tech lead

**ND footer phải:**
Tháng 5 / 2026

**GHI CHÚ speaker:**
- Đọc to tiêu đề + subtitle. Subtitle là frame quan trọng — đừng bỏ qua.
- Câu mở: "2 giờ tới, chúng ta không học prompt. Chúng ta học cách giao việc."

---

## Slide 1.2 — Câu hỏi mở

**LAYOUT:** Chỉ 1 câu duy nhất, font cực lớn, giữa slide. Không bullet, không hình.

**ND:**
Tuần vừa rồi, bạn mất bao lâu để fix bug do AI tạo ra?

**GHI CHÚ speaker:**
- Đọc to câu hỏi.
- Im lặng 10-20 giây. Quan trọng — đừng cứu lấp.
- Có thể chỉ định 1-2 người trả lời ngẫu nhiên. Mục đích KHÔNG phải lấy data — mà kích hoạt ký ức đau.
- Khi họ vừa nhớ ra một case cụ thể, họ sẽ chăm chú hơn rất nhiều ở phần tiếp theo.

---

## Slide 1.3 — Đau thật của chúng ta

**LAYOUT:** Bảng 2 cột chiếm gần hết slide. Tiêu đề slide nhỏ phía trên.

**ND tiêu đề slide:**
Đau thật của chúng ta

**ND bảng:**

| Cái bạn nghĩ AI sẽ làm | Cái thực sự xảy ra |
|---|---|
| "Bảo nó sửa bug, nó sửa" | Nó sửa nhưng đẻ ra 2 bug khác |
| "Bảo nó tối ưu, nó tối ưu" | Nó refactor cả file không liên quan |
| "Bảo nó viết feature, nó viết" | Code chạy nhưng logic sai |
| "Đỡ tốn thời gian" | Fix bug AI lâu hơn tự code |

**GHI CHÚ speaker:**
- Đừng đọc hết bảng. Chỉ vào 1-2 dòng, để người nghe tự đọc.
- Hỏi: "Có ai chưa từng gặp dòng nào trong bảng này không?" — kỳ vọng không ai giơ tay.
- Đây là moment đồng cảm. Không kéo dài quá 90 giây.

---

## Slide 1.4 — Sự thật khó nghe

**LAYOUT:** 1 câu lớn giữa slide, 1 câu nhỏ phía dưới.

**ND câu chính (lớn):**
Vấn đề không phải AI dở.

**ND câu phụ (nhỏ hơn, ngay dưới):**
Vấn đề là chúng ta giao việc cho AI sai cách.

**ND footer (nhỏ nhất):**
Y như khi giao task mơ hồ cho junior dev — nhận lại code không dùng được.

**GHI CHÚ speaker:**
- Đây là moment chuyển quan trọng. Nói chậm.
- Dừng giữa 2 câu chính. Để người nghe ngấm.
- Đây là câu khiến cả buổi training có ý nghĩa. Nếu mất câu này, cả buổi mất frame.

---

## Slide 1.5 — Frame cả buổi (SPINE)

**LAYOUT:** Tiêu đề lớn ở giữa, 3 bullet phía dưới, 1 footer.

**ND tiêu đề (cực lớn):**
AI là junior dev rất giỏi. Bạn là tech lead.

**ND 3 bullet:**
- **Junior giỏi:** code nhanh, biết nhiều ngôn ngữ, không mệt mỏi
- **Junior dở:** không biết project, không hiểu deadline, không biết phải hỏi gì
- **Tech lead:** brief rõ ràng → review chặt chẽ → kiểm soát scope

**ND footer:**
Cả buổi hôm nay = 4 kỹ năng của tech lead khi làm việc với junior.

**GHI CHÚ speaker:**
- Đây là SPINE. Sẽ lặp lại 3+ lần trong buổi.
- Hỏi: "Ai trong đây từng làm tech lead?" / "Ai từng được tech lead review code?" — kết nối kinh nghiệm cá nhân.
- Nói: "Mọi kỹ thuật chúng ta học hôm nay đều quay về 1 trong 3 vai trò: brief, review, kiểm soát scope."

---

# KHỐI 2 — GIAO VIỆC ĐÚNG (35 phút, 5 slide)

## Slide 2.1 — Tech lead không "hỏi", họ "brief"

**LAYOUT:** 2 khối code/text cạnh nhau, có ký hiệu ❌ và ✅ rõ ràng.

**ND tiêu đề:**
Tech lead không "hỏi", họ "brief"

**ND khối trái (đỏ/xám, có ❌):**
Câu hỏi (cách dev nói chuyện với nhau)

```
"Làm cho tao cái health system với"
```

**ND khối phải (xanh/cam, có ✅):**
Brief (cách tech lead giao task cho junior)

```
"Làm health system cho enemy.
Project Unity 6, đã có State Machine.
Yêu cầu:
- Máu dạng float
- Hiệu ứng nhấp nháy khi bị đánh
- Chết thì play animation rồi destroy sau 2s.

Trước khi code, liệt kê các class/file sẽ tạo."
```

**GHI CHÚ speaker:**
- Đọc to cả 2 prompt. Để người nghe tự thấy khác biệt.
- Hỏi: "Nếu bạn là AI, bạn làm được cái nào tốt hơn?" — câu trả lời hiển nhiên.
- Nhấn mạnh: "Prompt tốt KHÔNG dài hơn nhiều. Nó chỉ rõ ràng hơn."
- Không định nghĩa thuật ngữ ở đây. Để slide sau.

---

## Slide 2.2 — 4 thành phần của một brief tốt

**LAYOUT:** 4 box lớn, đánh số 1-4, mỗi box 1 thành phần. Có thể xếp 2x2 hoặc 4 hàng dọc.

**ND tiêu đề:**
4 thành phần của một brief tốt

**ND box 1:**
**1. VAI TRÒ**
AI là ai trong dự án này?
*"Bạn là Unity gameplay engineer"*

**ND box 2:**
**2. CONTEXT**
AI cần biết gì về project?
*Unity version, architecture đang dùng, convention, file liên quan*

**ND box 3:**
**3. TASK**
Chính xác phải làm gì?
*Một việc, có scope rõ. Không phải "làm cho xong feature"*

**ND box 4:**
**4. OUTPUT**
Trả về dạng gì?
*Plan? Code? File nào? Có comment không?*

**GHI CHÚ speaker:**
- Quan trọng: nhấn mạnh "4, không phải 7". Đếm trên 1 bàn tay.
- Có thể đề cập slide gốc có 7 thành phần — mình rút xuống 4 để dễ nhớ. 4 đủ để bắt đầu, người muốn học sâu sẽ tự đọc thêm.
- Không đi sâu định nghĩa — vì slide kế tiếp có ví dụ thật.

---

## Slide 2.3 — Demo before/after (SLIDE QUAN TRỌNG NHẤT KHỐI 2)

**LAYOUT:** Đây là slide DÀY. Có thể chia 2 slide (2.3a và 2.3b) nếu thiết kế chật. Hoặc dùng layout có 1 tiêu đề trên + 2 code block to bên dưới.

**ND tiêu đề:**
Cùng một task — 2 cách giao việc

**ND sub-tiêu đề:**
Task: "Thêm hệ thống loot drop khi enemy chết"

**ND khối ❌ PROMPT YẾU:**

```
"thêm loot drop khi enemy chết"
```

**Bên dưới khối ❌, ND:**
🤖 AI sẽ làm gì:
- Đoán loot là gì (item? gold? cả hai?)
- Tự sửa Enemy.cs theo cách của nó
- Có thể đụng vào InventoryManager, ItemDatabase
- Có thể tạo class mới mà bạn không biết
- Code "chạy được" nhưng không khớp pattern dự án

**ND khối ✅ BRIEF TỐT:**

```
[VAI TRÒ] Bạn là Unity gameplay engineer làm với codebase này.

[CONTEXT]
- Unity 6, đã có ScriptableObject ItemData cho item
- Enemy.cs đã có event OnDeath
- LootTable là field [SerializeField] trên Enemy prefab

[TASK]
Khi OnDeath fire, spawn item theo LootTable tại vị trí enemy.
Mỗi entry trong LootTable có dropRate (0-1).
KHÔNG sửa InventoryManager hay ItemData.

[OUTPUT]
1. Liệt kê file sẽ tạo / sửa
2. Code sạch, có XML comment cho public method
3. Chờ tôi confirm trước khi sửa file
```

**GHI CHÚ speaker:**
- Đây là slide QUAN TRỌNG NHẤT khối 2. Dành 5-7 phút.
- Đọc to cả 2 prompt — đặc biệt prompt tốt, đọc từng section.
- Hỏi: "Theo bạn AI sẽ làm tốt prompt nào hơn?" — câu trả lời hiển nhiên.
- Nhấn mạnh: prompt tốt dài hơn nhưng KHÔNG nhiều — đổi lại không phải fix bug.
- Mapping với slide 2.2: chỉ ra rõ [VAI TRÒ] [CONTEXT] [TASK] [OUTPUT] trong prompt tốt.

---

## Slide 2.4 — 3 lỗi prompt phổ biến nhất

**LAYOUT:** 3 khối ngang hoặc dọc. Mỗi khối có ❌ ✅ song song.

**ND tiêu đề:**
3 lỗi prompt phổ biến nhất

**ND khối lỗi 1:**

**Lỗi 1: Đại từ mơ hồ**
- ❌ "tối ưu cái này"
- ✅ "tối ưu hàm `CalculateDamage` ở `CombatSystem.cs` — đang chạy trong vòng lặp Update"

**ND khối lỗi 2:**

**Lỗi 2: Không nói được phép làm gì**
- ❌ "thêm tính năng X"
- ✅ "thêm X. Chỉ sửa file Y, Z. Không đụng tới A, B."

**ND khối lỗi 3:**

**Lỗi 3: Bảo code ngay, không cho suy nghĩ**
- ❌ "code cho tao cái này"
- ✅ "phân tích trước, đề xuất 2 cách, đợi tao chọn rồi mới code"

**GHI CHÚ speaker:**
- Đây là 3 lỗi sẽ chiếm 80% prompt kém của team.
- Hỏi: "Ai trong đây đã từng viết prompt giống ❌?" — kỳ vọng hầu hết giơ tay.
- Đừng nói lý thuyết. 3 cặp ❌/✅ tự nói lên hết.

---

## Slide 2.5 — Take-away khối 2

**LAYOUT:** 1 câu lớn giữa slide, 1 subtitle.

**ND câu lớn:**
Prompt = brief cho junior, không phải câu hỏi cho Google.

**ND subtitle:**
Junior cần biết: là ai, đang ở đâu, làm gì, trả gì.

**GHI CHÚ speaker:**
- Đọc to. Lặp lại spine: "AI là junior, bạn là tech lead — và tech lead viết brief."
- Sau slide này nghỉ 5 phút nếu thấy cần. Khối 2 đã dài (~35 phút).

---

# KHỐI 3 — KIỂM SOÁT SCOPE (30 phút, 6 slide)

## Slide 3.1 — Câu chuyện thật

**LAYOUT:** Storytelling slide. Chỉ text, font lớn, format kể chuyện.

**ND chính:**
Bạn bảo AI: *"fix bug ở UI button click"*.

5 phút sau, nó đã sửa **8 file**, đổi **3 namespace**, và thêm **1 design pattern mới** vào project.

**ND footer:**
*Quen không?*

**GHI CHÚ speaker:**
- Kể như chuyện thật. Dùng giọng "ai cũng từng gặp".
- Cười nhẹ với người nghe. Họ sẽ cười với mình.
- Hỏi: "Ai từng bị tương tự?" — gần như cả phòng giơ tay.
- Đây là pain point của khối 3 — đừng quên kích hoạt nó trước khi đi vào giải pháp.

---

## Slide 3.2 — Tại sao chuyện này xảy ra

**LAYOUT:** Tiêu đề lớn + 3 bullet giải thích.

**ND tiêu đề lớn:**
AI không biết "đủ rồi". Bạn phải nói.

**ND 3 bullet:**
Junior dev trong codebase mới sẽ:
- Thấy code "không đẹp" → muốn sửa
- Thấy có cơ hội refactor → tự refactor
- Không biết file nào "không được động" → động hết

**GHI CHÚ speaker:**
- Quay về spine: "AI hành xử y như junior chưa biết boundaries."
- Junior tốt sẽ hỏi. Junior chưa quen sẽ tự làm. AI cũng vậy — và mặc định nó tự làm.
- Trách nhiệm của tech lead = vẽ ranh giới TRƯỚC khi giao việc.

---

## Slide 3.3 — Quy tắc 1: Plan trước, Code sau

**LAYOUT:** Slide quan trọng nhất khối 3. Bố cục: tiêu đề lớn + danh sách + 1 box thần chú nổi bật.

**ND tiêu đề:**
Quy tắc 1 — Plan trước, Code sau

**ND mô tả:**
Trước khi cho AI sửa bất kỳ file nào, yêu cầu:
1. Liệt kê file sẽ sửa
2. Mô tả thay đổi cho từng file
3. Liệt kê rủi ro (cái gì có thể break)
4. **Chờ bạn duyệt** trước khi gõ một dòng code

**ND box thần chú (nổi bật, có khung):**

```
"Trước khi code, hãy trình bày kế hoạch.
Liệt kê file ảnh hưởng. Đợi tôi duyệt."
```

**GHI CHÚ speaker:**
- ĐÂY LÀ KỸ THUẬT QUAN TRỌNG NHẤT CẢ BUỔI.
- Nếu dev chỉ nhớ 1 thứ — phải là cái này.
- Lặp lại câu thần chú 3 lần. Yêu cầu cả phòng đọc theo 1 lần.
- Mention: paste câu này vào đầu mọi conversation lớn. Hoặc bỏ vào Cursor rules / Skill / system prompt.

---

## Slide 3.4 — Quy tắc 2: Chat mode vs Agent mode

**LAYOUT:** Bảng 2 cột so sánh + quy tắc ngắn phía dưới.

**ND tiêu đề:**
Quy tắc 2 — Chat mode vs Agent mode

**ND bảng:**

| Chat mode (Ctrl+L) | Agent mode (Ctrl+I) |
|---|---|
| AI nói chuyện, không sửa file | AI tự sửa file, tự chạy command |
| Bạn copy code thủ công | Bạn approve / reject từng change |
| Dùng khi: hỏi, học, design | Dùng khi: task rõ ràng, scope hẹp |
| Rủi ro thấp | Rủi ro CAO nếu prompt kém |

**ND quy tắc (box nổi bật):**

Quy tắc:
- Task không rõ → **Chat mode**
- Task rõ + scope hẹp → **Agent mode**
- Đang khám phá → **KHÔNG BAO GIỜ Agent mode**

**GHI CHÚ speaker:**
- Team mới dùng Cursor / Antigravity rất hay sai chỗ này. Họ bật Agent mode cho mọi thứ.
- Đây là nguyên nhân CHÍNH của "AI sửa file lung tung" — quan trọng hơn cả prompt tốt.
- Nếu có thời gian, demo nhanh Cursor: Ctrl+L vs Ctrl+I trên máy thật.
- Nếu thời lượng không thực hành: chỉ cần show screenshot.

---

## Slide 3.5 — Quy tắc 3: Một task, một chat

**LAYOUT:** 2 cột — bên trái "Khi nào mở chat mới", bên phải "Dấu hiệu AI đã lú".

**ND tiêu đề:**
Quy tắc 3 — Một task, một chat

**ND cột trái:**
Khi nào mở chat mới?
- ✅ Task mới, không liên quan task cũ
- ✅ AI đã "lú" — quên yêu cầu, lặp lại lỗi, sửa lại cái vừa sửa
- ✅ Chat đã quá dài (>30 lượt)
- ✅ Đổi chiến lược lớn (đang refactor → chuyển sang debug)

**ND cột phải:**
Dấu hiệu AI đã lú:
- Hỏi lại thứ bạn đã nói
- "Tôi xin lỗi, bạn nói đúng" liên tục
- Đề xuất lại giải pháp bạn vừa reject

**GHI CHÚ speaker:**
- Nhiều dev cứ chat mãi vì "ngại mất context". Thực ra context đã hỏng từ lâu.
- Mở chat mới + tóm tắt → nhanh hơn dò trong chat dài.
- Mẹo: dùng AI tóm tắt chat hiện tại trước khi mở chat mới. Paste tóm tắt làm context.

---

## Slide 3.6 — Take-away khối 3

**LAYOUT:** 1 câu lớn + 3 bullet quy tắc.

**ND câu lớn:**
AI không biết "đủ rồi". Bạn phải vẽ ranh giới.

**ND 3 bullet:**
1. Plan trước, code sau
2. Chat mode trừ khi chắc chắn
3. Một task, một chat

**GHI CHÚ speaker:**
- Lặp lại 3 quy tắc lần cuối. Yêu cầu cả phòng nhắc lại.
- Nói: "3 quy tắc này có trong cheatsheet cuối buổi. Tuần sau, mỗi lần định bật Agent mode, nhớ slide này."

---

# KHỐI 4 — VERIFY & SCALE (30 phút, 6 slide)

## Slide 4.1 — Sự thật về code AI

**LAYOUT:** 1 câu lớn + bảng so sánh 2 dòng.

**ND câu lớn:**
Code AI luôn trông đúng. Đó là vấn đề.

**ND bảng:**

| | |
|---|---|
| Junior viết code sai | Trông sai → bạn để ý → review |
| **AI viết code sai** | **Trông đúng → bạn tin → merge → bug production** |

**GHI CHÚ speaker:**
- Đây là cái khiến "fix bug AI lâu hơn tự code" — bug giấu trong code trông sạch sẽ.
- Hỏi: "Ai từng accept code AI, sau đó phát hiện sai sau 2 ngày?" — nhiều cánh tay sẽ giơ.
- Đây là pain point của khối 4. Kích hoạt trước khi đưa giải pháp.

---

## Slide 4.2 — 5 dấu hiệu code AI "trông đúng mà sai"

**LAYOUT:** 5 bullet to + 1 box quy tắc bên dưới.

**ND tiêu đề:**
5 dấu hiệu code AI "trông đúng mà sai"

**ND 5 bullet:**
1. **Method tên đúng, nội dung không khớp** — `CalculateDamage` mà không nhân với armor
2. **Dùng API không tồn tại** — gọi `UnityEngine.X.Y()` mà Unity không có
3. **Logic ngược dấu** — `if (hp > 0)` thay vì `if (hp <= 0)` chết
4. **Edge case bị bỏ qua** — null check, mảng rỗng, divide by zero
5. **"Quá hoàn hảo"** — code dài, có comment đẹp, nhưng không khớp pattern dự án

**ND box quy tắc:**
Quy tắc đọc code AI:
- Đọc TỪNG DÒNG
- Đặc biệt nghi ngờ những đoạn "có vẻ thông minh"
- So với code đã có trong dự án — có giống pattern không?

**GHI CHÚ speaker:**
- Nếu có thời gian, lấy 1 đoạn code AI thật từ project team — chỉ ra bug. Resonate hơn 10 slide.
- Mention: AI "ảo giác" API là vấn đề rất phổ biến với Unity vì có nhiều version khác nhau.
- Câu nói: "Code AI không phải 'sai' — nó là 'chưa đúng'. Đó là việc của bạn."

---

## Slide 4.3 — Kỹ thuật verify: bắt AI tự giải thích

**LAYOUT:** 1 prompt thần chú nổi bật + giải thích.

**ND tiêu đề:**
Kỹ thuật verify: bắt AI tự giải thích

**ND mô tả:**
Trước khi accept code, hỏi:

**ND box thần chú:**

```
"Giải thích từng dòng cho tôi.
Tại sao chọn cách này thay vì cách khác?
Code này sẽ fail trong trường hợp nào?"
```

**ND giải thích:**
Tại sao hiệu quả:
- AI bị buộc "nghĩ lại" — thường tự phát hiện lỗi của chính nó
- Bạn hiểu code → review thật, không phải fake review
- Nếu AI không giải thích được → đừng dùng code đó

**GHI CHÚ speaker:**
- Đây là kỹ thuật MIỄN PHÍ, dùng được NGAY. Không cần tool mới.
- Hôm nay bảo dev áp dụng → tuần sau họ làm được.
- Kết hợp với Plan trước Code (slide 3.3) là 2 kỹ thuật mạnh nhất cả buổi.

---

## Slide 4.4 — Khi feature lớn: Phases & Tasks

**LAYOUT:** Tiêu đề + sơ đồ cấu trúc folder + workflow.

**ND tiêu đề:**
Khi feature lớn: Phases & Tasks

**ND mô tả:**
Prompt tốt cũng không đủ khi feature quá to (inventory system, multiplayer, save / load).
**Giải pháp: chia thành phases và tasks.**

**ND cấu trúc folder (dạng tree, font monospace):**

```
📁 Feature: Inventory System
   📄 overview.md (mô tả toàn bộ + các phase)
   📁 phase_1_data_layer/
      📄 overview.md
      📄 task_1_item_scriptable_object.md
      📄 task_2_inventory_data_model.md
   📁 phase_2_ui/
      📄 overview.md
      📄 task_1_grid_view.md
      ...
```

**ND workflow:**
1. AI tạo overview tổng → bạn duyệt
2. AI tạo overview phase 1 → bạn duyệt
3. AI làm task 1 trong phase 1 → bạn review
4. Lặp lại

**GHI CHÚ speaker:**
- Đây là phần workflow mạnh nhất.
- Nhấn mạnh: đây là WORKFLOW, không phải tool. Áp dụng được ở mọi AI tool.
- Lợi ích: AI không lú giữa chừng vì context được chia nhỏ, mỗi task có scope rõ.
- Đừng đi quá sâu cấu hình — chỉ giới thiệu khái niệm. Để buổi follow-up nếu có.

---

## Slide 4.5 — Skill: khi bạn lặp lại workflow

**LAYOUT:** Tiêu đề + 1 ví dụ skill file + use cases.

**ND tiêu đề:**
Skill: khi bạn lặp lại workflow

**ND định nghĩa:**
**Skill = file markdown chứa instructions tái sử dụng.**

**ND ví dụ skill file (font monospace, box):**

```
📄 unity-feature-skill.md

Khi user yêu cầu thêm gameplay feature:
1. Luôn tạo plan trước, không code ngay
2. Tuân theo coding convention: PascalCase,
   brace mở dòng mới
3. Dùng pattern hiện có:
   - ScriptableObject cho config
   - State Machine cho behavior
4. Mọi public method phải có XML comment
5. Không tự ý sửa file ngoài scope task
```

**ND use cases:**
Khi nào dùng Skill:
- Có workflow lặp đi lặp lại (feature mới, code review, refactor)
- Có convention chung cả team phải tuân
- Onboard member mới — họ chỉ cần dùng skill, không cần học prompt

**GHI CHÚ speaker:**
- Đừng đi sâu vào cấu hình kỹ thuật của từng tool (Cursor rules vs Claude skill...).
- Chỉ giới thiệu khái niệm + lợi ích.
- Có thể nói: "Tuần sau, một trong các bạn sẽ thử tạo skill cho team — chúng ta sẽ review chung."
- Đây là cách scale workflow toàn team — quan trọng cho team lead nghe.

---

## Slide 4.6 — Take-away khối 4

**LAYOUT:** 1 câu lớn giữa slide.

**ND câu lớn:**
Review code AI nghiêm hơn code đồng nghiệp. Vì nó trông đúng hơn.

**GHI CHÚ speaker:**
- Nếu dev chỉ nhớ 1 câu cả buổi — đây phải là câu này.
- Chống lại bản năng "AI nó giỏi, tin nó đi".
- Nói chậm. Đọc 2 lần nếu cần.

---

# KHỐI 5 — TỔNG KẾT (10 phút, 4 slide)

## Slide 5.1 — Quay lại spine

**LAYOUT:** Tiêu đề lớn + bảng tổng kết.

**ND tiêu đề:**
AI là junior dev. Bạn là tech lead.

**ND bảng:**

| Vai trò tech lead | Kỹ thuật hôm nay học |
|---|---|
| Brief rõ ràng | 4 thành phần: Vai trò, Context, Task, Output |
| Kiểm soát scope | Plan trước Code, Chat vs Agent, một task một chat |
| Review chặt | Đọc từng dòng, bắt AI giải thích, 5 dấu hiệu sai |
| Scale workflow | Phases & Tasks, Skill |

**GHI CHÚ speaker:**
- Đọc to bảng. Để người nghe thấy mạch xuyên suốt 2 giờ.
- Nhấn: "Mọi kỹ thuật bạn học hôm nay đều quay về spine này."

---

## Slide 5.2 — 3 quy tắc cuối cùng (SLIDE TO NHẤT)

**LAYOUT:** 3 dòng to giữa slide. KHÔNG bullet. KHÔNG trang trí. Mỗi dòng đánh số to.

**ND tiêu đề nhỏ phía trên:**
Nếu chỉ nhớ 3 thứ về làm:

**ND 3 dòng (font CỰC LỚN):**

**1. Brief, không hỏi.**

**2. Plan trước, code sau.**

**3. Đọc từng dòng AI viết.**

**GHI CHÚ speaker:**
- Đây là MOMENT QUAN TRỌNG NHẤT cả buổi.
- Đọc to TỪNG DÒNG, dừng 2-3 giây giữa các dòng.
- Yêu cầu cả phòng đọc theo 1 lần.
- Đảm bảo dev khi về vẫn nhớ 3 dòng này — kể cả khi quên hết slide khác.

---

## Slide 5.3 — Cheatsheet mang về

**LAYOUT:** 1 thumbnail ảnh của cheatsheet ở giữa + 1 call-to-action.

**ND tiêu đề:**
Cheatsheet mang về

**ND mô tả:**
File này có đính kèm — tải về máy hoặc in ra để ở bàn làm việc.

**ND footer:**
Mỗi lần định prompt AI, mở cái này ra.
2 tuần là thành phản xạ.

**GHI CHÚ speaker:**
- Show cheatsheet thật trên màn hình.
- Có thể in trước + phát ra phòng — dev sẽ giữ nó tốt hơn file PDF.
- Nhắc: cheatsheet không phải để học — để PHẢN XẠ. Mỗi lần định gõ prompt, mở ra.

---

## Slide 5.4 — Bước tiếp theo + Q&A

**LAYOUT:** 2 cột: tuần này / tuần sau + footer Q&A.

**ND tiêu đề:**
Bước tiếp theo

**ND cột "Tuần này":**
Tuần này:
- Áp dụng "Plan trước, code sau" cho mọi feature mới
- Mỗi lần Accept code AI, hỏi "giải thích từng dòng" trước

**ND cột "Tuần sau":**
Tuần sau:
- Thử tạo 1 Skill cho team
- Thử workflow Phases & Tasks cho 1 feature lớn

**ND footer to:**
Hỏi đáp

**GHI CHÚ speaker:**
- Đặt deadline cụ thể: "tuần này", "tuần sau" — không phải "khi nào đó".
- Hỏi: "Ai cam kết thử Plan trước Code trong tuần này?" — giơ tay.
- Chuyển sang Q&A. Dành ít nhất 5 phút cho phần này.

---

# PHỤ LỤC A — CHEATSHEET (1 trang in ra)

> File này nên thiết kế trên A4 ngang, in được 1 mặt, phát cho team cuối buổi.

```
═══════════════════════════════════════════════════════════════════
                AI = JUNIOR DEV. BẠN = TECH LEAD.
═══════════════════════════════════════════════════════════════════

📝 BRIEF (4 thành phần)
   [VAI TRÒ]  AI đóng vai gì? (Unity engineer, gameplay dev...)
   [CONTEXT]  Project, version, architecture, file liên quan
   [TASK]     1 việc, scope rõ, không "làm cho xong feature"
   [OUTPUT]   Plan? Code? Chờ duyệt? Comment?

🚧 KIỂM SOÁT SCOPE (3 quy tắc)
   1. Plan trước, code sau
      → "Trình bày kế hoạch + file ảnh hưởng. Chờ tôi duyệt."
   2. Chat mode trừ khi chắc chắn
      → Agent mode chỉ khi scope rõ + task hẹp
   3. Một task, một chat
      → AI lú → mở chat mới + tóm tắt

🔍 VERIFY CODE AI (5 dấu hiệu sai)
   □ Method tên đúng, nội dung sai
   □ API không tồn tại
   □ Logic ngược dấu
   □ Edge case bị bỏ qua
   □ "Quá hoàn hảo", không khớp pattern

   Câu thần chú:
   "Giải thích từng dòng. Tại sao chọn cách này?
    Code này fail trong case nào?"

📈 FEATURE LỚN: PHASES & TASKS
   overview.md → phase_x/overview.md → phase_x/task_y.md
   Duyệt từng cấp trước khi xuống cấp dưới.

═══════════════════════════════════════════════════════════════════
                    3 quy tắc cuối:
                    1. Brief, không hỏi
                    2. Plan trước, code sau
                    3. Đọc từng dòng AI viết
═══════════════════════════════════════════════════════════════════
```

---

# PHỤ LỤC B — GỢI Ý PROMPT TẠO SLIDE TỪ FILE NÀY

Nếu bạn muốn dùng AI tạo slide tự động, copy nguyên file này vào ChatGPT/Claude/Gemini với prompt sau:

```
Bạn là một chuyên gia thiết kế slide training cho dev.

Dưới đây là spec đầy đủ cho buổi training Unity AI 2 giờ.
File spec tự đầy đủ — KHÔNG cần hỏi thêm thông tin.

YÊU CẦU:
1. Tạo file PowerPoint (.pptx) theo spec.
2. Mỗi đề mục `## Slide X.Y` = 1 slide riêng.
3. Tuân thủ:
   - Tông màu cam (#F97316), match brand XGAME STUDIO
   - Sentence case cho tiêu đề
   - Font hỗ trợ tiếng Việt đầy đủ (Inter, Roboto, hoặc tương tự)
   - 1 ý / 1 slide, không nhồi bullet
   - Code block hiển thị font monospace, có background tối
4. Bỏ qua phần `**GHI CHÚ speaker:**` khi render slide — chỉ dùng để hiểu intent.
5. Đặt `**GHI CHÚ speaker:**` vào phần Notes của slide (Speaker Notes).
6. Thêm số slide + tên section ở footer.
7. Thêm logo placeholder "XGAME STUDIO" ở góc trên trái mọi slide nội dung.

CHẤT LƯỢNG:
- Slide phải dễ nhìn trên màn chiếu 1080p
- Không text dưới 18pt
- Có khoảng trắng đủ, không bịt kín slide

[Paste toàn bộ file spec ở đây]
```

---

**HẾT SPEC.**
