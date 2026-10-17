import type { EvidenceId, IntakeField, IntakePrefill, IntakeWarning, ObservationSeries, Severity } from '@/types/mdt';

/**
 * Klíčové údaje pro úzký panel projektoru (T-512): šablona podle diagnózy z `IntakePrefill.fields`
 * (POZADAVKY §4, stejná jako při zařazení pacienta), laboratoř s referenčním rozmezím a varování pravidel.
 *
 * Barvu nikdy neodhadujeme: zelená = hodnota v referenčním rozmezí z FHIR, oranžová = mimo rozmezí
 * (H/L) nebo varování pravidla, červená = varování se závažností `high`. Údaj bez rozmezí
 * (biomarker, text zprávy) je „zaznamenáno“ bez hodnocení normality.
 */
export type FactStatus = 'normal' | 'abnormal' | 'critical' | 'recorded' | 'missing' | 'pending' | 'skipped';
export type FactGroup = 'diagnosis' | 'lab' | 'general' | 'alert';

export interface KeyFact {
  id: string;
  /** Lékařská zkratka (Hb, PNP, FLR…). */
  abbr: string;
  /** Plný název pro čtečky a tooltip. */
  label: string;
  value: string | null;
  date?: string;
  status: FactStatus;
  /** Proč má údaj danou barvu (název varování, referenční rozmezí). */
  reason?: string;
  citations: EvidenceId[];
  group: FactGroup;
}

export interface KeyFacts {
  facts: KeyFact[];
  /** Varování k ECOG (rozdíl lékař × pacient): panel je ukazuje v hlavičce u PS. */
  ecogWarnings: IntakeWarning[];
}

/** Pole, která panel ukazuje jinde: otázku v dolním pásu, ECOG v hlavičce. */
const ELSEWHERE = new Set(['mdt.question', 'ecog.physician', 'ecog.patient']);
/** Společná pole OBC-1.1 (`intake._common_fields`); ostatní jsou podle diagnózy (POZADAVKY §4.2–4.4). */
const GENERAL = new Set([
  'dx.histology', 'staging.tnm', 'staging.imaging', 'comorbidities', 'treatment.history',
  'preferences', 'allergies', 'weight', 'geri.g8',
]);

const FIELD_ABBR: Record<string, string> = {
  'dx.histology': 'Histologie',
  'staging.tnm': 'TNM',
  'staging.imaging': 'Zobrazení ≤ 6 t.',
  comorbidities: 'Komorbidity',
  'treatment.history': 'Dosavadní léčba',
  preferences: 'Přání pacienta',
  allergies: 'AA',
  weight: 'Hmotnost',
  'geri.g8': 'G8',
  'staging.pet': 'PET/CT',
  'staging.brain_mr': 'MR mozku',
  'staging.ebus': 'EBUS',
  'bm.egfr': 'EGFR',
  'bm.alk': 'ALK',
  'bm.pdl1': 'PD-L1',
  'spiro.fev1': 'FEV1',
  'spiro.dlco': 'DLCO',
  'spiro.ppo_fev1': 'ppoFEV1',
  'spiro.ppo_dlco': 'ppoDLCO',
  'spiro.vo2max': 'VO2max',
  smoking: 'Kouření',
  'lab.na': 'Na',
  'bm.er': 'ER',
  'bm.pr': 'PR',
  'bm.her2': 'HER2',
  'bm.ki67': 'Ki-67',
  'bm.esr1': 'ESR1',
  'bm.pik3ca': 'PIK3CA',
  'bm.gbrca': 'gBRCA',
  lvef: 'LVEF',
  'bm.ras': 'RAS',
  'bm.braf': 'BRAF',
  'bm.mmr': 'MMR/MSI',
  'staging.chest_ct': 'CT hrudníku',
  'staging.liver_mr': 'MR jater',
  'liver.flr': 'FLR',
  'treatment.bevacizumab': 'BEV posl.',
  'tox.neuropathy': 'PNP',
};

const LAB_ABBR: [RegExp, string][] = [
  [/hemoglobin/i, 'Hb'],
  [/leukocyt/i, 'Leu'],
  [/neutrofil/i, 'Neu'],
  [/trombocyt/i, 'Tr'],
  [/kreatinin/i, 'Kreat'],
  [/bilirubin/i, 'Bili'],
  [/albumin/i, 'Alb'],
  [/sod[ií]k|natrium/i, 'Na'],
  [/drasl[ií]k|kalium/i, 'K'],
  [/v[aá]pn[ií]k|kalcium/i, 'Ca'],
  [/glyk[eé]mie|gluk[oó]za/i, 'Glu'],
];

/** Klinické pořadí laboratoře: krevní obraz, ledviny a ionty, játra, pak ostatní (markery) v pořadí z API. */
const LAB_ORDER = ['Hb', 'Leu', 'Neu', 'Tr', 'Kreat', 'Na', 'K', 'Ca', 'Bili', 'ALT', 'AST', 'ALP', 'Alb', 'Glu'];

const WARNING_KIND: Record<IntakeWarning['kind'], string> = {
  missing: 'Chybí',
  out_of_range: 'Mimo normu',
  conflict: 'Rozpor',
  ai_uncertain: 'Nejistota AI',
};

const SEVERITY_RANK: Record<Severity, number> = { high: 0, moderate: 1, low: 2 };

const number = (value: number) => value.toLocaleString('cs-CZ', { maximumFractionDigits: 2 });

export const labAbbr = (label: string) => LAB_ABBR.find(([pattern]) => pattern.test(label))?.[1] ?? label;

const unit = (value: string) => value.replace(/10\^9/g, '10⁹').replace(/10\^12/g, '10¹²');

/**
 * Hodnota pro úzký panel: bez opakovaného nadpisu ze zprávy („Histologie a grade: …“), odrážky a řádky
 * na jeden řádek, ISO datum česky. Plné znění ukáže zdroj citace.
 */
export function compactValue(value: string): string {
  return unit(value)
    .replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, (_, y: string, m: string, d: string) => `${Number(d)}. ${Number(m)}. ${y}`)
    .replace(/^[^:\n\d]{3,40}:\s*/, '')
    .replace(/\s*\n+\s*(?:[-•]\s*)?/g, '; ')
    .replace(/^[-•]\s*/, '')
    .trim();
}

function fieldStatus(field: IntakeField): FactStatus {
  if (field.status === 'present') return 'recorded';
  return field.status;
}

/** Poslední bod laboratorní řady s referenčním rozmezím → řádek „v normě“ / „mimo normu“. */
function labFact(series: ObservationSeries): KeyFact | null {
  const points = series.points.toSorted((a, b) => a.date.localeCompare(b.date));
  const last = points.at(-1);
  const ref = points.findLast((p) => p.ref_low !== undefined || p.ref_high !== undefined);
  if (!last || !ref) return null;
  const low = last.ref_low ?? ref.ref_low;
  const high = last.ref_high ?? ref.ref_high;
  const outside = last.interpretation !== undefined
    || (low !== undefined && last.value < low)
    || (high !== undefined && last.value > high);
  const range = low !== undefined && high !== undefined ? `${number(low)}–${number(high)}`
    : low !== undefined ? `≥ ${number(low)}` : `≤ ${number(high as number)}`;
  const shownUnit = series.unit ? ` ${unit(series.unit)}` : '';
  return {
    id: `lab:${series.code}`,
    abbr: labAbbr(series.label),
    label: series.label,
    value: `${number(last.value)}${shownUnit}`,
    date: last.date,
    status: outside ? 'abnormal' : 'normal',
    reason: `${outside ? 'mimo ref.' : 'ref.'} ${range}${shownUnit}`,
    citations: [last.citation],
    group: 'lab',
  };
}

/** Kam varování patří: pole s jednoznačnou citací, laboratorní řada, ECOG v hlavičce, nebo samostatný řádek. */
function warningTarget(
  warning: IntakeWarning,
  fieldById: Map<string, IntakeField>,
  fieldByCitation: Map<EvidenceId, IntakeField>,
  labByCitation: Map<EvidenceId, string>,
): { field?: IntakeField; labId?: string } {
  if (warning.id.startsWith('missing:')) {
    const field = fieldById.get(warning.id.slice('missing:'.length));
    if (field) return { field };
  }
  // ID pravidla nese citaci za dvojtečkou („RF-TOX:P03-neuro01“), pak teprve citace v pořadí od pravidla.
  const ownCitation = warning.id.includes(':') ? warning.id.slice(warning.id.indexOf(':') + 1) : null;
  for (const citation of [ownCitation, ...warning.citations]) {
    if (!citation) continue;
    const labId = labByCitation.get(citation);
    if (labId) return { labId };
    const field = fieldByCitation.get(citation);
    if (field) return { field };
  }
  return {};
}

export function buildKeyFacts(intake: IntakePrefill | null | undefined, series: ObservationSeries[] | null | undefined): KeyFacts {
  const fields = intake?.fields ?? [];
  const fieldById = new Map(fields.map((f) => [f.id, f]));

  // Citace sdílená víc poli (např. celý dotazník PROMs u alergií i ECOG pacienta) nic jednoznačně neurčuje.
  const citationUse = new Map<EvidenceId, number>();
  for (const f of fields) if (f.citation) citationUse.set(f.citation, (citationUse.get(f.citation) ?? 0) + 1);
  const fieldByCitation = new Map<EvidenceId, IntakeField>();
  for (const f of fields) if (f.citation && citationUse.get(f.citation) === 1) fieldByCitation.set(f.citation, f);

  // Řádek, kterému patří každý bod laboratorní řady (i starší body, které cituje pravidlo trendu).
  const labs = new Map<string, KeyFact>();
  const rowByLabCitation = new Map<EvidenceId, string>();
  for (const s of series ?? []) {
    if (s.code.startsWith('proms:')) continue;
    const fact = labFact(s);
    if (!fact) continue;
    labs.set(fact.id, fact);
    for (const p of s.points) rowByLabCitation.set(p.citation, fact.id);
  }

  const rows = new Map<string, KeyFact>();
  for (const f of fields) {
    if (ELSEWHERE.has(f.id)) continue;
    const labId = f.citation ? rowByLabCitation.get(f.citation) : undefined;
    const lab = labId ? labs.get(labId) : undefined;
    if (lab && labId) {     // pole šablony je hodnota z laboratoře (Na u plic): jeden řádek, normalita z rozmezí
      labs.delete(labId);
      for (const [citation, rowId] of rowByLabCitation) if (rowId === labId) rowByLabCitation.set(citation, f.id);
    }
    rows.set(f.id, {
      id: f.id,
      abbr: FIELD_ABBR[f.id] ?? f.label,
      label: f.label,
      value: lab?.value ?? (f.value ? compactValue(f.value)
        : f.status === 'skipped' ? 'přeskočeno lékařem' : f.status === 'pending' ? 'čeká se na výsledek' : null),
      date: lab?.date,
      status: lab && f.status === 'present' ? lab.status : fieldStatus(f),
      reason: lab?.reason,
      citations: [f.citation, f.required_by].filter((c): c is EvidenceId => Boolean(c)),
      group: GENERAL.has(f.id) ? 'general' : 'diagnosis',
    });
  }

  const ecogWarnings: IntakeWarning[] = [];
  const alerts: KeyFact[] = [];
  const attach = (row: KeyFact, warning: IntakeWarning) => {
    // Chybějící údaj zůstává „chybí“ (ne „mimo normu“); varování jen doplní citace (pravidlo, zdroj).
    if (warning.kind === 'missing' && (row.status === 'missing' || row.status === 'pending' || row.status === 'skipped')) {
      row.citations = [...new Set([...row.citations, ...warning.citations])];
      return;
    }
    if (warning.severity === 'high') row.status = 'critical';
    else if (row.status !== 'critical') row.status = 'abnormal';
    // Obecné „mimo rozmezí“ (H/L) jen opakuje hodnotu, kterou řádek už ukazuje; přidáme jen rozmezí.
    const repeatsValue = warning.id.startsWith('out_of_range:') && Boolean(row.reason);
    row.reason = repeatsValue ? row.reason : row.reason ? `${warning.title}; ${row.reason}` : warning.title;
    row.citations = [...new Set([...row.citations, ...warning.citations])];
  };

  for (const warning of (intake?.warnings ?? []).toSorted((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])) {
    const { field, labId } = warningTarget(warning, fieldById, fieldByCitation, rowByLabCitation);
    if (field && ELSEWHERE.has(field.id)) {
      ecogWarnings.push(warning);
      continue;
    }
    const row = field ? rows.get(field.id) : labId ? rows.get(labId) ?? labs.get(labId) : undefined;
    if (row) {
      attach(row, warning);
      continue;
    }
    alerts.push({
      id: `alert:${warning.id}`,
      abbr: WARNING_KIND[warning.kind],
      label: warning.title,
      value: warning.title,
      status: warning.severity === 'high' ? 'critical' : 'abnormal',
      reason: warning.detail,
      citations: warning.citations,
      group: 'alert',
    });
  }

  const ordered = [...rows.values()];
  const labRank = (fact: KeyFact) => {
    const rank = LAB_ORDER.indexOf(fact.abbr);
    return rank === -1 ? LAB_ORDER.length : rank;
  };
  return {
    facts: [
      ...ordered.filter((r) => r.group === 'diagnosis'),
      ...[...labs.values()].toSorted((a, b) => labRank(a) - labRank(b)),
      ...ordered.filter((r) => r.group === 'general'),
      ...alerts,
    ],
    ecogWarnings,
  };
}
