/**
 * Sinh template GIÀU: layout pro (html-ppt) + nội dung tiếng Việt tự soạn +
 * màu khóa cứng theo theme (token CSS). Render 1600×900 trong engine.
 * Mỗi template = 1 theme (màu) × bộ layout VN dùng chung.
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ENGINE = path.resolve('.');
const HPPT = 'C:/Users/admin/AppData/Local/Temp/htmlppt';
const BASE_SESSION = 'data/storage/45f127f2-2a82-4781-b253-20f7854dc2b5';
const TEMPLATES = 'data/templates';

const basePage = fs.readFileSync(
  path.join(ENGINE, BASE_SESSION, fs.readdirSync(path.join(ENGINE, BASE_SESSION)).find((f) => f.startsWith('page-') && f.endsWith('.html'))),
  'utf-8'
);
const CONTENT_OPEN = '<main data-block-id="content" data-role="content" class="h-full min-h-0">';
const iOpen = basePage.indexOf(CONTENT_OPEN) + CONTENT_OPEN.length;
const iFit = basePage.indexOf('<script id="ppt-page-fit">');
const HEAD = basePage.slice(0, iOpen);
const TAIL = '</main>\n  </section>\n</div>\n      </div>\n    </main>\n    ' + basePage.slice(iFit);
const baseCss = fs.readFileSync(path.join(HPPT, 'assets/base.css'), 'utf-8');

// CSS custom cho các layout giàu (rút từ html-ppt) + chỉnh cho hộp engine
const CUSTOM = `
.hppt-root{width:100%;height:100%;position:relative;overflow:hidden;background:var(--bg);color:var(--text-1);font-family:var(--font-sans)}
.hppt-root .slide{position:relative!important;inset:auto!important;width:100%!important;height:100%!important;opacity:1!important;transform:none!important;padding:60px 84px;display:flex;flex-direction:column;justify-content:center;overflow:hidden}
:root{--font-sans:"Inter","Noto Sans SC",sans-serif;--font-display:"Montserrat","Inter",sans-serif;--font-serif:"Montserrat","Inter",serif}
/* timeline */
.tl{position:relative;margin-top:40px}
.tl::before{content:"";position:absolute;left:0;right:0;top:48px;height:2px;background:var(--border)}
.tl .trow{display:grid;grid-template-columns:repeat(5,1fr);gap:22px;align-items:start}
.tl .item{position:relative;padding-top:80px;text-align:center}
.tl .dot{position:absolute;top:36px;left:50%;transform:translateX(-50%);width:24px;height:24px;border-radius:50%;background:var(--accent);border:4px solid var(--bg);box-shadow:0 0 0 2px var(--accent)}
.tl .year{font-size:14px;color:var(--text-3);letter-spacing:.1em;text-transform:uppercase;position:absolute;top:0;left:0;right:0;font-weight:600}
.tl h4{font-size:18px;margin:0 0 4px}.tl p{font-size:14px;color:var(--text-2);line-height:1.5}
/* comparison */
.vs{display:grid;grid-template-columns:1fr 90px 1fr;gap:28px;align-items:stretch;margin-top:30px}
.vs .side{padding:30px}.vs .mid{font-size:56px;font-weight:800;color:var(--text-3);display:flex;align-items:center;justify-content:center}
.vs .bad-side{border-top:3px solid var(--bad)}.vs .good-side{border-top:3px solid var(--good)}
.vs h3{font-size:24px;margin:0 0 12px}.vs ul{padding-left:20px;font-size:16px;line-height:1.9;color:var(--text-2);margin:0}
/* process steps */
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin-top:34px}
.step{position:relative;padding:26px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);box-shadow:var(--shadow)}
.step .num{position:absolute;top:-24px;left:22px;width:48px;height:48px;border-radius:50%;background:var(--accent);color:var(--bg);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:20px;box-shadow:var(--shadow)}
.step h4{margin:16px 0 8px;font-size:18px}.step p{font-size:14px;color:var(--text-2);line-height:1.6}
/* image hero (slot) */
.hero{position:relative;height:100%;border-radius:var(--radius-lg);overflow:hidden;box-shadow:var(--shadow-lg)}
.hero .bg{position:absolute;inset:0;background:var(--grad)}
.hero .overlay{position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(0,0,0,.45))}
.hero .slotmark{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#fff;text-align:center;opacity:.9;z-index:2}
.hero .caption{position:absolute;bottom:44px;left:52px;right:52px;color:#fff;z-index:3}
.hero .caption h2{font-size:52px;line-height:1.05;font-weight:800;margin:8px 0 6px}
.hero .caption p{font-size:18px;opacity:.9;max-width:60ch}
/* image grid (slots) */
.gg{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:200px;gap:16px;margin-top:30px}
.gg .cell{border-radius:var(--radius);overflow:hidden;position:relative;box-shadow:var(--shadow);display:flex;align-items:center;justify-content:center;color:#fff;font-size:34px}
.gg .cell span{position:absolute;inset:auto 0 0 0;padding:12px 14px;font-size:13px;background:linear-gradient(transparent,rgba(0,0,0,.5))}
.gg .c1{background:var(--grad);grid-column:span 2;grid-row:span 2}
.gg .c2{background:var(--accent)}.gg .c3{background:var(--accent-2)}
.gg .c4{background:color-mix(in srgb,var(--accent) 60%,#000)}.gg .c5{background:var(--accent-3,var(--accent))}
`;

const escapeThemeBg = (themeCss) => (/--bg\s*:\s*([^;]+);/.exec(themeCss) || [])[1]?.trim() || '#ffffff';

// ── 10 LAYOUT tiếng Việt (nội dung mẫu, thay được) ──
const S = (inner) => `<section class="slide is-active">${inner}</section>`;
const LAYOUTS = {
  cover: () => S(`
    <p class="kicker">XNEW · MẪU THUYẾT TRÌNH</p>
    <h1 class="h1">Tiêu đề bìa <span class="gradient-text">ấn tượng</span><br>đặt ở đây</h1>
    <p class="lede">Một dòng phụ đề ngắn gọn nêu thông điệp chính của bài — thay bằng nội dung của bạn.</p>
    <div class="row wrap mt-l">
      <span class="pill pill-accent">Điểm nhấn 1</span><span class="pill">Điểm nhấn 2</span><span class="pill">Điểm nhấn 3</span>
    </div>`),
  kpi: () => S(`
    <p class="kicker">Số liệu · chỉ số chính</p>
    <h2 class="h2">Những con số nổi bật</h2>
    <div class="grid g4 mt-l">
      ${[['Người chơi', '855K', '↑ 38%'], ['Doanh thu', '2.4M', '↑ 12%'], ['Giữ chân', '74%', '↑ 3đ'], ['Đánh giá', '4.8', '★★★★★']]
        .map(([l, n, d]) => `<div class="card"><p class="eyebrow">${l}</p><div style="font-size:56px;font-weight:800;line-height:1.05;color:var(--text-1)">${n}</div><p class="dim" style="color:var(--good)">${d}</p></div>`).join('')}
    </div>`),
  stat: () => S(`
    <div class="center tc" style="flex-direction:column">
      <p class="kicker">Điểm nhấn · một con số</p>
      <div style="font-size:230px;line-height:1;font-weight:900;letter-spacing:-.05em"><span class="gradient-text">92%</span></div>
      <h3 class="mt-s">thời gian chuẩn bị được tiết kiệm</h3>
      <p class="lede" style="margin:14px auto 0">Thay câu này bằng dẫn giải cho con số: bối cảnh, nguồn, ý nghĩa.</p>
    </div>`),
  timeline: () => S(`
    <p class="kicker">Tiến trình · dòng thời gian</p>
    <h2 class="h2">Các cột mốc chính</h2>
    <div class="tl"><div class="trow">
      ${[['2024 Q1', 'Khởi đầu', 'Mô tả cột mốc đầu tiên.'], ['2024 Q3', 'Tăng trưởng', 'Mở rộng quy mô, thêm tính năng.'], ['2025 Q1', 'Bước ngoặt', 'Sự kiện quan trọng, thay đổi lớn.'], ['2025 Q4', 'Ổn định', 'Củng cố vị thế, tối ưu.'], ['2026', 'Tương lai', 'Định hướng sắp tới.']]
        .map(([y, h, p]) => `<div class="item"><div class="year">${y}</div><div class="dot"></div><h4>${h}</h4><p>${p}</p></div>`).join('')}
    </div></div>`),
  comparison: () => S(`
    <p class="kicker">So sánh · trước & sau</p>
    <h2 class="h2">Từ "vấn đề" đến "giải pháp"</h2>
    <div class="vs">
      <div class="card bad-side side"><h3>📉 Trước</h3><ul><li>Hạn chế thứ nhất</li><li>Hạn chế thứ hai</li><li>Hạn chế thứ ba</li><li>Hạn chế thứ tư</li></ul></div>
      <div class="mid">→</div>
      <div class="card good-side side"><h3>📈 Sau</h3><ul><li>Cải thiện thứ nhất</li><li>Cải thiện thứ hai</li><li>Cải thiện thứ ba</li><li>Cải thiện thứ tư</li></ul></div>
    </div>`),
  quote: () => S(`
    <div class="center tc"><div style="max-width:1040px">
      <div class="serif" style="font-size:130px;line-height:.9;color:var(--accent);opacity:.55">"</div>
      <blockquote class="serif" style="font-size:52px;line-height:1.25;margin:-36px 0 22px;font-style:italic;font-weight:600;color:var(--text-1)">Một câu trích dẫn mạnh mẽ, cô đọng thông điệp cốt lõi của bài thuyết trình.</blockquote>
      <p class="dim" style="font-size:20px;letter-spacing:.06em">— Nguồn / tác giả</p>
    </div></div>`),
  process: () => S(`
    <p class="kicker">Quy trình · các bước</p>
    <h2 class="h2">Cách hoạt động</h2>
    <div class="steps">
      ${[['1', 'Bước một', 'Mô tả ngắn cho bước đầu tiên của quy trình.'], ['2', 'Bước hai', 'Tiếp nối bước một, giữ nội dung gọn.'], ['3', 'Bước ba', 'Chuyển sang giai đoạn kế tiếp.'], ['4', 'Bước bốn', 'Kết quả / cột mốc cuối cùng.']]
        .map(([n, h, p]) => `<div class="step"><div class="num">${n}</div><h4>${h}</h4><p>${p}</p></div>`).join('')}
    </div>`),
  imagehero: () => S(`
    <div class="hero" data-ppt-image-slot="1">
      <div class="bg"></div><div class="overlay"></div>
      <div class="slotmark"><div style="font-size:52px">🖼️</div><div style="font-weight:700;font-size:20px;margin-top:6px">Khu vực ảnh lớn</div><div style="font-size:14px;opacity:.85">Thay bằng ảnh của bạn</div></div>
      <div class="caption"><span class="pill">Ảnh bìa</span><h2>Tiêu đề đè lên ảnh</h2><p>Chú thích ngắn cho hình ảnh — mô tả bối cảnh hoặc điểm nhấn.</p></div>
    </div>`),
  imagegrid: () => S(`
    <p class="kicker">Thư viện · lưới ảnh</p>
    <h2 class="h2">Bộ ảnh minh hoạ</h2>
    <div class="gg" data-ppt-image-slot="1">
      <div class="cell c1">🖼️<span>Ảnh chính — thay bằng ảnh của bạn</span></div>
      <div class="cell c2">🖼️<span>Ảnh 2</span></div><div class="cell c3">🖼️<span>Ảnh 3</span></div>
      <div class="cell c4">🖼️<span>Ảnh 4</span></div><div class="cell c5">🖼️<span>Ảnh 5</span></div>
    </div>`),
  thanks: () => S(`
    <div class="center tc" style="flex-direction:column">
      <p class="kicker">Kết thúc</p>
      <h1 class="h1" style="font-size:88px">Cảm ơn <span class="gradient-text">đã theo dõi</span></h1>
      <p class="lede" style="margin:8px auto 0">Thêm lời kêu gọi hành động, thông tin liên hệ hoặc nguồn ở đây.</p>
      <div class="row wrap mt-l" style="justify-content:center"><span class="pill pill-accent">Liên hệ</span><span class="pill">Website</span><span class="pill">Nguồn</span></div>
    </div>`),
};
const ORDER = ['cover', 'kpi', 'stat', 'timeline', 'comparison', 'quote', 'process', 'imagehero', 'imagegrid', 'thanks'];
const TITLES = { cover: 'Bìa', kpi: 'Chỉ số chính', stat: 'Số liệu nổi bật', timeline: 'Dòng thời gian', comparison: 'So sánh', quote: 'Trích dẫn', process: 'Quy trình', imagehero: 'Ảnh bìa lớn', imagegrid: 'Lưới ảnh', thanks: 'Cảm ơn' };

function makeTemplate(cfg) {
  const themeCss = fs.readFileSync(path.join(HPPT, `assets/themes/${cfg.theme}.css`), 'utf-8');
  const styleTag = `<style id="hppt-style">${baseCss}\n${themeCss}\n${CUSTOM}</style>`;
  const themeBg = escapeThemeBg(themeCss);
  const tid = cfg.id;
  const dir = path.join(ENGINE, TEMPLATES, tid);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  execSync(`cp -r "${path.join(ENGINE, BASE_SESSION, 'assets')}" "${path.join(dir, 'assets')}"`);
  fs.mkdirSync(path.join(dir, 'images'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'videos'), { recursive: true });

  const pages = [];
  ORDER.forEach((key, idx) => {
    const pageId = `page-${tid.replace(/[^a-z0-9]/gi, '').slice(-6)}${idx}`;
    const head = HEAD.replace(/--ppt-page-bg:\s*[^;]+;/, `--ppt-page-bg: ${themeBg};`).replace(/<body data-page-id="[^"]*">/, `<body data-page-id="${pageId}">`);
    const inner = `${styleTag}<div class="hppt-root">${LAYOUTS[key]()}</div>`;
    fs.writeFileSync(path.join(dir, `${pageId}.html`), head + '\n' + inner + '\n' + TAIL);
    pages.push({ pageNumber: idx + 1, pageId, title: TITLES[key], htmlPath: `${pageId}.html` });
  });
  const manifest = {
    schemaVersion: 1, id: tid, name: cfg.name, description: cfg.description,
    sourceSessionId: null, createdAt: 1783700000000 + cfg.order * 1000, updatedAt: 1783700000000 + cfg.order * 1000,
    pageCount: pages.length, tags: cfg.tags, styleId: null,
    designContract: { theme: cfg.name, background: '', palette: [], titleStyle: '', layoutMotif: '', chartStyle: '', shapeLanguage: '', titleFont: 'Montserrat', bodyFont: 'Inter' }, pages,
  };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  fs.writeFileSync(path.join(dir, 'index.html'), `<!doctype html><meta charset="utf-8"><title>${cfg.name}</title>`);
  console.log(`✓ ${cfg.name} → ${pages.length} trang`);
}

// 30 theme × bộ 10 layout VN dùng chung
const THEMES = [
  ['sunset-warm', 'Sunset Warm', 'Hoàng hôn ấm — cam/hổ phách', ['ấm', 'sáng']],
  ['tokyo-night', 'Tokyo Night', 'Tối tech — navy/neon', ['tối', 'tech']],
  ['minimal-white', 'Minimal White', 'Trắng tối giản, sạch sẽ', ['sáng', 'tối giản']],
  ['editorial-serif', 'Editorial Serif', 'Tạp chí serif thanh lịch', ['sáng', 'tạp chí']],
  ['soft-pastel', 'Soft Pastel', 'Pastel dịu nhẹ', ['pastel', 'sáng']],
  ['swiss-grid', 'Swiss Grid', 'Lưới Thụy Sĩ, kỷ luật', ['sáng', 'grid']],
  ['xiaohongshu-white', 'Xiaohongshu White', 'Tiểu Hồng Thư trắng', ['sáng', 'social']],
  ['corporate-clean', 'Corporate Clean', 'Doanh nghiệp sạch sẽ', ['sáng', 'business']],
  ['academic-paper', 'Academic Paper', 'Học thuật, báo cáo', ['sáng', 'academic']],
  ['magazine-bold', 'Magazine Bold', 'Tạp chí chữ đậm', ['sáng', 'bold']],
  ['pitch-deck-vc', 'Pitch Deck', 'Gọi vốn, thuyết trình', ['business', 'pitch']],
  ['japanese-minimal', 'Japanese Minimal', 'Nhật tối giản', ['sáng', 'zen']],
  ['dracula', 'Dracula', 'Tối tím dev', ['tối', 'dev']],
  ['gruvbox-dark', 'Gruvbox Dark', 'Tối retro ấm', ['tối', 'retro']],
  ['catppuccin-mocha', 'Catppuccin Mocha', 'Tối dịu pastel', ['tối', 'dịu']],
  ['catppuccin-latte', 'Catppuccin Latte', 'Sáng dịu pastel', ['sáng', 'dịu']],
  ['nord', 'Nord', 'Lạnh Bắc Âu', ['tối', 'lạnh']],
  ['arctic-cool', 'Arctic Cool', 'Băng giá xanh', ['sáng', 'lạnh']],
  ['terminal-green', 'Terminal Green', 'Terminal xanh lá', ['tối', 'code']],
  ['blueprint', 'Blueprint', 'Bản vẽ kỹ thuật', ['tối', 'tech']],
  ['cyberpunk-neon', 'Cyberpunk Neon', 'Neon tương lai', ['tối', 'neon']],
  ['vaporwave', 'Vaporwave', 'Vaporwave hoài niệm', ['tối', 'vibrant']],
  ['y2k-chrome', 'Y2K Chrome', 'Y2K chrome bóng', ['sáng', 'vibrant']],
  ['retro-tv', 'Retro TV', 'Truyền hình retro', ['sáng', 'retro']],
  ['aurora', 'Aurora', 'Cực quang gradient', ['tối', 'gradient']],
  ['rainbow-gradient', 'Rainbow Gradient', 'Cầu vồng gradient', ['sáng', 'gradient']],
  ['neo-brutalism', 'Neo Brutalism', 'Brutalism đậm nét', ['sáng', 'bold']],
  ['memphis-pop', 'Memphis Pop', 'Memphis vui nhộn', ['sáng', 'pop']],
  ['rose-pine', 'Rose Pine', 'Hồng thông dịu', ['tối', 'dịu']],
  ['midcentury', 'Midcentury', 'Giữa thế kỷ ấm', ['sáng', 'retro']],
];

THEMES.forEach(([theme, name, description, tags], i) => {
  let slug = theme.replace(/-/g, '_');
  if (slug.length < 8) slug += '_deck';
  makeTemplate({ id: 'tpl_' + slug, order: i + 1, name, description: description + ' — layout pro, màu khóa cứng.', tags, theme });
});
console.log(`Xong — ${THEMES.length} template.`);
