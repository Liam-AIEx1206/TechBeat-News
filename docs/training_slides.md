# SLIDE NỘI DUNG — Training Unity AI (Buổi training 2h)

> **Mục đích:** slide dùng trong buổi training 2h, SAU KHI team đã xem video priming.
> Nội dung khớp với video — người nghe có cảm giác "à mình đã thấy cái này" → tăng nhớ.
> Slide đào sâu hơn video: thêm ví dụ, thêm Q&A, có thời gian dừng lại bàn luận.

---

## METADATA

- **Tổng số slide:** 30 (vs 23 frame video — slide nhiều hơn vì có thời gian đào sâu)
- **Thời lượng:** 2 giờ
- **Đối tượng:** team dev hỗn hợp, đã xem video priming
- **Spine:** "AI là junior dev rất giỏi. Bạn là tech lead." (LẶP LẠI từ video — đây là chủ ý)
- **Phân bổ:**
  - Khối 1: Mở đầu + Recap video (15 phút, 5 slide)
  - Khối 2: Brief (35 phút, 7 slide)
  - Khối 3: Kiểm soát scope (30 phút, 7 slide)
  - Khối 4: Verify code AI (25 phút, 6 slide)
  - Khối 5: Tổng kết + Q&A (15 phút, 5 slide)

### Khác biệt với video

- **Video** = priming, một chiều, ~15 phút, người xem thụ động
- **Slide** = training, hai chiều, 2 giờ, có Q&A, bàn luận, ví dụ thật từ team

Slide CỐ Ý lặp lại nội dung video — đây là **spaced repetition** (lặp giãn cách), tăng nhớ. KHÔNG phải lặp thừa.

### Quy ước

- `**ND:**` = nội dung hiển thị trên slide
- `**NÓI:**` = lời speaker nói (không hiển thị trên slide)
- `**HỎI:**` = câu hỏi tương tác với audience
- `**LAYOUT:**` = gợi ý bố cục

---

# KHỐI 1 — MỞ ĐẦU + RECAP (15 phút)

## Slide 1 — Title

**LAYOUT:** Title slide.

**ND tiêu đề (cực lớn):**
Training Unity AI

**ND subtitle:**
Làm việc với AI như một tech lead

**ND footer:**
Buổi training trực tiếp · Sau video priming

**NÓI:**
> Cả nhà đã xem video tuần trước rồi. Hôm nay 2 tiếng. Chúng ta không học lại — chúng ta đào sâu, ví dụ thật, và giải đáp các thắc mắc của các bạn.

---

## Slide 2 — Recap video

**LAYOUT:** Diagram đơn giản — 3 box đại diện 3 phần video, mỗi box 1 câu tóm tắt.

**ND tiêu đề:**
Video tuần trước nói gì?

**ND 3 box:**

```
PHẦN 1 — BRIEF             PHẦN 2 — SCOPE            PHẦN 3 — VERIFY
4 thành phần                3 quy tắc                  5 dấu hiệu sai
(Vai trò, Context,          (Plan trước, Chat vs       + Bắt AI giải thích
Task, Output)               Agent, 1 task 1 chat)
```

**Footer:**
*Spine: AI là junior dev. Bạn là tech lead.*

**NÓI:**
> Tóm tắt 30 giây cho ai chưa xem hoặc xem lâu rồi.
>
> Ba phần. Brief có bốn thành phần. Kiểm soát scope có ba quy tắc. Verify có năm dấu hiệu code AI sai.
>
> Spine xuyên suốt: AI là junior dev, bạn là tech lead.

**HỎI:**
> Có ai chưa xem video? *(nếu có — gửi link nhanh, cho 10 phút xem trước)*

---

## Slide 3 — Kích hoạt pain point (REAL)

**LAYOUT:** Câu hỏi to giữa slide. Không bullet.

**ND:**
Tuần này, ai trong team đã trải qua "fix bug AI"?

Kể 1 case.

**NÓI:**
> Đứng dậy đi. Tôi cần 2-3 người chia sẻ case thật trong tuần này. Bug gì, AI làm gì, các bạn xử lý thế nào.

**HỎI:** *(open mic, dành 5-7 phút)*
- Ai chia sẻ trước?
- (Sau khi nghe) Bug này thuộc loại nào trong 5 dấu hiệu video đã nói?

> 💡 **Tại sao slide này quan trọng:** Buổi training không có case thật từ chính team thì như nghe radio. Có case thật → người nghe nhận ra "à mình cũng vừa gặp" → mọi slide sau đều có context.

---

## Slide 4 — Sự thật

**LAYOUT:** Câu lớn giữa slide.

**ND:**
Vấn đề không phải AI dở.

Vấn đề là chúng ta giao việc cho AI sai cách.

**NÓI:**
> Video đã nói rồi. Nhưng tôi lặp lại vì đây là frame quan trọng nhất cả buổi.
>
> AI version 2026 không dở. GPT-5, Claude Opus, Gemini... chúng nó giỏi hơn nhiều dev junior bạn từng làm việc cùng.
>
> Vấn đề luôn ở phía bạn — cách giao việc.

---

## Slide 5 — Frame 2 giờ tới

**LAYOUT:** Tiêu đề + 3 phần + thời lượng + cam kết.

**ND:**
Hai giờ tới — chúng ta làm gì?

**3 phần:**
- **Phần 1 (35'):** Brief — đào sâu 4 thành phần, làm thử với case của các bạn
- **Phần 2 (30'):** Scope — phân biệt Chat/Agent mode trên Cursor/Antigravity
- **Phần 3 (25'):** Verify — review live 1 đoạn code AI thật

**+ Tổng kết & Q&A (15'):** câu hỏi của các bạn

**Footer:**
*Sau buổi này, các bạn có cheatsheet 1 trang mang về.*

**NÓI:**
> Đây là roadmap 2 giờ. Bất kỳ lúc nào dừng tôi để hỏi cũng được — không cần đợi đến cuối.

---

# KHỐI 2 — BRIEF (35 phút, 7 slide)

## Slide 6 — Section card

**LAYOUT:** Card chuyển section.

**ND tiêu đề (cực lớn):**
PHẦN 1

Brief, không hỏi

**Footer:**
*Tech lead viết brief, không trả lời câu hỏi.*

---

## Slide 7 — Recap 4 thành phần

**LAYOUT:** 4 box.

**ND:**
4 thành phần của một brief tốt

| **1. VAI TRÒ** | AI đóng vai gì? |
|---|---|
| **2. CONTEXT** | Project, version, file liên quan |
| **3. TASK** | Một việc, scope rõ |
| **4. OUTPUT** | Trả về dạng gì? Chờ duyệt? |

**NÓI:**
> Video đã giới thiệu 4 thành phần. Hôm nay, đào sâu từng cái. Bắt đầu với Vai trò.

---

## Slide 8 — Sâu hơn: VAI TRÒ

**LAYOUT:** Tiêu đề + 3 ví dụ + tip.

**ND tiêu đề:**
1. VAI TRÒ — chi tiết

**ND ví dụ:**

```
Mơ hồ ❌:
"Bạn là developer"

Tốt ✅:
"Bạn là Unity gameplay engineer làm với codebase
mobile RPG, đã có 2 năm kinh nghiệm Unity 6."

Rất tốt ✅✅:
"Bạn là Unity gameplay engineer.
Đang làm việc trong studio indie 5 người.
Quan tâm performance trên mobile mid-range.
Tuân thủ SOLID nhưng không over-engineer."
```

**Tip:**
> Vai trò không chỉ là "ai" — mà còn là **ưu tiên gì**. "Quan tâm performance" / "không over-engineer" → AI sẽ chọn cách tiếp cận khác.

**NÓI:**
> Vai trò càng cụ thể, output càng đúng. Nhưng đừng quá dài — 2-3 dòng là đủ.

---

## Slide 9 — Sâu hơn: CONTEXT

**LAYOUT:** Tiêu đề + checklist + ví dụ.

**ND tiêu đề:**
2. CONTEXT — chi tiết

**ND checklist:**

Context tối thiểu cần có:
- ✅ Engine + version (Unity 6, không phải "Unity")
- ✅ Architecture đang dùng (ECS? OOP? State Machine?)
- ✅ Libraries quan trọng (UniRx, DOTween, Zenject...)
- ✅ File liên quan (paste nếu cần)
- ✅ Convention dự án (PascalCase? K&R brace?)

**Tip mạnh:**
```
💡 Mẹo: tạo file CONTEXT.md trong project.
   Mỗi lần prompt — paste nội dung file đó.
   Hoặc đưa vào Cursor rules / Claude skill.
```

**NÓI:**
> Context là phần các bạn hay quên. Nhưng nó quan trọng nhất.
>
> Mẹo: viết 1 lần, dùng nhiều lần. Tạo file CONTEXT.md hoặc đưa vào Cursor rules.

**HỎI:**
> Trong team mình, ai đã có file CONTEXT.md? Ai dùng Cursor rules? *(thăm dò xem họ đang ở đâu)*

---

## Slide 10 — Sâu hơn: TASK + OUTPUT

**LAYOUT:** 2 cột.

**ND tiêu đề:**
3. TASK + 4. OUTPUT — chi tiết

**ND cột TASK:**

```
TASK xấu ❌:
"thêm hệ thống inventory"

TASK tốt ✅:
"Tạo class InventoryItem có:
- itemId (int)
- quantity (int)
- maxStack (int)
Không xử lý UI, không persist."
```

**ND cột OUTPUT:**

```
OUTPUT mơ hồ ❌:
(không nói gì)

OUTPUT tốt ✅:
- File: Scripts/Inventory/InventoryItem.cs
- Style: pure C# class, không MonoBehaviour
- Có XML comment cho public field
- Chờ tôi confirm trước khi sửa file khác
```

**NÓI:**
> Task hẹp hơn bạn nghĩ. "Thêm inventory" là cả 1 epic — chia ra 10 task nhỏ.
>
> Output bao gồm: file ở đâu, style gì, có comment không, và quan trọng nhất — bước kế tiếp.

---

## Slide 11 — Demo: trước khi nhìn brief tốt

**LAYOUT:** Khối ❌ một mình.

**ND tiêu đề:**
Cùng 1 task — 2 cách

**ND task:**
*Task: "Thêm loot drop khi enemy chết"*

**ND khối ❌:**

```
PROMPT YẾU:
"thêm loot drop khi enemy chết"
```

**NÓI:**
> Bạn nào trong đây, nếu là AI, nhận prompt này — sẽ làm gì?

**HỎI:** *(nhận 2-3 ý kiến từ phòng)*
- AI sẽ đoán loot là gì?
- AI sẽ sửa những file nào?
- AI có hỏi lại không?

> 💡 **Mục đích:** trước khi show brief tốt, để team tự nhận ra prompt yếu sẽ dẫn đến hỗn loạn. Self-discovery học sâu hơn lời giảng.

---

## Slide 12 — Demo: brief tốt

**LAYOUT:** Khối ✅ to, có annotation.

**ND tiêu đề:**
Brief tốt cho cùng task

**ND:**

```
[VAI TRÒ] Unity gameplay engineer làm với codebase này.

[CONTEXT]
- Unity 6, có ScriptableObject ItemData cho item
- Enemy.cs đã có event OnDeath
- LootTable là field [SerializeField] trên Enemy prefab

[TASK]
Khi OnDeath fire, spawn item theo LootTable tại vị trí enemy.
Mỗi entry có dropRate (0-1).
KHÔNG sửa InventoryManager hay ItemData.

[OUTPUT]
1. Liệt kê file sẽ tạo/sửa
2. Code sạch, XML comment cho public method
3. Chờ tôi confirm trước khi sửa file
```

**Annotation (highlight từng phần):**
- [VAI TRÒ] → ✓
- [CONTEXT] → ✓
- [TASK] → ✓ (có scope rõ + cấm)
- [OUTPUT] → ✓ (có format + bước kế tiếp)

**NÓI:**
> Dài hơn? Có. Nhưng đổi lại — không phải fix bug 2 tiếng.
>
> Để ý dòng "KHÔNG sửa InventoryManager hay ItemData" — đây là kiểm soát scope sớm. Phần 2 sẽ nói kỹ về cái này.

---

# KHỐI 3 — KIỂM SOÁT SCOPE (30 phút, 7 slide)

## Slide 13 — Section card

**LAYOUT:** Card chuyển section.

**ND:**
PHẦN 2

Kiểm soát scope

*AI không biết "đủ rồi". Bạn phải nói.*

---

## Slide 14 — Recap câu chuyện scope

**LAYOUT:** Storytelling.

**ND:**
Câu chuyện video kể lại

Bạn bảo AI: *"fix bug ở UI button click"*

5 phút sau:
- 8 file đã sửa
- 3 namespace đã đổi
- 1 design pattern mới được thêm

**HỎI:**
> Trong tuần này, ai gặp tương tự? Kể nhanh.

> 💡 Hỏi lại — buổi training không phải để nghe lại video. Để đào sâu bằng case thật của TEAM.

---

## Slide 15 — Quy tắc 1: Plan trước Code (đào sâu)

**LAYOUT:** Câu thần chú + ví dụ áp dụng.

**ND tiêu đề:**
Quy tắc 1 — Plan trước, Code sau

**ND box thần chú:**

```
🎯 Câu thần chú:

"Trước khi code, hãy trình bày kế hoạch.
Liệt kê file ảnh hưởng. Đợi tôi duyệt."
```

**ND áp dụng:**

3 cách paste câu này:
1. **Đầu mỗi prompt** (cách dễ nhất)
2. **Cursor rules** → tự áp dụng mọi conversation
3. **Skill file** → chia sẻ cho cả team

**NÓI:**
> Đừng chỉ nhớ — đặt nó vào hệ thống. Cursor rules là cách rẻ nhất, ai cũng làm được.

**HỎI:** *(demo trên màn hình nếu được)*
> Ai có Cursor mở luôn? Tôi sẽ show cách paste vào rules.

---

## Slide 16 — Demo Cursor rules (LIVE)

**LAYOUT:** Screenshot Cursor + step.

**ND:**
Live demo — paste vào Cursor rules

**Step:**
1. Mở Cursor → Settings → Rules
2. Paste câu thần chú
3. Mở chat mới → thử prompt → AI tự plan trước

**Screenshot placeholder:**
*[Chèn screenshot Cursor Settings → Rules]*

**NÓI:**
> Demo nhanh 2 phút. Nếu không có máy chiếu, kể lại — về nhà các bạn làm theo.

> 💡 Đây là một trong những moment có thể "demo" mặc dù buổi training không có thực hành. Demo 2 phút mạnh hơn nói 10 phút.

---

## Slide 17 — Quy tắc 2: Chat vs Agent

**LAYOUT:** Bảng + ví dụ thực tế.

**ND tiêu đề:**
Quy tắc 2 — Chat mode vs Agent mode

**ND bảng:**

| | Chat mode | Agent mode |
|---|---|---|
| Shortcut | Ctrl+L | Ctrl+I |
| Hành động | Chỉ nói chuyện | Tự sửa file, chạy command |
| Code | Bạn copy thủ công | AI tự apply, bạn approve |
| Rủi ro | Thấp | Cao nếu prompt kém |

**ND quy tắc:**
- Task không rõ → **Chat**
- Task rõ + scope hẹp → **Agent**
- Đang khám phá → **KHÔNG BAO GIỜ Agent**

**Ví dụ thực tế:**
```
"Tại sao GameObject này không render?" → CHAT (đang khám phá)
"Đổi color material thành đỏ" → AGENT (scope cực hẹp)
"Refactor InventorySystem cho đẹp hơn" → CHAT trước! (quá rộng)
```

**NÓI:**
> Quy tắc đơn giản nhưng hay sai. Đa số dev mới mở Agent mode cho mọi thứ — vì "tiện".
>
> Tiện một, debug mười.

---

## Slide 18 — Quy tắc 3: Một task, một chat

**LAYOUT:** 2 cột.

**ND tiêu đề:**
Quy tắc 3 — Một task, một chat

**ND cột trái — Khi nào mở chat mới:**
- Task mới, không liên quan task cũ
- AI bắt đầu "lú"
- Chat đã quá dài (>30 lượt)
- Đổi chiến lược lớn

**ND cột phải — Dấu hiệu AI "lú":**
- Hỏi lại thứ bạn đã nói
- "Xin lỗi, bạn nói đúng" liên tục
- Đề xuất lại giải pháp bạn vừa reject
- Quên context bạn paste 5 lượt trước

**Tip:**
```
💡 Trước khi mở chat mới:
   "Tóm tắt cho tôi: chúng ta đã làm gì, đang ở đâu,
    bước kế tiếp là gì?"
   → Paste tóm tắt vào chat mới làm context.
```

**NÓI:**
> Mẹo cuối: AI tự tóm tắt context trước khi bạn mở chat mới. Tiết kiệm 10 phút mỗi lần.

---

## Slide 19 — Take-away khối 3

**LAYOUT:** 1 câu lớn + 3 quy tắc.

**ND câu lớn:**
AI không biết "đủ rồi". Bạn phải vẽ ranh giới.

**ND 3 quy tắc:**
1. Plan trước, code sau
2. Chat mode trừ khi chắc chắn
3. Một task, một chat

**HỎI:** *(cả phòng đọc theo)*
> Nhắc lại với tôi: 3 quy tắc là gì?

> 💡 Yêu cầu phòng đọc TO theo — kỹ thuật memory hóa cổ điển. Nghe → nói lên → nhớ 3x.

---

# KHỐI 4 — VERIFY CODE AI (25 phút, 6 slide)

## Slide 20 — Section card

**ND:**
PHẦN 3

Verify code AI

*Code AI luôn trông đúng. Đó là vấn đề.*

---

## Slide 21 — Sự thật code AI

**LAYOUT:** Câu chính + so sánh.

**ND câu chính:**
Code AI luôn trông đúng. Đó là vấn đề.

**ND bảng so sánh:**

| Junior viết code sai | AI viết code sai |
|---|---|
| Trông sai luôn | **Trông ĐÚNG** |
| Bạn để ý → review → fix | Bạn tin → merge |
| Bug development | **Bug production** |

**NÓI:**
> Đây là lý do "fix bug AI lâu hơn tự code". Bug được giấu trong code trông sạch sẽ.

---

## Slide 22 — 5 dấu hiệu (recap + ví dụ thật)

**LAYOUT:** 5 bullet + ví dụ code thật bên cạnh.

**ND tiêu đề:**
5 dấu hiệu code AI "trông đúng mà sai"

**ND:**

```csharp
// Dấu hiệu 1: Method tên đúng, nội dung không khớp
public float CalculateDamage(float baseDmg, float armor) {
    return baseDmg;  // ❌ quên trừ armor!
}

// Dấu hiệu 2: API không tồn tại
GameObject.FindClosestByTag("enemy");  // ❌ Unity không có

// Dấu hiệu 3: Logic ngược dấu
if (health > 0) Die();  // ❌ ngược!

// Dấu hiệu 4: Edge case bị bỏ qua
int avg = total / count;  // ❌ count = 0 thì sao?

// Dấu hiệu 5: "Quá hoàn hảo"
// 50 dòng code có Factory + Strategy + Observer
// cho 1 việc đơn giản là toggle bool ❌
```

**NÓI:**
> 5 ví dụ trên là code AI THẬT mà tôi đã thấy trong các project — không bịa.
>
> Đặc biệt dấu hiệu 2 (API không tồn tại) — AI version mới vẫn ảo giác. Đừng tin.

---

## Slide 23 — Live review (interactive)

**LAYOUT:** 1 đoạn code lớn ở giữa.

**ND tiêu đề:**
Cùng tìm bug — code AI thật

**ND code:**

```csharp
public class PlayerHealth : MonoBehaviour
{
    public float maxHealth = 100f;
    public float currentHealth;

    void Start() {
        currentHealth = maxHealth;
    }

    public void TakeDamage(float damage) {
        currentHealth -= damage;
        if (currentHealth > 0) {
            Die();
        }
    }

    void Die() {
        gameObject.SetActive(false);
    }
}
```

**HỎI:** *(cho phòng 1 phút tìm)*
> Ai tìm ra bug? Có mấy bug?

**Đáp án (slide tiếp theo):**
1. Logic `> 0` ngược, phải là `<= 0`
2. Không check `currentHealth` tràn âm
3. `Die()` chỉ SetActive(false) — không có animation, không destroy, không event

> 💡 **MOMENT VÀNG của buổi training.** 1 phút interactive, kết nối mạnh hơn 30 phút nghe giảng. CHUẨN BỊ KỸ slide này.

---

## Slide 24 — Kỹ thuật: bắt AI tự giải thích

**LAYOUT:** Câu thần chú + lý do.

**ND tiêu đề:**
Kỹ thuật miễn phí — bắt AI giải thích

**ND box thần chú:**

```
🎯 "Giải thích từng dòng cho tôi.
    Tại sao chọn cách này thay vì cách khác?
    Code này sẽ fail trong trường hợp nào?"
```

**Tại sao hiệu quả:**
- AI phải "nghĩ lại" → tự phát hiện lỗi
- Bạn hiểu code → review thật, không phải fake review
- AI không giải thích được → đừng dùng code đó

**Tip nâng cao:**
```
💡 Combo mạnh nhất:
   1. AI tạo code
   2. "Giải thích từng dòng + fail case"
   3. "Viết unit test cho 3 fail case nguy hiểm nhất"
   4. Bạn review test + code cùng nhau
```

**NÓI:**
> Tip cuối là combo mạnh nhất. Mất 5 phút thêm, tránh 2 tiếng debug.

---

## Slide 25 — Take-away khối 4

**LAYOUT:** Câu lớn.

**ND:**
Review code AI nghiêm hơn code đồng nghiệp.

Vì nó trông đúng hơn.

**NÓI:**
> Câu này. Mang về. Chống lại bản năng "AI giỏi, tin nó đi."

---

# KHỐI 5 — TỔNG KẾT + Q&A (15 phút, 5 slide)

## Slide 26 — Quay lại spine

**LAYOUT:** Spine + bảng tổng kết.

**ND câu spine:**
AI là junior dev. Bạn là tech lead.

**ND bảng:**

| Vai trò tech lead | Kỹ thuật hôm nay |
|---|---|
| Brief rõ ràng | 4 thành phần: Vai trò, Context, Task, Output |
| Kiểm soát scope | Plan trước, Chat vs Agent, một task một chat |
| Review chặt | Đọc từng dòng, bắt AI giải thích, 5 dấu hiệu sai |

**NÓI:**
> Tóm lại 2 tiếng — bảng này. Mọi kỹ thuật đều quay về spine.

---

## Slide 27 — 3 quy tắc cuối (SLIDE TO NHẤT)

**LAYOUT:** 3 dòng to, không trang trí.

**ND tiêu đề nhỏ:**
Nếu chỉ nhớ 3 thứ:

**ND 3 dòng (FONT CỰC LỚN):**

**1. Brief, không hỏi.**

**2. Plan trước, code sau.**

**3. Đọc từng dòng AI viết.**

**NÓI:** *(đọc CHẬM, dừng 2-3s giữa mỗi câu)*
> Một. Brief, không hỏi.
>
> *(dừng)*
>
> Hai. Plan trước, code sau.
>
> *(dừng)*
>
> Ba. Đọc từng dòng AI viết.

**HỎI:**
> Cả phòng đọc theo tôi.

> 💡 MOMENT QUAN TRỌNG NHẤT. Đảm bảo dev khi về vẫn nhớ 3 dòng này.

---

## Slide 28 — Cheatsheet

**LAYOUT:** Thumbnail cheatsheet + QR code (nếu có).

**ND tiêu đề:**
Cheatsheet 1 trang

**ND:**
- File đính kèm chat (Slack/Discord/Email)
- In ra, dán cạnh màn hình
- Mỗi lần định gõ prompt → liếc qua

**Footer:**
*2 tuần áp dụng = thành phản xạ.*

**NÓI:**
> Phát cheatsheet ngay bây giờ. Cầm tay. Mang về dán bàn.

---

## Slide 29 — Cam kết tuần này

**LAYOUT:** 2 cột.

**ND tiêu đề:**
Cam kết tuần này / tuần sau

**Tuần này:**
- Áp dụng "Plan trước, code sau" cho mọi feature mới
- Mỗi Accept code AI → hỏi "giải thích từng dòng" trước
- Paste câu thần chú vào Cursor rules

**Tuần sau:**
- Thử tạo 1 Skill cho team
- Thử workflow Phases & Tasks cho 1 feature lớn
- Quay lại đây — buổi follow-up (nếu có)

**HỎI:**
> Ai cam kết áp dụng "Plan trước Code" trong tuần này? Giơ tay.

> 💡 Cam kết công khai → tăng tỉ lệ thực hiện gấp 3 lần. Hỏi luôn — không ngại.

---

## Slide 30 — Q&A

**LAYOUT:** Câu đơn giản giữa slide.

**ND:**
Hỏi gì cũng được.

**NÓI:**
> 10 phút Q&A. Câu hỏi nào tôi không trả lời được, sẽ ghi lại và phản hồi qua chat.

**Câu hỏi dự kiến + chuẩn bị sẵn:**

1. *"Cursor rules vs Claude Skill khác gì?"*
   → Cursor rules = config cho tool Cursor. Claude Skill = file markdown được load theo trigger. Bản chất giống — tái sử dụng instruction.

2. *"AI có thay được junior dev không?"*
   → Không. AI là junior siêu năng suất nhưng không có context. Vẫn cần human-in-the-loop.

3. *"Team mình code legacy, AI có dùng được không?"*
   → Được. Context quan trọng hơn bao giờ hết. Tạo CONTEXT.md mô tả legacy pattern.

4. *"Có nên dùng AI cho code production?"*
   → Có, NHƯNG review nghiêm hơn code human. 5 dấu hiệu phần 3 áp dụng cho mọi code merge.

---

# PHỤ LỤC — TIMING CHI TIẾT

| Khối | Slide | Phút | Cumulative |
|---|---|---|---|
| K1 — Mở đầu | 1-5 | 15' | 15' |
| K2 — Brief | 6-12 | 35' | 50' |
| K3 — Scope | 13-19 | 30' | 80' |
| K4 — Verify | 20-25 | 25' | 105' |
| K5 — Tổng kết | 26-30 | 15' | 120' |

**Buffer:** không có. Nếu vượt giờ — cắt Q&A trước, không cắt nội dung.

---

# PHỤ LỤC — KHÁC BIỆT VIDEO vs SLIDE

| | Video (Hyperframe) | Slide (Live) |
|---|---|---|
| Thời lượng | ~15 phút | 2 giờ |
| Hướng | Một chiều | Hai chiều (Q&A, demo) |
| Khi xem | Trước training | Trong training |
| Mục đích | Priming, mindset | Đào sâu, áp dụng |
| Slide đặc trưng | 1, 4, 22 (3 quy tắc) | 11 (HỎI trước demo), 23 (live review), 29 (cam kết) |

Nội dung CORE giống nhau — đây là chủ ý (spaced repetition).

---

**HẾT SLIDE CONTENT.**
