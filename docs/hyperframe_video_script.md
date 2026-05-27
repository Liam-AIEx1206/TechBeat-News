# HYPERFRAME — Training Unity AI (Video Priming)

> **Mục đích:** video ngắn ~15-20 phút cho team xem TRƯỚC buổi training 2h.
> Sau khi xem, người ta đã có mindset và từ vựng — buổi training sẽ chỉ đào sâu, không phải bắt đầu từ đầu.

---

## METADATA

- **Tổng số frame:** 23
- **Thời lượng dự kiến:** ~17 phút
- **Ngôn ngữ:** Vietnamese (giữ thuật ngữ tiếng Anh: prompt, context, scope, code, refactor, agent, chat, plan, brief)
- **Tông giọng narration:** thân thiện, như senior dev chia sẻ với đồng nghiệp. KHÔNG hàn lâm, KHÔNG đọc bài.
- **Visual style:** minimal, tông cam (#F97316) match brand XGAME STUDIO, font sans-serif hỗ trợ tiếng Việt (Inter/Be Vietnam Pro)

### Quy ước

- `[NARRATION]` = lời voiceover, đọc lên thành audio
- `[ON_SCREEN]` = nội dung text hiển thị trên màn hình
- `[VISUAL]` = mô tả visual/animation
- `[DURATION]` = thời lượng frame (giây)
- `[TRANSITION]` = chuyển cảnh sang frame kế tiếp

### Quy tắc viết narration

- Câu ngắn, < 15 từ mỗi câu
- Đọc thành tiếng phải tự nhiên — viết như nói, không như viết
- Không dùng từ Hán-Việt khó (ưu tiên "vấn đề" hơn "vấn nạn")
- Pause tự nhiên — dùng dấu `,` và `.` đúng chỗ để TTS ngắt nhịp đúng

---

# FRAME 1 — Hook

**[DURATION]** 8 giây

**[ON_SCREEN]**
```
Training Unity AI
Làm việc với AI như một tech lead
```
*(Tiêu đề lớn fade in, subtitle xuất hiện sau 1s)*

**[NARRATION]**
> Hai giờ tới, chúng ta không học cách viết prompt. Chúng ta học cách giao việc cho AI.

**[VISUAL]** Background trắng, logo XGAME STUDIO góc trái. Chữ "Training Unity AI" fade in to dần. Subtitle xuất hiện sau.

**[TRANSITION]** Fade to next

---

# FRAME 2 — Pain point hook

**[DURATION]** 12 giây

**[ON_SCREEN]**
```
Tuần vừa rồi,
bạn mất bao lâu để fix bug
do AI tạo ra?
```
*(Mỗi dòng xuất hiện cách nhau 1s)*

**[NARRATION]**
> Câu hỏi đầu tiên. Tuần vừa rồi… bạn mất bao lâu để fix bug do AI tạo ra? Một tiếng? Hai tiếng? Cả buổi chiều?

**[VISUAL]** Chữ to giữa màn hình, hiện từng dòng theo nhịp đọc. Pause 2-3 giây cuối để người xem ngấm.

**[TRANSITION]** Slide left

---

# FRAME 3 — Đau thật

**[DURATION]** 50 giây

**[ON_SCREEN]** *(Bảng 2 cột, xuất hiện từng dòng theo narration)*

| Cái bạn nghĩ AI sẽ làm | Cái thực sự xảy ra |
|---|---|
| "Bảo nó sửa bug, nó sửa" | Nó sửa, nhưng đẻ ra 2 bug khác |
| "Bảo nó tối ưu, nó tối ưu" | Nó refactor cả file không liên quan |
| "Bảo nó viết feature, nó viết" | Code chạy, nhưng logic sai |
| "Đỡ tốn thời gian" | Fix bug AI lâu hơn tự code |

**[NARRATION]**
> Câu chuyện quen thuộc.
>
> Bạn bảo AI sửa bug — nó sửa, nhưng đẻ ra hai bug khác.
>
> Bạn bảo nó tối ưu — nó refactor cả file không liên quan.
>
> Bạn bảo nó viết feature — code chạy được, nhưng logic sai.
>
> Bạn nghĩ AI giúp đỡ tốn thời gian. Thực tế? Fix bug của nó lâu hơn tự code.

**[VISUAL]** Hai cột table. Cột trái màu xám (cái mình kỳ vọng), cột phải màu cam (cái thực sự). Mỗi cặp dòng xuất hiện cùng lúc khi narrator đọc đến.

**[TRANSITION]** Fade

---

# FRAME 4 — Sự thật khó nghe

**[DURATION]** 15 giây

**[ON_SCREEN]**
```
Vấn đề không phải AI dở.

Vấn đề là chúng ta
giao việc cho AI sai cách.
```
*(Dòng 1 xuất hiện trước, pause 2s, dòng 2 xuất hiện)*

**[NARRATION]**
> Sự thật khó nghe đây.
>
> *(pause 1s)*
>
> Vấn đề không phải AI dở.
>
> *(pause 2s)*
>
> Vấn đề là chúng ta… giao việc cho AI sai cách.

**[VISUAL]** Chỉ text, không hình. Font cực to. Background trắng. Câu thứ hai có dòng "giao việc cho AI sai cách" highlight màu cam.

**[TRANSITION]** Slide up

---

# FRAME 5 — Spine

**[DURATION]** 35 giây

**[ON_SCREEN]**
```
AI là junior dev rất giỏi.
Bạn là tech lead.
```

*(Sau 3 giây, 3 bullet hiện ra bên dưới:)*

- **Junior giỏi**: code nhanh, biết nhiều thứ, không mệt
- **Junior dở**: không biết project, không biết phải hỏi gì
- **Tech lead**: brief rõ → review chặt → kiểm soát scope

**[NARRATION]**
> Đây là cách nghĩ đúng về AI.
>
> AI là một junior dev rất giỏi. Bạn là tech lead.
>
> Junior giỏi thì sao? Code nhanh, biết nhiều ngôn ngữ, không bao giờ mệt.
>
> Nhưng junior cũng dở. Không biết project. Không hiểu deadline. Không biết phải hỏi cái gì.
>
> Và tech lead làm gì với junior? Ba việc. Brief rõ ràng. Review chặt chẽ. Kiểm soát scope.
>
> Cả video này là về ba việc đó.

**[VISUAL]** Câu tiêu đề lớn ở trên. Ba bullet xuất hiện lần lượt theo narration. Mỗi bullet có icon nhỏ: 👍 cho junior giỏi, 🤔 cho junior dở, 🎯 cho tech lead.

**[TRANSITION]** Slide left to "Phần 1: Brief"

---

# FRAME 6 — Chuyển section: Phần 1

**[DURATION]** 4 giây

**[ON_SCREEN]**
```
PHẦN 1

Brief, không hỏi
```

**[NARRATION]**
> Phần một. Brief, không hỏi.

**[VISUAL]** Background cam đậm. Chữ trắng. Như card chuyển scene phim.

**[TRANSITION]** Fade

---

# FRAME 7 — Brief vs Hỏi

**[DURATION]** 45 giây

**[ON_SCREEN]** *(2 khối song song)*

```
❌ Câu hỏi
"Làm cho tao cái health system với"
```

```
✅ Brief
"Làm health system cho enemy.
Project Unity 6, đã có State Machine.
Yêu cầu:
- Máu dạng float
- Hiệu ứng nhấp nháy khi bị đánh
- Chết thì play animation rồi destroy sau 2s

Trước khi code, liệt kê các class sẽ tạo."
```

**[NARRATION]**
> Cùng một việc, hai cách nói.
>
> Cách thứ nhất. "Làm cho tao cái health system với." Đây là câu hỏi — kiểu nói với đồng nghiệp.
>
> Cách thứ hai. Làm health system cho enemy. Project Unity 6. Đã có State Machine. Yêu cầu cụ thể. Trước khi code, liệt kê class sẽ tạo.
>
> Đây là brief. Kiểu giao task cho junior.
>
> Bạn nhận cái nào, làm tốt hơn?

**[VISUAL]** Khối trái nhỏ, khối phải lớn hơn. Khối trái viền đỏ nhạt, khối phải viền cam. Code block font monospace.

**[TRANSITION]** Slide up

---

# FRAME 8 — 4 thành phần brief

**[DURATION]** 50 giây

**[ON_SCREEN]** *(4 box xuất hiện lần lượt theo narration)*

```
4 thành phần của một brief tốt

[1] VAI TRÒ    → AI đóng vai gì?
[2] CONTEXT    → Project, version, file liên quan
[3] TASK       → Một việc, scope rõ
[4] OUTPUT     → Plan? Code? File nào?
```

**[NARRATION]**
> Một brief tốt có bốn thành phần. Đếm trên một bàn tay.
>
> Một. Vai trò. AI đóng vai gì? Unity engineer? Gameplay dev? Backend?
>
> Hai. Context. Project nào? Version mấy? File nào liên quan?
>
> Ba. Task. Chính xác làm gì? Một việc thôi, scope rõ. Không phải "làm cho xong feature".
>
> Bốn. Output. Trả về cái gì? Plan? Code? Có comment không? Chờ duyệt hay làm luôn?
>
> Bốn thành phần. Nhớ được không?

**[VISUAL]** 4 box xếp dọc. Mỗi box xuất hiện khi narrator đến. Số to bên trái, label ngắn bên phải.

**[TRANSITION]** Fade

---

# FRAME 9 — Demo before/after

**[DURATION]** 75 giây

**[ON_SCREEN]** *(Chia 2 phần — phần 1 hiện trước, phần 2 hiện sau theo narration)*

**Phần 1:**
```
Task: Thêm loot drop khi enemy chết

❌ Prompt yếu:
"thêm loot drop khi enemy chết"
```

**Phần 2:**
```
✅ Brief tốt:

[VAI TRÒ] Unity gameplay engineer làm với codebase này.

[CONTEXT]
- Unity 6, có ScriptableObject ItemData
- Enemy.cs có event OnDeath
- LootTable là field [SerializeField] trên Enemy

[TASK]
Khi OnDeath fire, spawn item theo LootTable.
Mỗi entry có dropRate (0-1).
KHÔNG sửa InventoryManager hay ItemData.

[OUTPUT]
1. Liệt kê file sẽ tạo/sửa
2. Code sạch, XML comment cho public method
3. Chờ tôi confirm trước khi sửa file
```

**[NARRATION]**
> Ví dụ thật. Task: thêm loot drop khi enemy chết.
>
> Cách thứ nhất. "Thêm loot drop khi enemy chết." Hết.
>
> *(pause 1s)*
>
> AI nhận cái này sẽ làm gì? Đoán loot là item hay gold. Tự sửa Enemy. Có thể đụng InventoryManager. Tạo class mới mà bạn không biết.
>
> *(pause 2s)*
>
> Bây giờ xem brief tốt.
>
> *(narrator chậm rãi đọc qua các section)*
>
> Vai trò: Unity gameplay engineer.
>
> Context: Unity 6, có ScriptableObject ItemData. Enemy đã có event OnDeath. LootTable là SerializeField.
>
> Task: rất cụ thể. Khi OnDeath fire, spawn theo LootTable. Mỗi entry có dropRate. Không sửa file ngoài.
>
> Output: liệt kê file, code sạch, chờ duyệt.
>
> Brief dài hơn. Nhưng đổi lại không phải fix bug.

**[VISUAL]** Frame quan trọng — có thể dài hơn các frame khác. Khối ❌ ở trên, khối ✅ ở dưới. Khi narrator đọc đến mỗi section trong brief tốt, section đó được highlight cam.

**[TRANSITION]** Slide up

---

# FRAME 10 — 3 lỗi prompt phổ biến

**[DURATION]** 55 giây

**[ON_SCREEN]** *(3 cặp ❌✅ xuất hiện lần lượt)*

```
3 lỗi prompt phổ biến nhất

Lỗi 1: Đại từ mơ hồ
❌ "tối ưu cái này"
✅ "tối ưu hàm CalculateDamage ở CombatSystem.cs"

Lỗi 2: Không nói scope
❌ "thêm tính năng X"
✅ "thêm X. Chỉ sửa file Y, Z. Không đụng A, B."

Lỗi 3: Code ngay, không suy nghĩ
❌ "code cho tao"
✅ "phân tích, đề xuất 2 cách, đợi tao chọn rồi code"
```

**[NARRATION]**
> Ba lỗi prompt phổ biến nhất. Chiếm tám mươi phần trăm prompt kém.
>
> Lỗi một. Đại từ mơ hồ. "Tối ưu cái này." Cái nào? File nào? Đổi sang: "tối ưu hàm CalculateDamage ở CombatSystem.cs". Rõ ràng.
>
> Lỗi hai. Không nói scope. "Thêm tính năng X." AI sẽ động vào mọi file nó nghĩ liên quan. Đổi sang: "thêm X. Chỉ sửa file Y, Z. Không đụng A, B."
>
> Lỗi ba. Bắt code ngay, không cho suy nghĩ. "Code cho tao." AI nhảy thẳng vào implementation. Đổi sang: "phân tích, đề xuất hai cách, đợi tao chọn rồi mới code."

**[VISUAL]** 3 khối xếp dọc. Mỗi khối hiện ra theo narration. ❌ màu đỏ nhạt, ✅ màu xanh nhạt.

**[TRANSITION]** Fade to section card

---

# FRAME 11 — Chuyển section: Phần 2

**[DURATION]** 4 giây

**[ON_SCREEN]**
```
PHẦN 2

Kiểm soát scope
```

**[NARRATION]**
> Phần hai. Kiểm soát scope.

**[VISUAL]** Card cam, chữ trắng.

**[TRANSITION]** Fade

---

# FRAME 12 — Câu chuyện thật về scope

**[DURATION]** 30 giây

**[ON_SCREEN]**
```
Bạn bảo AI:
"fix bug ở UI button click"

5 phút sau:
→ 8 file đã sửa
→ 3 namespace đã đổi
→ 1 design pattern mới được thêm

Quen không?
```
*(Các dòng "5 phút sau" xuất hiện lần lượt, hơi giật)*

**[NARRATION]**
> Câu chuyện này quen không?
>
> Bạn bảo AI: fix bug ở UI button click.
>
> Năm phút sau, kiểm tra lại. Tám file đã sửa. Ba namespace đã đổi. Và một design pattern mới vừa được thêm vào project.
>
> *(pause 2s)*
>
> Quen không?

**[VISUAL]** Câu "fix bug" hiện trước, bình thường. Sau đó các con số (8, 3, 1) xuất hiện kèm hiệu ứng zoom giật nhẹ — tăng cảm giác "ôi không".

**[TRANSITION]** Slide left

---

# FRAME 13 — Tại sao scope mất kiểm soát

**[DURATION]** 25 giây

**[ON_SCREEN]**
```
AI không biết "đủ rồi".
Bạn phải nói.

Junior dev trong codebase mới:
→ Thấy code "không đẹp" → muốn sửa
→ Thấy chỗ refactor được → tự refactor
→ Không biết file nào không được động → động hết
```

**[NARRATION]**
> Tại sao chuyện này xảy ra?
>
> Vì AI không biết "đủ rồi". Bạn phải nói.
>
> Y như junior dev mới vào project. Thấy code không đẹp, muốn sửa. Thấy chỗ refactor được, tự refactor. Không biết file nào không được động, nên động hết.
>
> Tech lead làm gì? Vẽ ranh giới TRƯỚC khi giao việc.

**[VISUAL]** Câu chính ở trên to. 3 bullet ở dưới, hiện lần lượt.

**[TRANSITION]** Slide up

---

# FRAME 14 — Quy tắc 1: Plan trước, Code sau

**[DURATION]** 50 giây

**[ON_SCREEN]**
```
QUY TẮC 1
Plan trước, Code sau

Trước khi AI sửa file nào, yêu cầu:
1. Liệt kê file sẽ sửa
2. Mô tả thay đổi cho từng file
3. Liệt kê rủi ro
4. Chờ bạn duyệt
```

*(Sau 4s, hiện thêm box thần chú nổi bật:)*

```
🎯 Câu thần chú:

"Trước khi code, hãy trình bày kế hoạch.
Liệt kê file ảnh hưởng. Đợi tôi duyệt."
```

**[NARRATION]**
> Quy tắc một. Quan trọng nhất video này. Plan trước, Code sau.
>
> Trước khi để AI sửa BẤT KỲ file nào, yêu cầu nó:
>
> Một, liệt kê file sẽ sửa. Hai, mô tả thay đổi cho từng file. Ba, liệt kê rủi ro. Bốn, chờ bạn duyệt.
>
> *(pause 1s)*
>
> Câu thần chú nhớ luôn. "Trước khi code, hãy trình bày kế hoạch. Liệt kê file ảnh hưởng. Đợi tôi duyệt."
>
> Paste câu này vào đầu mọi conversation lớn. Hoặc cho vào Cursor rules. Một câu — tiết kiệm vài giờ debug.

**[VISUAL]** Tiêu đề + 4 bước list. Sau đó box thần chú xuất hiện với background cam nhạt, viền cam đậm.

**[TRANSITION]** Slide left

---

# FRAME 15 — Quy tắc 2: Chat vs Agent

**[DURATION]** 55 giây

**[ON_SCREEN]**
```
QUY TẮC 2
Chat mode vs Agent mode
```

| Chat mode (Ctrl+L) | Agent mode (Ctrl+I) |
|---|---|
| AI nói chuyện, không sửa file | AI tự sửa file, chạy command |
| Bạn copy code thủ công | Bạn approve/reject từng change |
| Khi: hỏi, học, design | Khi: task rõ, scope hẹp |
| Rủi ro thấp | Rủi ro CAO nếu prompt kém |

```
Quy tắc:
✅ Task không rõ → Chat mode
✅ Task rõ + scope hẹp → Agent mode
🚫 Đang khám phá → KHÔNG BAO GIỜ Agent mode
```

**[NARRATION]**
> Quy tắc hai. Phân biệt Chat mode và Agent mode.
>
> Chat mode. AI chỉ nói chuyện, không sửa file. Bạn copy code thủ công. Rủi ro thấp.
>
> Agent mode. AI tự sửa file, tự chạy command. Bạn approve hoặc reject từng thay đổi. Rủi ro CAO nếu prompt kém.
>
> *(pause 1s)*
>
> Ba quy tắc đơn giản.
>
> Task không rõ — Chat mode.
>
> Task rõ và scope hẹp — Agent mode.
>
> Đang khám phá — KHÔNG BAO GIỜ Agent mode.
>
> Đa số dev mới dùng Cursor hoặc Antigravity sai chỗ này. Họ bật Agent mode cho mọi thứ. Đó là nguyên nhân chính của "AI sửa file lung tung".

**[VISUAL]** Bảng so sánh xuất hiện trước. Sau khi narrator giải thích xong bảng, 3 quy tắc xuất hiện ở dưới, mỗi quy tắc có icon ✅ hoặc 🚫.

**[TRANSITION]** Slide up

---

# FRAME 16 — Quy tắc 3: Một task, một chat

**[DURATION]** 40 giây

**[ON_SCREEN]**
```
QUY TẮC 3
Một task, một chat

Khi nào mở chat mới?
→ Task mới, không liên quan
→ AI bắt đầu "lú"
→ Chat dài quá (>30 lượt)
→ Đổi chiến lược lớn

Dấu hiệu AI "lú":
→ Hỏi lại thứ bạn đã nói
→ "Xin lỗi, bạn nói đúng" liên tục
→ Đề xuất lại giải pháp bạn vừa reject
```

**[NARRATION]**
> Quy tắc ba. Một task, một chat.
>
> Khi nào mở chat mới? Khi task mới không liên quan. Khi AI bắt đầu lú. Khi chat đã quá dài, hơn ba mươi lượt. Khi đổi chiến lược lớn.
>
> Dấu hiệu AI lú? Nó hỏi lại thứ bạn đã nói. Nó "xin lỗi, bạn nói đúng" liên tục. Nó đề xuất lại giải pháp bạn vừa reject.
>
> *(pause 1s)*
>
> Nhiều dev cứ chat mãi vì ngại mất context. Thực ra context đã hỏng từ lâu. Mở chat mới, tóm tắt — nhanh hơn dò trong chat dài.

**[VISUAL]** 2 cột song song. Cột trái "Khi nào mở", cột phải "Dấu hiệu lú". Mỗi dòng xuất hiện lần lượt.

**[TRANSITION]** Fade to section card

---

# FRAME 17 — Chuyển section: Phần 3

**[DURATION]** 4 giây

**[ON_SCREEN]**
```
PHẦN 3

Verify code AI
```

**[NARRATION]**
> Phần ba. Verify code AI.

**[VISUAL]** Card cam.

**[TRANSITION]** Fade

---

# FRAME 18 — Sự thật về code AI

**[DURATION]** 25 giây

**[ON_SCREEN]**
```
Code AI luôn trông đúng.
Đó là vấn đề.

Junior viết sai → trông sai → bạn review → fix
AI viết sai → trông ĐÚNG → bạn tin → merge → bug production
```

**[NARRATION]**
> Sự thật về code AI.
>
> Code AI luôn trông đúng. Đó chính là vấn đề.
>
> *(pause 1s)*
>
> Junior viết code sai, trông sai luôn. Bạn để ý ngay. Review. Fix.
>
> AI viết code sai? Nó trông đúng. Bạn tin. Merge. Bug production.

**[VISUAL]** Câu chính to ở giữa. 2 dòng so sánh xuất hiện sau. Dòng AI có chữ "ĐÚNG" highlight cam — gây chú ý.

**[TRANSITION]** Slide up

---

# FRAME 19 — 5 dấu hiệu code AI sai

**[DURATION]** 50 giây

**[ON_SCREEN]**
```
5 dấu hiệu code AI "trông đúng mà sai"

1. Method tên đúng, nội dung không khớp
   → CalculateDamage không nhân với armor

2. Dùng API không tồn tại
   → UnityEngine.X.Y() mà Unity không có

3. Logic ngược dấu
   → if (hp > 0) thay vì if (hp <= 0)

4. Edge case bị bỏ qua
   → null check, mảng rỗng, divide by zero

5. "Quá hoàn hảo"
   → Code dài, comment đẹp, không khớp pattern dự án
```

**[NARRATION]**
> Năm dấu hiệu code AI trông đúng mà sai. Học thuộc.
>
> Một. Method tên đúng, nội dung không khớp. Hàm tên CalculateDamage nhưng không nhân với armor.
>
> Hai. Dùng API không tồn tại. Gọi UnityEngine chấm gì đó mà Unity không có. Đây là "ảo giác" — rất phổ biến.
>
> Ba. Logic ngược dấu. If hp lớn hơn không thay vì if hp nhỏ hơn hoặc bằng không.
>
> Bốn. Edge case bị bỏ qua. Null check, mảng rỗng, chia cho không.
>
> Năm. Quá hoàn hảo. Code dài, comment đẹp — nhưng không khớp pattern dự án.

**[VISUAL]** Số to bên trái, nội dung bên phải. Mỗi dấu hiệu xuất hiện theo narration, không hiện hết 1 lượt.

**[TRANSITION]** Slide left

---

# FRAME 20 — Kỹ thuật: bắt AI tự giải thích

**[DURATION]** 35 giây

**[ON_SCREEN]**
```
Kỹ thuật miễn phí: Bắt AI tự giải thích

🎯 Câu thần chú:

"Giải thích từng dòng cho tôi.
Tại sao chọn cách này thay vì cách khác?
Code này sẽ fail trong trường hợp nào?"

Tại sao hiệu quả:
→ AI buộc phải "nghĩ lại" — tự phát hiện lỗi của nó
→ Bạn hiểu code → review thật
→ AI không giải thích được → đừng dùng code đó
```

**[NARRATION]**
> Kỹ thuật miễn phí, dùng được ngay hôm nay. Bắt AI tự giải thích.
>
> Câu thần chú: "Giải thích từng dòng cho tôi. Tại sao chọn cách này thay vì cách khác? Code này sẽ fail trong trường hợp nào?"
>
> *(pause 1s)*
>
> Tại sao hiệu quả? Vì AI buộc phải nghĩ lại — thường tự phát hiện lỗi của chính nó. Vì bạn hiểu code — review thật, không phải fake review. Và nếu AI không giải thích được — đừng dùng code đó.

**[VISUAL]** Tiêu đề trên. Box thần chú giữa, viền cam, rõ ràng. 3 lý do bên dưới.

**[TRANSITION]** Fade to summary

---

# FRAME 21 — Tổng kết

**[DURATION]** 40 giây

**[ON_SCREEN]**
```
AI là junior dev. Bạn là tech lead.
```

| Vai trò tech lead | Kỹ thuật |
|---|---|
| Brief rõ ràng | 4 thành phần: Vai trò, Context, Task, Output |
| Kiểm soát scope | Plan trước, Chat vs Agent, một task một chat |
| Review chặt | Đọc từng dòng, bắt AI giải thích, 5 dấu hiệu sai |

**[NARRATION]**
> Quay lại nơi bắt đầu.
>
> AI là junior dev. Bạn là tech lead.
>
> Tech lead làm ba việc.
>
> Brief rõ ràng — bốn thành phần: Vai trò, Context, Task, Output.
>
> Kiểm soát scope — Plan trước Code, Chat mode trừ khi chắc, một task một chat.
>
> Review chặt — đọc từng dòng, bắt AI giải thích, năm dấu hiệu sai.

**[VISUAL]** Câu spine lớn ở trên. Bảng tổng kết bên dưới.

**[TRANSITION]** Slide up

---

# FRAME 22 — 3 quy tắc cuối cùng

**[DURATION]** 25 giây

**[ON_SCREEN]**
```
Nếu chỉ nhớ 3 thứ:

1. Brief, không hỏi.

2. Plan trước, code sau.

3. Đọc từng dòng AI viết.
```

**[NARRATION]**
> Nếu video này dài quá, bạn quên hết. Nhớ ba thứ thôi.
>
> *(đọc chậm rãi, dừng giữa mỗi câu)*
>
> Một. Brief, không hỏi.
>
> Hai. Plan trước, code sau.
>
> Ba. Đọc từng dòng AI viết.

**[VISUAL]** 3 dòng to giữa màn hình. Không trang trí. Mỗi dòng to và đậm. Xuất hiện lần lượt theo narration, dừng lâu cho người xem ngấm.

**[TRANSITION]** Fade

---

# FRAME 23 — Kết & call to action

**[DURATION]** 15 giây

**[ON_SCREEN]**
```
Buổi training tuần này
chúng ta sẽ đào sâu.

Hẹn gặp lại.

— XGAME STUDIO —
```

**[NARRATION]**
> Buổi training tuần này, chúng ta sẽ đào sâu từng phần. Mang theo các câu hỏi của bạn.
>
> Hẹn gặp lại.

**[VISUAL]** Background trắng, chữ to giữa màn hình. Logo XGAME STUDIO ở dưới. Fade out cuối.

**[TRANSITION]** Fade to black

---

# TỔNG KẾT THỜI LƯỢNG

| Frame | Nội dung | Thời lượng |
|---|---|---|
| 1 | Hook | 8s |
| 2 | Pain point hook | 12s |
| 3 | Đau thật | 50s |
| 4 | Sự thật khó nghe | 15s |
| 5 | Spine | 35s |
| 6 | Section card 1 | 4s |
| 7 | Brief vs Hỏi | 45s |
| 8 | 4 thành phần | 50s |
| 9 | Demo before/after | 75s |
| 10 | 3 lỗi phổ biến | 55s |
| 11 | Section card 2 | 4s |
| 12 | Câu chuyện scope | 30s |
| 13 | Tại sao scope mất | 25s |
| 14 | Plan trước Code | 50s |
| 15 | Chat vs Agent | 55s |
| 16 | Một task, một chat | 40s |
| 17 | Section card 3 | 4s |
| 18 | Sự thật code AI | 25s |
| 19 | 5 dấu hiệu sai | 50s |
| 20 | AI tự giải thích | 35s |
| 21 | Tổng kết | 40s |
| 22 | 3 quy tắc cuối | 25s |
| 23 | Kết | 15s |
| **TỔNG** | | **~12 phút 30 giây** |

> Cộng thêm pause và transition, video thật sẽ ~14-15 phút. Phù hợp cho priming trước training.

---

# GỢI Ý GIỌNG NARRATION

- **Nhịp**: chậm vừa, không hối hả. ~140-150 từ/phút.
- **Tông**: dev nói chuyện với dev. Không trịnh trọng. Không như giáo viên.
- **Pause**: dùng pause để nhấn — đặc biệt ở Frame 4, 14, 22.
- **TTS phù hợp**: Vietnamese voices như ElevenLabs "Adam Vietnamese", Google Cloud "vi-VN-Standard-D" (nam), hoặc bạn tự thu.

---

# FORMAT CONVERT SANG CÔNG CỤ KHÁC

**Nếu Hyperframe của bạn dùng format khác**, các mapping phổ biến:

- **Remotion (React)**: mỗi `# FRAME X` → `<Sequence>`, narration → `<Audio>`, on_screen → JSX components, duration → `durationInFrames={X*30}` (30fps)
- **Tella**: mỗi frame → 1 segment, paste on_screen vào slide editor, narration đọc lên thu thành audio rồi import
- **Pictory / Synthesia**: paste narration vào script editor, mỗi frame là 1 scene, on_screen text dùng làm subtitle/overlay
- **Capcut/After Effects**: dùng on_screen làm text layer, narration làm audio track, duration làm timing keyframes

---

**HẾT HYPERFRAME SCRIPT.**
