"""Doplní do slidů prolínací přechod a animace (vše se spouští samo po zobrazení slidu)."""
import re, sys, zipfile, os

SRC, OUT = sys.argv[1], sys.argv[2]

# (zpoždění ms, efekt, [skupiny]) ; skupina "c1" = tvar "c1" i všechny "c1_*"
ANIM = {
    1: [(200, 'pop', ['logo']), (700, 'up', ['sub']), (1100, 'pop', ['tag']),
        (1500, 'pop', ['l_rak']), (1650, 'pop', ['l_ass']), (1800, 'pop', ['l_int'])],
    2: [(200, 'pop', ['big']), (900, 'up', ['line']), (1400, 'pop', ['c1']), (1650, 'pop', ['c2'])],
    3: [(200, 'up', ['h2']), (800, 'pop', ['c1']), (1200, 'pop', ['c2'])],
    4: [(200, 'pop', ['app']), (600, 'up', ['i0']), (900, 'up', ['i1']), (1200, 'up', ['i2']), (1500, 'up', ['i3'])],
    5: [(300, 'pop', ['r0']), (700, 'pop', ['r1']), (1100, 'pop', ['r2'])],
    6: [(200, 'pop', ['big']), (900, 'up', ['line']), (1500, 'pop', ['p1']), (1750, 'fade', ['x1']),
        (1900, 'pop', ['p2']), (2150, 'fade', ['x2']), (2300, 'pop', ['p3'])],
    8: [(200, 'up', ['h2']), (700, 'fade', ['p']), (1100, 'pop', ['tag']), (1500, 'pop', ['logos', 'l_mdt', 'l_rak', 'l_ass', 'l_int'])],
}
# Slide 7: počítadlo + ikonky, které naskočí a poskočí
s7 = [(300, 'pop', ['t0']), (300, 'pop', ['num0']), (300, 'fade', ['lab0']), (900, 'hop', ['t0_icon'])]
for i in range(1, 5):
    t = 300 + i * 1400
    s7 += [(t, 'pop', [f't{i}']), (t, 'out', [f'num{i-1}']), (t, 'pop', [f'num{i}']), (t + 600, 'hop', [f't{i}_icon'])]
s7 += [(300 + 4 * 1400, 'out', ['lab0']), (300 + 4 * 1400, 'fade', ['lab1', 'lab2'])]
ANIM[7] = s7

class Ids:
    def __init__(self): self.n = 2
    def __call__(self): self.n += 1; return self.n

def tgt(spid): return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
def setvis(nid, spid, val):
    return (f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'{tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:to><p:strVal val="{val}"/></p:to></p:set>')
def anim(nid, spid, attr, tavs, dur):
    tl = ''.join(f'<p:tav tm="{tm}"><p:val><p:strVal val="{v}"/></p:val></p:tav>' for tm, v in tavs)
    return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{nid()}" dur="{dur}" fill="hold"/>{tgt(spid)}'
            f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>{tl}</p:tavLst></p:anim>')
def fade(nid, spid, dur):
    return f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{nid()}" dur="{dur}"/>{tgt(spid)}</p:cBhvr></p:animEffect>'

def effect(nid, kind, spid, delay, grp):
    if kind == 'pop':
        preset, cls, sub = 53, 'entr', 16
        body = (setvis(nid, spid, 'visible')
                + anim(nid, spid, 'ppt_w', [(0, '0'), (70000, '#ppt_w*1.12'), (100000, '#ppt_w')], 600)
                + anim(nid, spid, 'ppt_h', [(0, '0'), (70000, '#ppt_h*1.12'), (100000, '#ppt_h')], 600)
                + fade(nid, spid, 300))
    elif kind == 'fade':
        preset, cls, sub = 10, 'entr', 0
        body = setvis(nid, spid, 'visible') + fade(nid, spid, 500)
    elif kind == 'up':
        preset, cls, sub = 42, 'entr', 0
        body = (setvis(nid, spid, 'visible') + fade(nid, spid, 600)
                + anim(nid, spid, 'ppt_y', [(0, '#ppt_y+0.04'), (100000, '#ppt_y')], 600))
    elif kind == 'out':
        preset, cls, sub = 1, 'exit', 0
        body = setvis(nid, spid, 'hidden')
    elif kind == 'hop':
        preset, cls, sub = 0, 'path', 0
        body = (f'<p:animMotion origin="layout" path="M 0 0 L 0 -0.03 L 0 0 L 0 -0.015 L 0 0 E" pathEditMode="relative" ptsTypes="">'
                f'<p:cBhvr><p:cTn id="{nid()}" dur="900" fill="hold"/>{tgt(spid)}'
                f'<p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr></p:animMotion>')
    cid = nid()
    return (f'<p:par><p:cTn id="{cid}" presetID="{preset}" presetClass="{cls}" presetSubtype="{sub}" fill="hold" grpId="{grp}" nodeType="withEffect">'
            f'<p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>{body}</p:childTnLst></p:cTn></p:par>')

def build_timing(xml, steps):
    shapes = re.findall(r'<p:(sp|pic)>\s*<p:nv(?:Sp|Pic)Pr>\s*<p:cNvPr id="(\d+)" name="([^"]*)"', xml)
    kinds = {name: (kind, int(i)) for kind, i, name in shapes}
    def match(g): return [(n, kinds[n]) for n in kinds if n == g or n.startswith(g + '_')]
    nid = Ids(); effects = []; grp_count = {}; bld = []
    for delay, kind, groups in steps:
        for g in groups:
            hits = match(g)
            if not hits: raise SystemExit(f'Skupina {g} nenalezena')
            for name, (k, spid) in hits:
                if kind == 'hop' or (kind == 'out' and False):
                    pass
                grp = grp_count.get(spid, 0); grp_count[spid] = grp + 1
                effects.append(effect(nid, kind, spid, delay, grp))
                if k == 'sp': bld.append(f'<p:bldP spid="{spid}" grpId="{grp}" animBg="1"/>')
    inner = ''.join(effects)
    timing = ('<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
              '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
              f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
              f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{inner}</p:childTnLst></p:cTn></p:par>'
              '</p:childTnLst></p:cTn></p:par>'
              '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
              '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
              '</p:childTnLst></p:cTn></p:par></p:tnLst>'
              + (f'<p:bldLst>{"".join(bld)}</p:bldLst>' if bld else '') + '</p:timing>')
    return timing

zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    m = re.match(r'ppt/slides/slide(\d+)\.xml$', item.filename)
    if m:
        n = int(m.group(1)); xml = data.decode('utf-8')
        add = '<p:transition spd="med"><p:fade/></p:transition>'
        if n in ANIM: add += build_timing(xml, ANIM[n])
        xml = xml.replace('</p:clrMapOvr></p:sld>', '</p:clrMapOvr>' + add + '</p:sld>')
        assert add in xml, f'slide {n}: vložení selhalo'
        data = xml.encode('utf-8')
    zout.writestr(item, data)
zout.close()
print('hotovo:', OUT)
