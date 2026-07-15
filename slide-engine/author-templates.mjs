/**
 * Trình tạo template thiết kế sẵn cho XNEW slide.
 * Clone shell (scaffold + assets + font Montserrat/Inter) từ 1 trang engine thật,
 * chỉ thay nội dung + màu nền theo THEME → style khóa cứng 100%, không do model tô.
 *
 * Chạy: node author-templates.mjs
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ENGINE = path.resolve('.');
const BASE_SESSION = 'data/storage/45f127f2-2a82-4781-b253-20f7854dc2b5'; // deck Montserrat/Inter
const TEMPLATES = 'data/templates';

// ── lấy shell (HEAD tới <main content>, và TAIL từ fit-script) từ 1 trang thật ──
const basePage = fs.readFileSync(
  path.join(ENGINE, BASE_SESSION, fs.readdirSync(path.join(ENGINE, BASE_SESSION)).find((f) => f.startsWith('page-') && f.endsWith('.html'))),
  'utf-8'
);
const CONTENT_OPEN = '<main data-block-id="content" data-role="content" class="h-full min-h-0">';
const iOpen = basePage.indexOf(CONTENT_OPEN) + CONTENT_OPEN.length;
const iFit = basePage.indexOf('<script id="ppt-page-fit">');
let HEAD = basePage.slice(0, iOpen);
const TAIL = '</main>\n  </section>\n</div>\n      </div>\n    </main>\n    ' + basePage.slice(iFit);

function buildHead(pageId, pageBg, defaultText) {
  return HEAD
    .replace(/--ppt-page-bg:\s*[^;]+;/, `--ppt-page-bg: ${pageBg};`)
    .replace('color: #0f172a;', `color: ${defaultText};`)
    .replace(/<body data-page-id="[^"]*">/, `<body data-page-id="${pageId}">`);
}

function assemblePage(pageId, pageBg, defaultText, inner) {
  return buildHead(pageId, pageBg, defaultText) + '\n' + inner + '\n' + TAIL;
}

// ── helper thư viện khối UI (dùng chung, màu truyền vào) ──
function chip(text, c) {
  return `<span style="display:inline-flex;align-items:center;padding:6px 14px;border-radius:999px;font-size:15px;font-weight:600;background:${c.chipBg};color:${c.chipText};border:1px solid ${c.border}">${text}</span>`;
}

// ═══════════════ ĐỊNH NGHĨA TEMPLATE ═══════════════
function makeTemplate(cfg) {
  const c = cfg.colors;
  const card = `background:${c.card};border:1px solid ${c.border};border-radius:24px;box-shadow:0 18px 40px ${c.shadow}`;
  const eyebrow = `font-size:15px;font-weight:700;letter-spacing:0.28em;text-transform:uppercase;color:${c.accent}`;
  const h1 = `font-family:var(--ppt-title-font);font-weight:800;color:${c.title};line-height:1.05`;
  const body = `font-family:var(--ppt-body-font);color:${c.body}`;

  const pages = [
    // 1) COVER
    {
      title: cfg.sampleTitles[0],
      inner: `<div style="height:100%;padding:96px;display:grid;grid-template-columns:1.15fr 0.85fr;gap:56px;align-items:center">
        <div>
          <div style="${eyebrow}" data-anim="fade-up">${cfg.brand}</div>
          <h1 style="${h1};font-size:76px;margin-top:20px" data-anim="fade-up">${cfg.sampleTitles[0]}</h1>
          <p style="${body};font-size:24px;line-height:1.6;margin-top:24px;max-width:640px;opacity:.9" data-anim="fade-up">${cfg.coverSub}</p>
          <div style="display:flex;gap:12px;margin-top:36px" data-anim="fade-up">
            ${chip('Điểm nhấn 1', c)}${chip('Điểm nhấn 2', c)}${chip('Điểm nhấn 3', c)}
          </div>
        </div>
        <div style="${card};padding:44px;display:flex;flex-direction:column;gap:20px" data-anim="fade-up">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="padding:6px 14px;border-radius:999px;background:${c.title};color:${c.card};font-weight:700;font-size:16px">NỔI BẬT</span>
            <span style="${body};font-size:15px;opacity:.7">tổng quan</span>
          </div>
          <div style="font-family:var(--ppt-title-font);font-weight:800;font-size:120px;line-height:1;color:${c.accent}">01</div>
          <div style="${body};font-size:19px;line-height:1.5">Con số / thông điệp chính đặt ở đây để mở đầu ấn tượng.</div>
          <div style="height:1px;background:${c.border}"></div>
          <div style="display:flex;justify-content:space-between;${body};font-size:16px"><span>Chủ đề</span><b style="color:${c.title}">Giá trị</b></div>
        </div>
      </div>`,
    },
    // 2) KPI GRID
    {
      title: cfg.sampleTitles[1],
      inner: `<div style="height:100%;padding:88px 96px;display:flex;flex-direction:column;gap:40px">
        <div>
          <div style="${eyebrow}" data-anim="fade-up">SỐ LIỆU</div>
          <h1 style="${h1};font-size:52px;margin-top:14px" data-anim="fade-up">${cfg.sampleTitles[1]}</h1>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px;flex:1" data-anim="fade-up">
          ${[['85%', 'Chỉ số thứ nhất', c.accent], ['2.4x', 'Chỉ số thứ hai', c.accent2], ['#1', 'Chỉ số thứ ba', c.accent]]
            .map(([n, l, col]) => `<div style="${card};padding:40px;display:flex;flex-direction:column;justify-content:center;gap:12px">
              <div style="font-family:var(--ppt-title-font);font-weight:800;font-size:72px;color:${col};line-height:1">${n}</div>
              <div style="${body};font-size:20px;font-weight:600;color:${c.title}">${l}</div>
              <div style="${body};font-size:16px;opacity:.75;line-height:1.5">Mô tả ngắn cho chỉ số, thay bằng nội dung thật.</div>
            </div>`).join('')}
        </div>
      </div>`,
    },
    // 3) TIMELINE / PROCESS
    {
      title: cfg.sampleTitles[2],
      inner: `<div style="height:100%;padding:88px 96px;display:flex;flex-direction:column;gap:44px">
        <div>
          <div style="${eyebrow}" data-anim="fade-up">TIẾN TRÌNH</div>
          <h1 style="${h1};font-size:52px;margin-top:14px" data-anim="fade-up">${cfg.sampleTitles[2]}</h1>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px;flex:1;position:relative" data-anim="fade-up">
          ${[['1', 'Bước một', 'Mô tả bước đầu tiên của quy trình.'], ['2', 'Bước hai', 'Mô tả bước tiếp theo, giữ ngắn gọn.'], ['3', 'Bước ba', 'Kết quả / cột mốc cuối cùng.']]
            .map(([n, t, d]) => `<div style="${card};padding:36px;display:flex;flex-direction:column;gap:16px">
              <div style="width:56px;height:56px;border-radius:16px;background:${c.accent};color:${c.card};display:flex;align-items:center;justify-content:center;font-family:var(--ppt-title-font);font-weight:800;font-size:26px">${n}</div>
              <div style="font-family:var(--ppt-title-font);font-weight:700;font-size:26px;color:${c.title}">${t}</div>
              <div style="${body};font-size:18px;line-height:1.55;opacity:.85">${d}</div>
            </div>`).join('')}
        </div>
      </div>`,
    },
    // 4) COMPARISON
    {
      title: cfg.sampleTitles[3],
      inner: `<div style="height:100%;padding:88px 96px;display:flex;flex-direction:column;gap:40px">
        <div>
          <div style="${eyebrow}" data-anim="fade-up">SO SÁNH</div>
          <h1 style="${h1};font-size:52px;margin-top:14px" data-anim="fade-up">${cfg.sampleTitles[3]}</h1>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px;flex:1" data-anim="fade-up">
          <div style="${card};padding:44px;display:flex;flex-direction:column;gap:18px">
            <div style="${eyebrow};font-size:13px">PHƯƠNG ÁN A</div>
            <div style="font-family:var(--ppt-title-font);font-weight:700;font-size:30px;color:${c.title}">Tiêu đề A</div>
            ${['Ưu điểm thứ nhất', 'Ưu điểm thứ hai', 'Ưu điểm thứ ba'].map((t) => `<div style="${body};font-size:19px;display:flex;gap:12px"><span style="color:${c.accent};font-weight:800">✓</span>${t}</div>`).join('')}
          </div>
          <div style="padding:44px;border-radius:24px;display:flex;flex-direction:column;gap:18px;background:${c.invBg};border:1px solid ${c.border}">
            <div style="font-size:13px;font-weight:700;letter-spacing:.28em;text-transform:uppercase;color:${c.accent2}">PHƯƠNG ÁN B</div>
            <div style="font-family:var(--ppt-title-font);font-weight:700;font-size:30px;color:${c.invText}">Tiêu đề B</div>
            ${['Điểm khác biệt một', 'Điểm khác biệt hai', 'Điểm khác biệt ba'].map((t) => `<div style="font-family:var(--ppt-body-font);color:${c.invText};opacity:.9;font-size:19px;display:flex;gap:12px"><span style="color:${c.accent2};font-weight:800">→</span>${t}</div>`).join('')}
          </div>
        </div>
      </div>`,
    },
    // 5) IMAGE SLOT
    {
      title: cfg.sampleTitles[4],
      inner: `<div style="height:100%;padding:88px 96px;display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:center">
        <div>
          <div style="${eyebrow}" data-anim="fade-up">HÌNH ẢNH</div>
          <h1 style="${h1};font-size:50px;margin-top:14px" data-anim="fade-up">${cfg.sampleTitles[4]}</h1>
          <p style="${body};font-size:20px;line-height:1.65;margin-top:22px;opacity:.9" data-anim="fade-up">Đặt ảnh minh hoạ bên phải: ảnh sản phẩm, ảnh chụp màn hình game, hoặc ảnh bìa. Chữ mô tả nằm bên trái để cân bằng.</p>
          <div style="display:flex;gap:12px;margin-top:28px" data-anim="fade-up">${chip('Thay chữ', c)}${chip('Thay ảnh', c)}</div>
        </div>
        <div data-ppt-image-slot="1" style="height:520px;border:2px dashed ${c.accent};border-radius:24px;background:${c.chipBg};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px" data-anim="fade-up">
          <div style="width:84px;height:84px;border-radius:20px;background:${c.accent};display:flex;align-items:center;justify-content:center;font-size:40px">🖼️</div>
          <div style="font-family:var(--ppt-title-font);font-weight:700;font-size:24px;color:${c.title}">Khu vực ảnh</div>
          <div style="${body};font-size:17px;opacity:.75">Thay bằng ảnh của bạn (chỉnh trong trình sửa)</div>
        </div>
      </div>`,
    },
    // 6) CLOSING
    {
      title: cfg.sampleTitles[5],
      inner: `<div style="height:100%;padding:96px;display:flex;flex-direction:column;justify-content:center;gap:32px">
        <div style="${eyebrow}" data-anim="fade-up">KẾT LUẬN</div>
        <h1 style="${h1};font-size:64px;max-width:1100px" data-anim="fade-up">${cfg.closingLine}</h1>
        <div style="display:flex;gap:16px;margin-top:12px" data-anim="fade-up">
          ${['Thông điệp 1', 'Thông điệp 2', 'Thông điệp 3'].map((t) => `<div style="${card};padding:24px 30px;flex:1"><div style="font-family:var(--ppt-title-font);font-weight:700;font-size:22px;color:${c.title}">${t}</div><div style="${body};font-size:16px;opacity:.8;margin-top:6px">Ý ngắn gọn</div></div>`).join('')}
        </div>
        <div style="${body};font-size:16px;opacity:.6;margin-top:20px">${cfg.brand} · mẫu ${cfg.name}</div>
      </div>`,
    },
  ];

  // ── ghi template dir ──
  const tid = cfg.id;
  const dir = path.join(ENGINE, TEMPLATES, tid);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  // copy assets từ base session
  execSync(`cp -r "${path.join(ENGINE, BASE_SESSION, 'assets')}" "${path.join(dir, 'assets')}"`);
  fs.mkdirSync(path.join(dir, 'images'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'videos'), { recursive: true });

  const manifestPages = [];
  pages.forEach((p, idx) => {
    const pageId = `page-${tid.slice(-4)}${idx}`;
    const html = assemblePage(pageId, cfg.colors.pageBg, cfg.colors.body, p.inner);
    fs.writeFileSync(path.join(dir, `${pageId}.html`), html);
    manifestPages.push({ pageNumber: idx + 1, pageId, title: p.title, htmlPath: `${pageId}.html` });
  });

  const manifest = {
    schemaVersion: 1,
    id: tid,
    name: cfg.name,
    description: cfg.description,
    sourceSessionId: null,
    createdAt: 1783500000000 + cfg.order * 1000,
    updatedAt: 1783500000000 + cfg.order * 1000,
    pageCount: manifestPages.length,
    tags: cfg.tags,
    styleId: null,
    designContract: cfg.designContract,
    pages: manifestPages,
  };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  // index.html tối giản (redirect trang đầu)
  fs.writeFileSync(path.join(dir, 'index.html'), `<!doctype html><meta charset="utf-8"><title>${cfg.name}</title>`);
  console.log(`✓ ${cfg.name} → ${dir} (${manifestPages.length} trang)`);
}

// ═══════════════ THEME #1: SUNSET WARM ═══════════════
makeTemplate({
  id: 'tpl_sunset_warm',
  order: 1,
  name: 'Sunset Warm',
  description: 'Tông hoàng hôn ấm — cam/hổ phách, thẻ trắng nổi trên nền gradient. Hợp tin nhẹ nhàng, tổng kết, câu chuyện.',
  tags: ['ấm', 'sáng', 'gradient'],
  brand: 'XNEW · MẪU HOÀNG HÔN',
  coverSub: 'Bố cục ấm áp với thẻ trắng nổi trên nền gradient cam — đặt tiêu đề, phụ đề và điểm nhấn ở đây.',
  closingLine: 'Chốt lại thông điệp chính bằng một câu ngắn, ấm và dễ nhớ.',
  sampleTitles: ['Tiêu đề bìa ấn tượng', 'Số liệu nổi bật', 'Tiến trình 3 bước', 'So sánh hai phương án', 'Slide có ảnh minh hoạ', 'Kết luận & thông điệp'],
  colors: {
    pageBg: 'linear-gradient(135deg, #fed7aa 0%, #fdba74 45%, #fb923c 100%)',
    title: '#7c2d12', body: '#9a3412', accent: '#f97316', accent2: '#fbbf24',
    card: 'rgba(255,255,255,0.9)', border: 'rgba(251,146,60,0.35)', shadow: 'rgba(124,45,18,0.12)',
    chipBg: 'rgba(255,255,255,0.7)', chipText: '#9a3412',
    invBg: '#7c2d12', invText: '#ffffff',
  },
  designContract: {
    theme: 'warm editorial sunset mood', background: 'linear-gradient(135deg, #fed7aa 0%, #fdba74 45%, #fb923c 100%)',
    palette: ['#7c2d12', '#9a3412', '#f97316', '#fbbf24', '#ffffff'],
    titleStyle: 'text-5xl font-extrabold text-[#7c2d12]', layoutMotif: 'white floating cards on warm gradient',
    chartStyle: 'warm tones, soft', shapeLanguage: 'rounded 24px, soft shadow', titleFont: 'Montserrat', bodyFont: 'Inter',
  },
});

// ═══════════════ THEME #2: TOKYO NIGHT ═══════════════
makeTemplate({
  id: 'tpl_tokyo_night',
  order: 2,
  name: 'Tokyo Night',
  description: 'Nền tối navy sâu, chữ sáng, nhấn xanh/tím neon. Hợp chủ đề game, công nghệ, dữ liệu.',
  tags: ['tối', 'tech', 'neon'],
  brand: 'XNEW · MẪU TOKYO NIGHT',
  coverSub: 'Nền tối sang trọng với thẻ kính mờ và nhấn neon — hợp tin công nghệ, game, dữ liệu.',
  closingLine: 'Chốt thông điệp chính bằng một câu mạnh, sắc, dễ nhớ.',
  sampleTitles: ['Tiêu đề bìa công nghệ', 'Số liệu nổi bật', 'Tiến trình 3 bước', 'So sánh hai phương án', 'Slide có ảnh minh hoạ', 'Kết luận & thông điệp'],
  colors: {
    pageBg: 'linear-gradient(135deg, #1a1b26 0%, #24283b 60%, #1f2335 100%)',
    title: '#c0caf5', body: '#a9b1d6', accent: '#7aa2f7', accent2: '#bb9af7',
    card: 'rgba(36,40,59,0.72)', border: 'rgba(122,162,247,0.28)', shadow: 'rgba(0,0,0,0.45)',
    chipBg: 'rgba(122,162,247,0.14)', chipText: '#7aa2f7',
    invBg: 'rgba(122,162,247,0.16)', invText: '#c0caf5',
  },
  designContract: {
    theme: 'deep tokyo-night tech mood', background: 'linear-gradient(135deg, #1a1b26 0%, #24283b 60%, #1f2335 100%)',
    palette: ['#1a1b26', '#c0caf5', '#7aa2f7', '#bb9af7', '#7dcfff'],
    titleStyle: 'text-5xl font-extrabold text-[#c0caf5]', layoutMotif: 'glassy dark panels with neon accents',
    chartStyle: 'neon lines on dark', shapeLanguage: 'rounded 24px, soft glow', titleFont: 'Montserrat', bodyFont: 'Inter',
  },
});

console.log('Xong.');
