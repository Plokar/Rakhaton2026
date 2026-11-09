// Postaví MDTcore_vlada.pptx (13,333 × 7,5 in). Souřadnice v px plátna 1920×1080, 1 in = 144 px, pt = px/2.
const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.title = 'MDTcore: nový standard onkologických komisí';
pres.author = 'Tým MDTcore, Rakathon 2026';
pres.theme = { headFontFace: 'Montserrat ExtraBold', bodyFontFace: 'Inter' };

const X = (px) => px / 144;
const PT = (px) => px / 2;
const H = 'Montserrat ExtraBold', M = 'Montserrat', I = 'Inter';
const C = { bg: 'E9EEF3', sheet: 'FCFDFE', ink: '0E2A47', body: '2B3D52', soft: '4A5B6E', muted: '6B7A8C',
  blue: '1C7FC4', blueDark: '1C6FAD', tint: 'F1F6FB', pill: 'E3F1FB', light: 'D9EAF7' };
const IMG = (f) => 'img/' + f;

function box(s, name, x, y, w, h) { return { objectName: name, x: X(x), y: X(y), w: X(w), h: X(h) }; }
function sheet(s, blue) {
  s.background = { color: C.bg };
  if (blue) s.addImage({ path: IMG('sheet_blue.png'), ...box(s, 'sheet', 48, 48, 1824, 984) });
  else s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...box(s, 'sheet', 48, 48, 1824, 984), rectRadius: X(40),
    fill: { color: C.sheet }, line: { color: C.sheet }, shadow: { type: 'outer', blur: 18, offset: 6, angle: 90, color: '0E2A47', opacity: 0.14 } });
}
function text(s, name, str, x, y, w, h, o = {}) {
  s.addText(str, { ...box(s, name, x, y, w, h), isTextBox: true, margin: 0, valign: 'top', fontFace: I, fontSize: 14, color: C.body, ...o });
}
function pill(s, name, str, x, y, w, onBlue) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...box(s, name + '_bg', x, y, w, 50), rectRadius: X(25),
    fill: onBlue ? { color: 'FFFFFF', transparency: 84 } : { color: C.pill }, line: { type: 'none' } });
  text(s, name, str, x, y, w, 50, { fontFace: M, bold: true, fontSize: 12, charSpacing: 1, color: onBlue ? 'FFFFFF' : C.blueDark, align: 'center', valign: 'middle' });
}
function footer(s, src, page, x = 128, w = 1664, onBlue = false) {
  text(s, 'foot_src', src, x, 940, w - 160, 36, { fontSize: 12, color: onBlue ? C.light : C.muted, valign: 'middle' });
  text(s, 'foot_page', page, x + w - 150, 940, 150, 36, { fontFace: M, bold: true, fontSize: 12, color: onBlue ? 'FFFFFF' : C.blueDark, align: 'right', valign: 'middle' });
}
function card(s, name, x, y, w, h, color = C.tint, r = 24, transp) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...box(s, name, x, y, w, h), rectRadius: X(r),
    fill: transp ? { color: 'FFFFFF', transparency: transp } : { color }, line: { type: 'none' } });
}

// 1 · Úvod
{
  const s = pres.addSlide(); sheet(s);
  s.addImage({ path: IMG('cover.png'), ...box(s, 'photo', 1152, 96, 672, 888), altText: 'Lékaři u kulatého stolu na onkologické komisi' });
  s.addImage({ path: IMG('mdtcore_logo.png'), ...box(s, 'logo', 128, 150, 880, 279), altText: 'Logo MDTcore' });
  text(s, 'sub', 'Méně papírů pro lékaře. Dřívější rozhodnutí o léčbě pro pacienty.', 128, 520, 880, 120, { fontSize: 19, color: C.body, lineSpacingMultiple: 1.3 });
  pill(s, 'tag', 'DESIGNED BY DOCTOR, MADE BY STUDENTS', 128, 680, 780);
  s.addImage({ path: IMG('rakathon_logo.png'), ...box(s, 'l_rak', 128, 820, 72, 120), altText: 'Logo Rakathon' });
  s.addImage({ path: IMG('asseco_logo.png'), ...box(s, 'l_ass', 248, 868, 400, 23.4), altText: 'Logo Asseco Central Europe' });
  s.addImage({ path: IMG('intersystems.png'), ...box(s, 'l_int', 696, 846, 260, 69.3), altText: 'Logo InterSystems' });
  s.addNotes('Vážený pane premiére, vážený pane ministře. Jsme tým MDTcore z hackathonu Rakathon 2026. Ukážeme vám, jak může každý onkologický pacient v Česku dostat rozhodnutí o léčbě dříve.');
}
// 2 · 65 242
{
  const s = pres.addSlide(); sheet(s);
  pill(s, 'pill', 'ROZSAH PROBLÉMU', 128, 128, 380);
  text(s, 'big', '65 242', 128, 230, 1600, 320, { fontFace: H, fontSize: 150, color: C.blue, valign: 'middle' });
  text(s, 'line', 'lidí v Česku slyšelo v roce 2023 diagnózu rakovina.', 128, 560, 1600, 70, { fontFace: M, bold: true, fontSize: 26, color: C.ink });
  card(s, 'c1', 128, 690, 420, 190);
  text(s, 'c1_a', '≈ 180', 164, 718, 360, 70, { fontFace: H, fontSize: 26, color: C.ink });
  text(s, 'c1_b', 'nových pacientů denně', 164, 800, 360, 40, { fontSize: 14, color: C.soft });
  card(s, 'c2', 572, 690, 1220, 190);
  text(s, 'c2_a', 'O léčbě každého rozhoduje onkologická komise (MDT)', 608, 718, 1150, 60, { fontFace: M, bold: true, fontSize: 19, color: C.ink });
  text(s, 'c2_b', '5 specialistů u jednoho stolu, 3 až 5 minut na pacienta', 608, 800, 1150, 40, { fontSize: 14, color: C.soft });
  footer(s, 'Zdroj: ČSÚ, Zdravotní stav obyvatelstva (data ÚZIS), nové zhoubné novotvary 2023 bez C44', '02 / 08');
  s.addNotes('Každý rok slyší v Česku diagnózu rakovina přes 65 tisíc lidí, zhruba 180 každý den. O léčbě každého z nich rozhoduje onkologická komise: pět specialistů, pár minut na pacienta.');
}
// 3 · Háček (modrý)
{
  const s = pres.addSlide(); sheet(s, true);
  s.addImage({ path: IMG('papiry.png'), ...box(s, 'photo', 96, 96, 800, 888), altText: 'Lékař nese chodbou nemocnice náruč papírové dokumentace' });
  pill(s, 'pill', 'HÁČEK', 976, 150, 180, true);
  text(s, 'h2', 'Před komisí musí onkolog projít hory papírů', 976, 230, 816, 220, { fontFace: H, fontSize: 32, color: 'FFFFFF', lineSpacingMultiple: 1.05 });
  card(s, 'c1', 976, 520, 816, 130, null, 24, 88);
  text(s, 'c1_a', '12', 1008, 520, 210, 130, { fontFace: H, fontSize: 30, color: 'FFFFFF', valign: 'middle' });
  text(s, 'c1_b', 'normostran textu na jednoho pacienta', 1246, 520, 520, 130, { fontSize: 15, color: C.light, valign: 'middle' });
  card(s, 'c2', 976, 670, 816, 130, null, 24, 88);
  text(s, 'c2_a', '4,1 h', 1008, 670, 210, 130, { fontFace: H, fontSize: 30, color: 'FFFFFF', valign: 'middle' });
  text(s, 'c2_b', 'stráví každý lékař jednou komisí, většinu přípravou', 1246, 670, 520, 130, { fontSize: 15, color: C.light, valign: 'middle' });
  footer(s, 'Pacient P04 (Rakathon) · Alexandersson 2018', '03 / 08', 976, 816, true);
  s.addNotes('Háček: onkolog musí předtím projít hory papírů, dvanáct normostran na pacienta. Hodiny přípravy místo péče.');
}
// 4 · Řešení
{
  const s = pres.addSlide(); sheet(s);
  card(s, 'panel', 1176, 96, 648, 888, C.pill, 32);
  s.addImage({ path: IMG('app.png'), ...box(s, 'app', 1240, 150, 520, 780), rotate: 2, altText: 'Obrazovka MDTcore: přehled pacienta P04',
    shadow: { type: 'outer', blur: 24, offset: 10, angle: 90, color: '0E2A47', opacity: 0.3 } });
  pill(s, 'pill', 'ŘEŠENÍ: MDTCORE', 128, 180, 380);
  text(s, 'h2', 'Podklad pro komisi do minuty, ne za hodiny', 128, 260, 960, 180, { fontFace: H, fontSize: 34, color: C.ink, lineSpacingMultiple: 1.05 });
  const items = ['Vše důležité o pacientovi na jedné obrazovce', 'Každý údaj s odkazem na původní zprávu', 'Upozorní na rozpory a chybějící vyšetření', 'Rozhoduje vždy lékař.'];
  items.forEach((t, i) => {
    const y = 490 + i * 90;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...box(s, `i${i}_n`, 128, y, 68, 48), rectRadius: X(24), fill: { color: C.blue }, line: { type: 'none' } });
    text(s, `i${i}_nt`, String(i + 1).padStart(2, '0'), 128, y, 68, 48, { fontFace: H, fontSize: 13, color: 'FFFFFF', align: 'center', valign: 'middle' });
    text(s, `i${i}_t`, t, 224, y - 6, 860, 60, { fontSize: 16, color: i === 3 ? C.ink : C.body, bold: i === 3, valign: 'middle' });
  });
  footer(s, 'Snímek aplikace, syntetický pacient P04', '04 / 08', 128, 960);
  s.addNotes('MDTcore přečte zprávy za lékaře a do minuty připraví přehled pro komisi. Každý údaj má odkaz na zdroj a systém sám upozorní na rozpory a chybějící vyšetření. Rozhoduje vždy lékař.');
}
// 5 · Nový standard
{
  const s = pres.addSlide(); sheet(s);
  pill(s, 'pill', 'NOVÝ STANDARD EFEKTIVITY MDT', 128, 128, 620);
  text(s, 'h2', 'Lékaři se vrátí k pacientům, stát ušetří', 128, 210, 1600, 100, { fontFace: H, fontSize: 34, color: C.ink });
  [['50 000 h', 'ročně vrácených lékařům pro pacienty'], ['≈ 30 lékařů', 'na plný úvazek navíc, bez jediného náboru'], ['3,7×', 'dražší je léčba pokročilého nádoru než časného']].forEach(([a, b], i) => {
    const y = 390 + i * 160;
    card(s, `r${i}`, 128, y, 1664, 140);
    text(s, `r${i}_a`, a, 168, y, 560, 140, { fontFace: H, fontSize: 40, color: C.blue, valign: 'middle' });
    text(s, `r${i}_b`, b, 760, y, 1000, 140, { fontSize: 16, color: C.body, valign: 'middle' });
  });
  footer(s, 'Modelový odhad (65 242 pacientů, příprava o polovinu kratší) · 3,7×: tlusté střevo, CRUK 2014', '05 / 08');
  s.addNotes('Lékařům tím vrátíme padesát tisíc hodin ročně, jako třicet onkologů navíc. A dřívější léčba je levnější: pokročilý nádor stojí až 3,7krát víc.');
}
// 6 · Životy (modrý)
{
  const s = pres.addSlide(); sheet(s, true);
  pill(s, 'pill', 'CO TO ZNAMENÁ PRO PACIENTY', 128, 128, 620, true);
  text(s, 'big', '200–500', 128, 230, 1600, 300, { fontFace: H, fontSize: 130, color: 'FFFFFF', valign: 'middle' });
  text(s, 'line', 'zachráněných životů ročně, když komise rozhodne o jediný týden dříve.', 128, 540, 1500, 150, { fontFace: M, bold: true, fontSize: 28, color: 'FFFFFF' });
  const parts = [['p1', '1 týden = riziko úmrtí nižší o 1,5–1,9 %', 600], ['x1', '×', 50], ['p2', '≈ 27 000 úmrtí na rakovinu ročně', 500], ['x2', '=', 50], ['p3', '200 až 500 lidí', 300]];
  let x = 128;
  parts.forEach(([n, t, w]) => {
    if (n[0] === 'p') {
      const last = n === 'p3';
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...box(s, n + '_bg', x, 760, w, 72), rectRadius: X(36), fill: last ? { color: 'FCFDFE' } : { color: 'FFFFFF', transparency: 86 }, line: { type: 'none' } });
      text(s, n, t, x, 760, w, 72, { fontSize: 14, bold: last, color: last ? C.ink : 'FFFFFF', align: 'center', valign: 'middle' });
    } else text(s, n, t, x, 760, w, 72, { fontFace: H, fontSize: 18, color: C.light, align: 'center', valign: 'middle' });
    x += w + 20;
  });
  footer(s, 'Modelový odhad: HR 1,06–1,08 za 4 týdny (Hanna a kol., BMJ 2020); úmrtí ≈ ¼ ze 112 800 zemřelých v ČR 2023 (ČSÚ)', '06 / 08', 128, 1664, true);
  s.addNotes('Hlavně ale: každý měsíc čekání zvyšuje riziko úmrtí o šest až osm procent. Když komise rozhodne jen o týden dřív, zachráníme podle našeho modelu dvě stě až pět set životů ročně.');
}
// 7 · Onkologií to nekončí (animované počítadlo)
{
  const s = pres.addSlide(); sheet(s);
  pill(s, 'pill', 'ONKOLOGIÍ TO NEKONČÍ', 128, 128, 460);
  text(s, 'h2', 'Pomůžeme všude, kde se lékaři společně rozhodují o pacientovi', 128, 200, 1600, 150, { fontFace: H, fontSize: 30, color: C.ink, lineSpacingMultiple: 1.05 });
  card(s, 'left', 128, 380, 700, 540);
  ['65 242', '88 363', '95 935', '96 887', '1 296 397'].forEach((v, i) =>
    text(s, `num${i}`, v, 172, 470, 640, 140, { fontFace: H, fontSize: 60, color: C.blue, valign: 'middle' }));
  text(s, 'lab0', 'pacientů ročně, o jejichž léčbě rozhoduje tým lékařů', 172, 640, 620, 100, { fontSize: 16, color: C.body });
  text(s, 'lab1', 'pacientů ročně projde nemocnicemi akutní péče', 172, 640, 620, 100, { fontSize: 16, color: C.body });
  text(s, 'lab2', 'z toho 96 887 s rozhodnutím týmu lékařů', 172, 760, 620, 50, { fontSize: 13, color: C.soft });
  const tiles = [['ic_onko', 'Onkologie', '65 242'], ['ic_neuro', 'Mozkové příhody', '23 121'], ['ic_srdce', 'Operace srdce', '7 572'], ['ic_transpl', 'Transplantace', '952'], ['ic_nemoc', 'Celá nemocnice', '1,3 mil.']];
  tiles.forEach(([ic, name, val], i) => {
    const y = 380 + i * 111, big = i === 4;
    if (big) s.addImage({ path: IMG('tile_blue.png'), ...box(s, `t${i}`, 868, y, 924, 96) });
    else card(s, `t${i}`, 868, y, 924, 96, C.tint, 22);
    s.addImage({ path: IMG(ic + '.png'), ...box(s, `t${i}_icon`, 884, y + 12, 72, 72) });
    text(s, `t${i}_m`, name, 984, y, 520, 96, { fontFace: M, bold: true, fontSize: 15, color: big ? 'FFFFFF' : C.ink, valign: 'middle' });
    text(s, `t${i}_k`, val, 1540, y, 220, 96, { fontFace: M, bold: true, fontSize: 14, color: big ? C.light : C.blueDark, align: 'right', valign: 'middle' });
  });
  footer(s, 'ČSÚ 2023 (onkologie), ÚZIS 2021 (CMP, kardiochirurgie), KST (transplantace), ČSÚ 2024 (hospitalizovaní v akutní péči)', '07 / 08');
  s.addNotes('A onkologií to nekončí. Stejně se tým lékařů rozhoduje u mozkových příhod, operací srdce i transplantací. To je skoro sto tisíc pacientů ročně. A když přidáme celou nemocnici, je to přes 1,3 milionu lidí každý rok.');
}
// 8 · Pilot
{
  const s = pres.addSlide(); sheet(s);
  s.addImage({ path: IMG('pilot.png'), ...box(s, 'photo', 1200, 96, 624, 888), altText: 'Stůl s hromadou papírů vedle stolu s jediným tabletem' });
  pill(s, 'pill', 'DALŠÍ KROK', 128, 128, 260);
  text(s, 'h2', 'Pojďme to dokázat na jedné komisi', 128, 220, 960, 200, { fontFace: H, fontSize: 42, color: C.ink, lineSpacingMultiple: 1.0 });
  text(s, 'p', 'Pilot změří minuty přípravy, dny do rozhodnutí a počet pacientů na komisi. Pak nový standard pro celé Česko.', 128, 450, 920, 150, { fontSize: 17, color: C.soft, lineSpacingMultiple: 1.3 });
  text(s, 'tag', 'Designed by Doctor\nMade by Students', 128, 620, 920, 120, { fontFace: H, fontSize: 20, color: C.blue, lineSpacingMultiple: 1.2 });
  card(s, 'logos', 128, 800, 1064, 140);
  s.addImage({ path: IMG('mdtcore_logo.png'), ...box(s, 'l_mdt', 168, 832, 240, 76) });
  s.addImage({ path: IMG('rakathon_logo.png'), ...box(s, 'l_rak', 456, 820, 60, 100) });
  s.addImage({ path: IMG('asseco_logo.png'), ...box(s, 'l_ass', 564, 861, 320, 18.7) });
  s.addImage({ path: IMG('intersystems.png'), ...box(s, 'l_int', 932, 841, 220, 58.7) });
  s.addNotes('Žádáme o pilot na jedné komisi, který to změří. Pak nový standard pro celé Česko. Designed by Doctor, Made by Students. Děkujeme.');
}

pres.writeFile({ fileName: 'MDTcore_vlada_raw.pptx' }).then(() => console.log('ok'));
