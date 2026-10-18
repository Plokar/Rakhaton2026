// Prezentace MedTeam · Rakathon 2026 (13 slidů) ve vizuálním jazyce videí: tmavý „sál“, tyrkysová, fialová = AI.
// node build_deck.js  → MedTeam_Prezentace.pptx (pak téma přes apply_theme.js, viz README v FILM_SCENAR §10)
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const sharp = require('sharp');

const OUT = 'MedTeam_Prezentace.pptx';
const A = (f) => path.join(__dirname, 'assets', f);
const HOOK = path.join(__dirname, '..', 'out', 'medteam-hook.mp4');

const THEME = {
  name: 'MedTeam',
  headFontFace: 'Segoe UI Semibold',
  bodyFontFace: 'Segoe UI',
  colors: {
    dk1: '0B1118', lt1: 'F1F5F9', dk2: '111A24', lt2: '94A3B8',
    accent1: '2DD4BF', accent2: 'A78BFA', accent3: 'FBBF24', accent4: 'F87171', accent5: 'C8102E', accent6: '3FB4C0',
    hlink: '2DD4BF', folHlink: 'A78BFA',
  },
};

// Ikony ze stejné sady jako aplikace (lucide), obarvené a zrastrované na 256 px.
const ICON_HEX = { teal: '2DD4BF', ai: 'A78BFA', amber: 'FBBF24', red: 'F87171', ink: 'F1F5F9', muted: '94A3B8' };
async function icon(name, tone = 'teal') {
  const svg = fs.readFileSync(require.resolve(`lucide-static/icons/${name}.svg`), 'utf8')
    .replace(/stroke="currentColor"/g, `stroke="#${ICON_HEX[tone]}"`)
    .replace(/width="24"/, 'width="256"').replace(/height="24"/, 'height="256"')
    .replace(/stroke-width="2"/, 'stroke-width="1.75"');
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

async function build() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13,333 × 7,5 in
  pres.author = 'Tým MedTeam';
  pres.title = 'MedTeam · MDT Copilot · Rakathon 2026';
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const INK = C.background1, MUTED = C.background2, SURF = C.text2, TEAL = C.accent1, AI = C.accent2, AMBER = C.accent3, RED = C.accent4;

  // ── rozvržení (layouts) ──
  const footer = [
    { image: { x: 0.7, y: 6.98, w: 0.327, h: 0.3, path: A('mark.png'), altText: 'MedTeam' } },
    { text: { text: 'MedTeam · MDT Copilot', options: { x: 1.12, y: 6.93, w: 4, h: 0.4, fontSize: 12, color: MUTED, margin: 0, valign: 'middle' } } },
  ];
  const titlePh = { placeholder: { options: { name: 'title', type: 'title', x: 0.7, y: 0.45, w: 11.9, h: 0.95, fontSize: 36, color: INK, align: 'left', valign: 'middle', margin: 0 }, text: '' } };
  const slideNumber = { x: 12.1, y: 6.93, w: 0.5, h: 0.4, fontSize: 12, color: MUTED, align: 'right' };
  const pic = (name, x, y, w, h, text) => ({ placeholder: { options: { name, type: 'pic', x, y, w, h, color: MUTED, fontSize: 16, align: 'center', valign: 'middle' }, text } });

  pres.defineSlideMaster({ title: 'TITLE', background: { path: A('bg_title.jpg') }, objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 4.55, w: 7.4, h: 1.1, fontSize: 48, color: INK, align: 'left', margin: 0, valign: 'middle' }, text: '' } },
  ] });
  pres.defineSlideMaster({ title: 'VIDEO', background: { color: '000000' }, objects: [] });
  pres.defineSlideMaster({ title: 'CONTENT', background: { path: A('bg_content.jpg') }, objects: [...footer, titlePh], slideNumber });
  pres.defineSlideMaster({ title: 'PHOTO1', background: { path: A('bg_content.jpg') }, objects: [...footer, titlePh, pic('photo', 0.7, 1.65, 7.4, 4.95, 'Vložte fotku z jednání komise (snímek na plátně, lékař čte zprávy)')], slideNumber });
  pres.defineSlideMaster({ title: 'PHOTO2', background: { path: A('bg_content.jpg') }, objects: [
    ...footer, titlePh, pic('photoA', 0.7, 1.65, 5.8, 3.85, 'Vložte fotku AI serveru'), pic('photoB', 6.83, 1.65, 5.8, 3.85, 'Vložte fotku Raspberry Pi'),
  ], slideNumber });
  const TEAM_X = [0.7, 3.8, 6.9, 10.0];
  pres.defineSlideMaster({ title: 'TEAM4', background: { path: A('bg_content.jpg') }, objects: [
    ...footer, titlePh, ...TEAM_X.map((x, i) => pic(`photo${i + 1}`, x, 1.75, 2.6, 2.6, 'Fotka')),
  ], slideNumber });

  // ── stavební prvky ──
  const card = (s, x, y, w, h, name, opts = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: SURF }, line: { color: opts.line ?? MUTED, transparency: opts.lineT ?? 72, width: opts.lw ?? 1 }, objectName: name,
  });
  const iconCircle = async (s, x, y, d, ic, tone, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: SURF }, line: { color: tone === 'ai' ? AI : tone === 'amber' ? AMBER : tone === 'red' ? RED : TEAL, width: 1.5 }, objectName: `${name} kruh` });
    s.addImage({ data: await icon(ic, tone), x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: `${name} ikona`, altText: name });
  };
  const text = (s, t, o) => s.addText(t, { isTextBox: true, margin: 0, color: INK, ...o });
  /** Šipka z bodu do bodu (čára se převrátí, když vede vzhůru). */
  const arrow = (s, x1, y1, x2, y2, name) => s.addShape(pres.shapes.LINE, {
    x: x1, y: Math.min(y1, y2), w: x2 - x1, h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color: MUTED, width: 1.25, endArrowType: 'triangle' }, objectName: name,
  });
  const photoFrame = async (s, x, y, w, h, label) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: SURF }, line: { color: MUTED, transparency: 45, width: 1.25, dashType: 'dash' }, objectName: `Rámeček: ${label}` });
    const d = Math.min(0.7, h * 0.25);
    s.addImage({ data: await icon('camera', 'muted'), x: x + w / 2 - d / 2, y: y + h / 2 - d * 0.85, w: d, h: d, objectName: `Rámeček ikona: ${label}`, altText: label });
    text(s, label, { x: x + 0.2, y: y + h / 2 + d * 0.3, w: w - 0.4, h: 0.6, fontSize: h > 3 ? 16 : 12, color: MUTED, align: 'center', valign: 'top' });
  };
  const qrCard = (s, x, y, size) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: size, h: size, rectRadius: 0.18, fill: { color: 'FFFFFF' }, line: { type: 'none' }, objectName: 'QR karta',
      shadow: { type: 'outer', color: '000000', opacity: 0.45, blur: 18, offset: 6, angle: 90 } });
    const pad = size * 0.07;
    s.addImage({ path: A('qr.png'), x: x + pad, y: y + pad, w: size - 2 * pad, h: size - 2 * pad, objectName: 'QR kód', altText: 'QR kód na medteam.nervelabs.co.uk' });
  };

  // ── 1 · Uvítání ──
  pres.addSection({ title: 'Úvod' });
  let s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'Úvod' });
  s.addImage({ path: A('logo.png'), x: 0.75, y: 1.75, w: 7.2, h: 2.38, objectName: 'Logo MedTeam', altText: 'MedTeam' });
  text(s, [{ text: 'MDT Copilot', options: { bold: true, color: INK } }, { text: ' · podklady pro onkologickou komisi', options: { color: MUTED } }], { x: 0.95, y: 4.35, w: 7.4, h: 0.5, fontSize: 22 });
  text(s, 'Rakathon 2026 · výzva Asseco CE · InterSystems IRIS for Health', { x: 0.95, y: 6.55, w: 8, h: 0.4, fontSize: 14, color: MUTED });
  qrCard(s, 9.2, 1.45, 3.4);
  text(s, 'Vyzkoušejte si demo', { x: 9.0, y: 5.05, w: 3.8, h: 0.5, fontSize: 22, bold: true, align: 'center' });
  text(s, 'medteam.nervelabs.co.uk', { x: 9.0, y: 5.55, w: 3.8, h: 0.4, fontSize: 16, color: TEAL, align: 'center' });
  s.addNotes('Svítí, než začneme prezentovat (publikum si může naskenovat QR a vyzkoušet demo). Pak přejít na slide 2 s hookem a teprve po něm začít mluvit.');

  // ── 2 · Video (hook) ──
  s = pres.addSlide({ masterName: 'VIDEO', sectionTitle: 'Úvod' });
  const poster = 'data:image/jpeg;base64,' + fs.readFileSync(A('hook_poster.jpg')).toString('base64');
  s.addMedia({ type: 'video', path: HOOK, cover: poster, x: 0, y: 0, w: 13.333, h: 7.5, objectName: 'Hook video' });
  s.addNotes('Hook (30 s). V PowerPointu: vyberte video → Přehrávání → Spustit: Automaticky (ať se spustí hned po přechodu na slide). Během videa nemluvíme, začínáme až po logu.');

  // ── 3 · Co je MDT ──
  pres.addSection({ title: 'Problém' });
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problém' });
  s.addText('Co je MDT', { placeholder: 'title' });
  const MDT = [
    ['M', 'Multi-', 'více oborů medicíny nad jedním pacientem'],
    ['D', 'disciplinární', 'každý přináší pohled své specializace'],
    ['T', 'tým', 'jedno společné rozhodnutí o léčbě'],
  ];
  MDT.forEach(([l, w, d], i) => {
    const x = 0.7 + i * 4.125;
    card(s, x, 1.75, 3.65, 4.2, `Karta ${l}`);
    text(s, l, { x: x + 0.4, y: 1.95, w: 2.8, h: 1.6, fontSize: 96, bold: true, color: TEAL, fontFace: THEME.headFontFace });
    text(s, w, { x: x + 0.4, y: 3.6, w: 2.9, h: 0.6, fontSize: 28, bold: true });
    text(s, d, { x: x + 0.4, y: 4.3, w: 2.9, h: 1.2, fontSize: 18, color: MUTED, valign: 'top' });
  });
  text(s, 'V onkologii se MDT říká onkologická komise (tumor board).', { x: 0.7, y: 6.2, w: 11.9, h: 0.45, fontSize: 18, color: MUTED });
  s.addNotes('MDT = multidisciplinární tým. V onkologii jde o komisi, kde se specialisté z různých oborů společně rozhodnou o léčbě pacienta s nádorem.');

  // ── 4 · Fungování MDT v praxi ──
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problém' });
  s.addText('Fungování MDT v praxi', { placeholder: 'title' });
  const cx = 3.75, cy = 4.15, r = 1.95, d = 0.8;
  await iconCircle(s, cx - 0.55, cy - 0.55, 1.1, 'user-round', 'ink', 'Pacient');
  text(s, 'Pacient', { x: cx - 1, y: cy + 0.6, w: 2, h: 0.35, fontSize: 14, bold: true, align: 'center' });
  const ROLES = [['stethoscope', 'Klinický onkolog'], ['scissors', 'Chirurg'], ['scan', 'Radiolog'], ['microscope', 'Patolog'], ['radiation', 'Radiační onkolog'], ['message-circle', 'Hlas pacienta']];
  for (let i = 0; i < ROLES.length; i++) {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / ROLES.length;
    const x = cx + r * Math.cos(a) * 1.25, y = cy + r * Math.sin(a);
    await iconCircle(s, x - d / 2, y - d / 2 - 0.15, d, ROLES[i][0], 'teal', ROLES[i][1]);
    text(s, ROLES[i][1], { x: x - 1.1, y: y + 0.3, w: 2.2, h: 0.35, fontSize: 14, align: 'center', color: MUTED });
  }
  text(s, 'Parta doktorů se schází, aby společně probrala, co se bude s pacientem dít dál.', { x: 7.6, y: 2.2, w: 5.0, h: 2.3, fontSize: 28, bold: true, valign: 'top' });
  text(s, 'Každý vidí jen svou část: snímky, histologii, laboratoř, dotazníky pacienta. Rozhodnutí je ale společné.', { x: 7.6, y: 4.6, w: 5.0, h: 1.4, fontSize: 18, color: MUTED, valign: 'top' });
  s.addNotes('Jak to funguje: u jednoho stolu sedí onkolog, chirurg, radiolog, patolog, radiační onkolog a hlas pacienta (dotazníky). Probírají pacienta po pacientovi a rozhodují, co bude dál.');

  // ── 5 · Jádro problému (fotka z boardu) ──
  s = pres.addSlide({ masterName: 'PHOTO1', sectionTitle: 'Problém' });
  s.addText('Jádro problému', { placeholder: 'title' });
  await photoFrame(s, 0.7, 1.65, 7.4, 4.95, 'Sem vložte fotku z jednání komise');
  s.addText('', { placeholder: 'photo' });
  await iconCircle(s, 8.55, 1.75, 0.8, 'ear-off', 'amber', 'Přeslechnutí');
  text(s, 'Na plátně je snímek a doktor nahlas čte zprávy.', { x: 8.55, y: 2.8, w: 4.1, h: 1.2, fontSize: 22, valign: 'top' });
  card(s, 8.55, 4.2, 4.08, 2.4, 'Problém', { line: AMBER, lineT: 40, lw: 1.5 });
  text(s, 'Jakmile něco přeslechneš, jsi ztracen.', { x: 8.85, y: 4.45, w: 3.5, h: 1.9, fontSize: 28, bold: true, color: AMBER, valign: 'middle' });
  s.addNotes('Fotka z jednání: na tabuli snímek, doktor čte zprávy. Problém: jakmile něco přeslechneš, jsi ztracen. A zeptat se znovu znamená zdržet celou komisi.');

  // ── 6 · Prvotní řešení ──
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problém' });
  s.addText('Prvotní řešení: nápověda v aplikaci', { placeholder: 'title' });
  await iconCircle(s, 0.7, 1.8, 0.8, 'search', 'teal', 'Hledání');
  text(s, 'Nápověda existuje. Stačí se podívat do aplikace.', { x: 0.7, y: 2.85, w: 5.2, h: 1.4, fontSize: 28, bold: true, valign: 'top' });
  text(s, [
    { text: 'zprávy a nálezy', options: { bullet: true, breakLine: true } },
    { text: 'laboratoř a snímky', options: { bullet: true, breakLine: true } },
    { text: 'dotazníky pacienta', options: { bullet: true } },
  ], { x: 0.7, y: 4.4, w: 5.2, h: 1.5, fontSize: 18, color: MUTED, paraSpaceAfter: 6, valign: 'top' });
  // schéma husté nemocniční aplikace (abstraktní, ne skutečný produkt)
  card(s, 6.4, 1.75, 6.25, 4.85, 'Okno aplikace', { lineT: 60 });
  [0, 1, 2].forEach((i) => s.addShape(pres.shapes.OVAL, { x: 6.65 + i * 0.25, y: 1.98, w: 0.13, h: 0.13, fill: { color: MUTED, transparency: 50 }, line: { type: 'none' }, objectName: `Tečka ${i + 1}` }));
  const TABS = ['Zprávy', 'Laboratoř', 'Zobrazování', 'Dotazníky', 'Medikace'];
  let tx = 6.65;
  TABS.forEach((t, i) => {
    const w = 0.25 + t.length * 0.085;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: tx, y: 2.35, w, h: 0.36, rectRadius: 0.18, fill: { color: i === 0 ? TEAL : SURF, transparency: i === 0 ? 75 : 0 }, line: { color: MUTED, transparency: 70, width: 0.75 }, objectName: `Záložka ${t}` });
    text(s, t, { x: tx, y: 2.35, w, h: 0.36, fontSize: 11, color: i === 0 ? INK : MUTED, align: 'center', valign: 'middle' });
    tx += w + 0.1;
  });
  for (let i = 0; i < 9; i++) {
    const y = 2.95 + i * 0.38;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.65, y, w: 0.9, h: 0.12, rectRadius: 0.06, fill: { color: INK, transparency: 82 }, line: { type: 'none' }, objectName: `Řádek ${i + 1} popisek` });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y, w: 2.2 + ((i * 37) % 23) / 10, h: 0.12, rectRadius: 0.06, fill: { color: MUTED, transparency: 80 }, line: { type: 'none' }, objectName: `Řádek ${i + 1} text` });
  }
  s.addNotes('Prvotní řešení: všechno je někde v aplikaci, zprávy, laboratoř, snímky, dotazníky. Stačí se podívat.');

  // ── 7 · Úskalí: nedostatek času ──
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Problém' });
  s.addText('Úskalí: na hledání není čas', { placeholder: 'title' });
  card(s, 0.7, 1.75, 5.4, 4.85, 'Čas na pacienta', { line: AMBER, lineT: 55 });
  await iconCircle(s, 1.1, 2.1, 0.8, 'timer', 'amber', 'Čas');
  text(s, '3–5 min', { x: 1.1, y: 3.05, w: 4.8, h: 1.6, fontSize: 80, bold: true, color: AMBER, fontFace: THEME.headFontFace });
  text(s, 'na jednoho pacienta', { x: 1.1, y: 4.6, w: 4.6, h: 0.5, fontSize: 22 });
  text(s, 'Pět specialistů se za tu dobu musí zorientovat v pacientovi, kterého často vidí poprvé.', { x: 1.1, y: 5.2, w: 4.6, h: 1.1, fontSize: 16, color: MUTED, valign: 'top' });
  text(s, 'Tohle všechno už víme.', { x: 6.75, y: 2.1, w: 5.9, h: 0.7, fontSize: 28, color: MUTED });
  text(s, 'Hledat v aplikaci uprostřed jednání ale nechce nikdo.', { x: 6.75, y: 2.85, w: 5.9, h: 1.6, fontSize: 32, bold: true, valign: 'top' });
  text(s, 'Než informaci dohledáš, diskuse už běží dál.', { x: 6.75, y: 4.7, w: 5.9, h: 0.6, fontSize: 18, color: MUTED });
  s.addNotes('Tohle všechno už víme. Ale hledat v aplikaci není to, co v tu chvíli chceš dělat. Komise má na pacienta 3 až 5 minut, na proklikávání prostě není čas.');

  // ── 8 · Hlavní řešení: AI bot ──
  pres.addSection({ title: 'Řešení' });
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Řešení' });
  s.addText([{ text: 'Chybí ti informace? ', options: {} }, { text: 'Zeptej se AI bota', options: { color: AI } }], { placeholder: 'title' });
  card(s, 0.7, 1.65, 11.9, 2.9, 'Ukázka odpovědi', { line: AI, lineT: 50, lw: 1.25 });
  s.addImage({ path: A('qa_answer.png'), x: 0.95, y: 1.85, w: 11.4, h: 2.5, objectName: 'Odpověď AI z aplikace', altText: 'Skutečná odpověď AI v aplikaci MedTeam s citacemi zdrojů' });
  const FEAT = [
    ['bot', 'ai', 'Odpoví hned', 'otázka vlastními slovy, odpověď za pár sekund'],
    ['database', 'teal', 'Jen z dat pacienta', 'čte z nemocniční databáze InterSystems IRIS (FHIR)'],
    ['file-search', 'teal', 'S citací zdroje', 'každá věta s odkazem a mírou shody, ověření jedním klikem'],
  ];
  for (let i = 0; i < FEAT.length; i++) {
    const x = 0.7 + i * 4.0;
    await iconCircle(s, x, 4.95, 0.75, FEAT[i][0], FEAT[i][1], FEAT[i][2]);
    text(s, FEAT[i][2], { x: x + 0.95, y: 4.95, w: 2.9, h: 0.45, fontSize: 20, bold: true });
    text(s, FEAT[i][3], { x: x + 0.95, y: 5.42, w: 2.9, h: 0.9, fontSize: 15, color: MUTED, valign: 'top' });
  }
  s.addNotes('Hlavní řešení: chybí ti informace? Zeptej se našeho AI bota. Odpoví okamžitě, jen z dat pacienta v nemocniční databázi, a každá věta má citaci zdroje. Na obrazovce je skutečná odpověď z aplikace.');

  // ── 9 · Infrastruktura (bez AI) ──
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Řešení' });
  s.addText('Infrastruktura dnes (bez AI)', { placeholder: 'title' });
  const SRC = [['file-text', 'NIS · zprávy'], ['image', 'PACS · snímky'], ['activity', 'Laboratoř'], ['messages-square', 'Dotazníky pacienta']];
  for (let i = 0; i < SRC.length; i++) {
    const y = 1.75 + i * 1.18;
    card(s, 0.7, y, 2.9, 0.95, SRC[i][1]);
    s.addImage({ data: await icon(SRC[i][0], 'muted'), x: 0.92, y: y + 0.24, w: 0.47, h: 0.47, objectName: `${SRC[i][1]} ikona`, altText: SRC[i][1] });
    text(s, SRC[i][1], { x: 1.55, y, w: 1.95, h: 0.95, fontSize: 15, valign: 'middle' });
    arrow(s, 3.6, y + 0.475, 4.55, 3.8, `Šipka ${SRC[i][1]} → IRIS`);
  }
  const node = async (x, y, w, h, ic, title, sub, tone, name) => {
    card(s, x, y, w, h, name, { line: tone === 'teal' ? TEAL : MUTED, lineT: tone === 'teal' ? 20 : 60, lw: tone === 'teal' ? 1.75 : 1 });
    s.addImage({ data: await icon(ic, tone), x: x + w / 2 - 0.3, y: y + 0.3, w: 0.6, h: 0.6, objectName: `${name} ikona`, altText: name });
    text(s, title, { x: x + 0.15, y: y + 1.0, w: w - 0.3, h: 0.8, fontSize: 18, bold: true, align: 'center', valign: 'top' });
    text(s, sub, { x: x + 0.15, y: y + 1.75, w: w - 0.3, h: 0.7, fontSize: 14, color: MUTED, align: 'center', valign: 'top' });
  };
  await node(4.55, 2.55, 2.9, 2.5, 'database', 'InterSystems IRIS for Health', 'FHIR R4 · jeden zdroj dat pacienta', 'teal', 'IRIS');
  await node(8.0, 2.55, 2.0, 2.5, 'laptop', 'MedTeam', 'webová aplikace', 'muted', 'MedTeam');
  await node(10.55, 2.55, 2.05, 2.5, 'presentation', 'Komise', 'notebook předsedy + plátno', 'muted', 'Komise');
  [[7.45, 8.0], [10.0, 10.55]].forEach(([a, b], i) => s.addShape(pres.shapes.LINE, { x: a, y: 3.8, w: b - a, h: 0, line: { color: MUTED, width: 1.25, endArrowType: 'triangle' }, objectName: `Spojení ${i + 1}` }));
  text(s, 'Data pacienta zůstávají v nemocnici. MedTeam čte jen z IRIS a potvrzený závěr zapisuje zpět.', { x: 4.55, y: 5.55, w: 8.05, h: 0.8, fontSize: 16, color: MUTED, valign: 'top' });
  s.addNotes('Aktuální síť bez AI: nemocniční systémy (NIS, PACS, laboratoř, dotazníky) → InterSystems IRIS for Health jako FHIR databáze → aplikace MedTeam → komise (notebook předsedy a plátno).');

  // ── 10 · Hardware a ukázka ──
  s = pres.addSlide({ masterName: 'PHOTO2', sectionTitle: 'Řešení' });
  s.addText('AI server a živá ukázka', { placeholder: 'title' });
  await photoFrame(s, 0.7, 1.65, 5.8, 3.85, 'Fotka AI serveru');
  await photoFrame(s, 6.83, 1.65, 5.8, 3.85, 'Fotka Raspberry Pi');
  s.addText('', { placeholder: 'photoA' });
  s.addText('', { placeholder: 'photoB' });
  text(s, 'AI server v serverovně nemocnice', { x: 0.7, y: 5.62, w: 5.8, h: 0.45, fontSize: 18, bold: true });
  text(s, 'Raspberry Pi: praktická ukázka', { x: 6.83, y: 5.62, w: 5.8, h: 0.45, fontSize: 18, bold: true });
  s.addImage({ data: await icon('shield-check', 'teal'), x: 0.7, y: 6.16, w: 0.36, h: 0.36, objectName: 'Ochrana dat ikona', altText: 'Ochrana dat' });
  text(s, 'Model běží v nemocnici, data pacienta ji neopustí.', { x: 1.16, y: 6.12, w: 6.5, h: 0.45, fontSize: 15, color: MUTED, valign: 'middle' });
  s.addNotes('AI server stojí v serverovně nemocnice, data neopouštějí nemocnici. Praktická ukázka na Raspberry Pi: zároveň kontrola, že je celý princip pochopitelný.');

  // ── 11 · Celý proces ──
  s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: 'Řešení' });
  s.addText('Celý proces od zprávy po zápis', { placeholder: 'title' });
  const STEPS = [
    ['file-text', 'Zprávy, nálezy, dotazníky', 'muted'],
    ['database', 'IRIS · FHIR databáze', 'teal'],
    ['sparkles', 'AI podklad s citacemi', 'ai'],
    ['presentation', 'Jednání: plátno, chat, AI bot', 'teal'],
    ['mic', 'AI zapisovatel', 'ai'],
    ['user-check', 'Lékař potvrdí', 'teal'],
    ['hard-drive', 'Zápis do IRIS a export', 'teal'],
  ];
  const step = 11.9 / STEPS.length;
  s.addShape(pres.shapes.LINE, { x: 0.7 + step / 2, y: 2.85, w: step * (STEPS.length - 1), h: 0, line: { color: MUTED, width: 1, transparency: 50 }, objectName: 'Osa procesu' });
  for (let i = 0; i < STEPS.length; i++) {
    const x = 0.7 + i * step + step / 2;
    await iconCircle(s, x - 0.48, 2.37, 0.96, STEPS[i][0], STEPS[i][2], STEPS[i][1]);
    text(s, String(i + 1), { x: x - 0.5, y: 3.5, w: 1.0, h: 0.4, fontSize: 16, bold: true, align: 'center', color: STEPS[i][2] === 'ai' ? AI : STEPS[i][2] === 'muted' ? MUTED : TEAL });
    text(s, STEPS[i][1], { x: x - step / 2 + 0.05, y: 3.9, w: step - 0.1, h: 1.0, fontSize: 15, align: 'center', valign: 'top' });
  }
  card(s, 0.7, 5.35, 11.9, 1.15, 'Legenda');
  s.addShape(pres.shapes.OVAL, { x: 1.0, y: 5.78, w: 0.28, h: 0.28, fill: { color: AI }, line: { type: 'none' }, objectName: 'Legenda AI' });
  text(s, 'AI navrhuje', { x: 1.4, y: 5.68, w: 2.2, h: 0.5, fontSize: 16, valign: 'middle' });
  s.addShape(pres.shapes.OVAL, { x: 3.7, y: 5.78, w: 0.28, h: 0.28, fill: { color: TEAL }, line: { type: 'none' }, objectName: 'Legenda lékař' });
  text(s, 'data a lékař', { x: 4.1, y: 5.68, w: 2.4, h: 0.5, fontSize: 16, valign: 'middle' });
  text(s, 'Oficiální je až to, co potvrdí lékař.', { x: 6.6, y: 5.68, w: 5.7, h: 0.5, fontSize: 18, bold: true, align: 'right', valign: 'middle' });
  s.addNotes('Celý tok dat: zprávy a dotazníky → databáze IRIS (FHIR) → AI připraví podklad s citacemi → jednání komise (plátno, chat, AI bot) → AI zapisovatel z diskuse → lékař potvrdí → zápis zpět do IRIS a export (PDF, FHIR).');

  // ── 12 · Náš tým ──
  pres.addSection({ title: 'Tým a závěr' });
  s = pres.addSlide({ masterName: 'TEAM4', sectionTitle: 'Tým a závěr' });
  s.addText('Náš tým', { placeholder: 'title' });
  const TEAM = [['Seb', 'infrastruktura a API'], ['Maty', 'data a InterSystems IRIS'], ['Jarda', 'AI'], ['Mira', 'UI a pitch']];
  for (let i = 0; i < TEAM.length; i++) await photoFrame(s, TEAM_X[i], 1.75, 2.6, 2.6, 'Fotka');
  TEAM.forEach(([n, role], i) => {
    s.addText('', { placeholder: `photo${i + 1}` });
    text(s, n, { x: TEAM_X[i], y: 4.6, w: 2.6, h: 0.5, fontSize: 24, bold: true, align: 'center' });
    text(s, role, { x: TEAM_X[i], y: 5.12, w: 2.6, h: 0.5, fontSize: 16, color: MUTED, align: 'center' });
  });
  s.addNotes('Představení týmu. Fotky vložíte kliknutím na ikonu obrázku v rámečku (doplní se a ořízne samy).');

  // ── 13 · Závěr ──
  s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'Tým a závěr' });
  s.addImage({ path: A('logo.png'), x: 0.75, y: 1.2, w: 6.0, h: 1.98, objectName: 'Logo MedTeam', altText: 'MedTeam' });
  s.addText('Děkujeme za pozornost', { placeholder: 'title' });
  text(s, [{ text: 'AI předkládá. ', options: { color: INK } }, { text: 'Lékař rozhoduje.', options: { color: TEAL } }], { x: 0.8, y: 5.7, w: 7.6, h: 0.6, fontSize: 26, bold: true });
  qrCard(s, 9.2, 1.45, 3.4);
  text(s, 'Vyzkoušejte si demo', { x: 9.0, y: 5.05, w: 3.8, h: 0.5, fontSize: 22, bold: true, align: 'center' });
  text(s, 'medteam.nervelabs.co.uk', { x: 9.0, y: 5.55, w: 3.8, h: 0.4, fontSize: 16, color: TEAL, align: 'center' });
  s.addNotes('Poděkování. QR kód zůstává na plátně během otázek.');

  await pres.writeFile({ fileName: path.join(__dirname, OUT) });
  await markPicturePlaceholders(path.join(__dirname, OUT));
  fs.writeFileSync(path.join(__dirname, 'theme.json'), JSON.stringify(THEME, null, 2));
  console.log('hotovo:', OUT);
}

// Zástupné prvky na fotky (idx 103+ v rozvrženích PHOTO1/PHOTO2/TEAM4) dostanou type="pic", aby PowerPoint
// nabídl vložení obrázku a fotku do rámečku ořízl. pptxgenjs 4 typ „pic“ u placeholderu nezapisuje.
async function markPicturePlaceholders(file) {
  const JSZip = require(require.resolve('jszip', { paths: [require.resolve('pptxgenjs')] }));
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const isPhotoLayout = (xml) => /<p:cSld name="(PHOTO1|PHOTO2|TEAM4)"/.test(xml);
  const layouts = new Set();
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/slideLayouts\/slideLayout\d+\.xml$/.test(n))) {
    let xml = await zip.file(name).async('string');
    if (!isPhotoLayout(xml)) continue;
    layouts.add(path.basename(name));
    xml = xml.replace(/<p:ph(\s+)idx="(10[3-9])"/g, '<p:ph$1type="pic" idx="$2"');
    zip.file(name, xml);
  }
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n))) {
    const rels = await zip.file(name.replace('slides/', 'slides/_rels/') + '.rels').async('string');
    const layout = (rels.match(/slideLayouts\/(slideLayout\d+\.xml)/) || [])[1];
    if (!layouts.has(layout)) continue;
    const xml = (await zip.file(name).async('string')).replace(/<p:ph(\s+)idx="(10[3-9])"/g, '<p:ph$1type="pic" idx="$2"');
    zip.file(name, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}

build().catch((e) => { console.error(e); process.exit(1); });
