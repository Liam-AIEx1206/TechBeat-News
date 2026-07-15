/**
 * Port template GIÀU từ bộ html-ppt (36 theme + 31 layout token-based) sang
 * định dạng engine (trang 1600×900 + scaffold). Màu/tương phản khóa cứng bằng
 * CSS token → luôn đúng style, luôn đọc được, bố cục pro & đa dạng.
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ENGINE = path.resolve('.');
const HPPT = 'C:/Users/admin/AppData/Local/Temp/htmlppt';
const BASE_SESSION = 'data/storage/45f127f2-2a82-4781-b253-20f7854dc2b5'; // shell: scaffold + font Inter/Montserrat (VN chuẩn)
const TEMPLATES = 'data/templates';

// shell engine (head+scaffold+fit+motion) — chèn CSS hppt + nội dung vào
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

// CSS phủ: .slide vừa hộp 1600×900, ẩn chrome, map font html-ppt → font engine (VN chuẩn)
const OVERRIDE = `
/* engine-box adapt */
.hppt-root{width:100%;height:100%;position:relative;overflow:hidden;background:var(--bg);color:var(--text-1);font-family:var(--font-sans)}
.hppt-root .slide{position:relative!important;inset:auto!important;width:100%!important;height:100%!important;opacity:1!important;transform:none!important;pointer-events:auto!important;padding:64px 84px;display:flex;flex-direction:column;justify-content:center;overflow:hidden}
.hppt-root .deck-header,.hppt-root .deck-footer,.hppt-root .slide-number,.hppt-root .progress-bar,.hppt-root .notes,.hppt-root .notes-overlay,.hppt-root .overview{display:none!important}
:root{--font-sans:"Inter","Noto Sans SC",sans-serif;--font-display:"Montserrat","Inter",sans-serif;--font-serif:"Montserrat","Inter",serif;--font-mono:ui-monospace,monospace}
`;

function extractSlide(layoutHtml) {
  const i = layoutHtml.indexOf('<section class="slide');
  if (i < 0) return null;
  const j = layoutHtml.lastIndexOf('</section>');
  if (j < 0) return null;
  return layoutHtml.slice(i, j + '</section>'.length);
}

function makeTemplate(cfg) {
  const themeCss = fs.readFileSync(path.join(HPPT, `assets/themes/${cfg.theme}.css`), 'utf-8');
  const styleTag = `<style id="hppt-style">${baseCss}\n${themeCss}\n${OVERRIDE}</style>`;

  const tid = cfg.id;
  const dir = path.join(ENGINE, TEMPLATES, tid);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  execSync(`cp -r "${path.join(ENGINE, BASE_SESSION, 'assets')}" "${path.join(dir, 'assets')}"`);
  fs.mkdirSync(path.join(dir, 'images'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'videos'), { recursive: true });

  const pages = [];
  cfg.layouts.forEach((lay, idx) => {
    const layoutHtml = fs.readFileSync(path.join(HPPT, `templates/single-page/${lay}.html`), 'utf-8');
    const slide = extractSlide(layoutHtml);
    if (!slide) { console.warn('  ! bỏ qua', lay); return; }
    const pageId = `page-${tid.replace(/[^a-z0-9]/gi, '').slice(-6)}${idx}`;
    // page bg lấy theo theme (--bg): set trực tiếp lên guard var
    const themeBg = (/--bg\s*:\s*([^;]+);/.exec(themeCss) || [])[1]?.trim() || '#ffffff';
    const head = HEAD
      .replace(/--ppt-page-bg:\s*[^;]+;/, `--ppt-page-bg: ${themeBg};`)
      .replace(/<body data-page-id="[^"]*">/, `<body data-page-id="${pageId}">`);
    const inner = `${styleTag}<div class="hppt-root">${slide}</div>`;
    const html = head + '\n' + inner + '\n' + TAIL;
    fs.writeFileSync(path.join(dir, `${pageId}.html`), html);
    pages.push({ pageNumber: idx + 1, pageId, title: cfg.titles[idx] || lay, htmlPath: `${pageId}.html` });
  });

  const manifest = {
    schemaVersion: 1, id: tid, name: cfg.name, description: cfg.description,
    sourceSessionId: null, createdAt: 1783600000000 + cfg.order * 1000, updatedAt: 1783600000000 + cfg.order * 1000,
    pageCount: pages.length, tags: cfg.tags, styleId: null,
    designContract: { theme: cfg.name, background: '', palette: [], titleStyle: '', layoutMotif: '', chartStyle: '', shapeLanguage: '', titleFont: 'Montserrat', bodyFont: 'Inter' },
    pages,
  };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  fs.writeFileSync(path.join(dir, 'index.html'), `<!doctype html><meta charset="utf-8"><title>${cfg.name}</title>`);
  console.log(`✓ ${cfg.name} → ${pages.length} trang`);
}

const LAYOUTS = ['cover', 'kpi-grid', 'stat-highlight', 'timeline', 'comparison', 'big-quote', 'image-hero', 'thanks'];
const TITLES = ['Bìa', 'Chỉ số chính', 'Số liệu nổi bật', 'Dòng thời gian', 'So sánh', 'Trích dẫn', 'Ảnh lớn (slot)', 'Cảm ơn'];

makeTemplate({ id: 'tpl_hppt_sunset', order: 1, name: 'Sunset Warm (Pro)', description: 'Hoàng hôn ấm — bộ layout pro html-ppt, màu khóa cứng.', tags: ['ấm', 'sáng', 'pro'], theme: 'sunset-warm', layouts: LAYOUTS, titles: TITLES });
console.log('Xong.');
