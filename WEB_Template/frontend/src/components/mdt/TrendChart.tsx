'use client';

import * as React from 'react';
import type { ObservationSeries, RoleId } from '@/types/mdt';
import { useCitationOpen } from './citations';
import { formatDate } from './format';

const W = 320;
const H = 96;
const PAD = { left: 8, right: 8, top: 10, bottom: 14 };

const fmt = (n: number) => n.toLocaleString('cs-CZ', { maximumFractionDigits: 2 });

/** Trend jedné řady (Hb, markery, hmotnost, PROMs…) s referenčním rozsahem; bod otevře zdroj (FR-R3). */
export function TrendChart({ series }: { series: ObservationSeries }) {
  const open = useCitationOpen();
  const points = series.points;
  const times = points.map((p) => new Date(p.date).getTime());
  const refLow = points.find((p) => p.ref_low !== undefined)?.ref_low;
  const refHigh = points.find((p) => p.ref_high !== undefined)?.ref_high;
  // Symptomy z PROMs mají pevnou škálu 0–10 a práh výrazné zátěže 7 (OBC-1.3); jinak měřítko podle dat.
  const promsScale = series.code.startsWith('proms:') && series.unit === null;
  const values = [...points.map((p) => p.value), ...(refLow !== undefined ? [refLow] : []), ...(refHigh !== undefined ? [refHigh] : [])];
  const [vMin, vMax] = promsScale ? [0, 10] : [Math.min(...values), Math.max(...values)];
  const span = vMax - vMin || 1;
  const [tMin, tMax] = [Math.min(...times), Math.max(...times)];
  const x = (t: number) => PAD.left + ((t - tMin) / (tMax - tMin || 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - vMin) / span) * (H - PAD.top - PAD.bottom);
  const first = points[0];
  const last = points[points.length - 1];
  const unit = series.unit ? ` ${series.unit}` : '';

  return (
    <figure className="rounded-lg border border-border bg-background p-2">
      <figcaption className="flex items-baseline justify-between gap-2 text-xs">
        <span className="font-semibold text-foreground">{series.label}</span>
        <span className="text-muted-foreground">
          {fmt(first.value)} → <span className="font-semibold text-foreground">{fmt(last.value)}</span>
          {unit}
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-1 h-24 w-full" role="img" aria-label={`${series.label}: ${points.map((p) => fmt(p.value)).join(', ')}${unit}`}>
        {refLow !== undefined && refHigh !== undefined && (
          <rect
            x={PAD.left}
            width={W - PAD.left - PAD.right}
            y={y(refHigh)}
            height={Math.max(1, y(refLow) - y(refHigh))}
            className="fill-foreground/[0.07]"
          />
        )}
        {promsScale && (
          <>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(7)} y2={y(7)} className="stroke-muted-foreground/60" strokeDasharray="4 3" />
            <text x={W - PAD.right} y={y(7) - 2} textAnchor="end" className="fill-muted-foreground text-[9px]">
              7 = výrazná zátěž
            </text>
          </>
        )}
        <polyline
          points={points.map((p, i) => `${x(times[i])},${y(p.value)}`).join(' ')}
          className="fill-none stroke-primary"
          strokeWidth={2}
        />
        {points.map((p, i) => (
          <circle
            key={p.citation}
            cx={x(times[i])}
            cy={y(p.value)}
            r={4}
            className="cursor-pointer fill-card stroke-primary hover:fill-primary"
            strokeWidth={2}
            onClick={() => open?.(p.citation)}
          >
            <title>{`${formatDate(p.date)}: ${fmt(p.value)}${unit} (${p.citation})`}</title>
          </circle>
        ))}
        <text x={PAD.left} y={H - 2} className="fill-muted-foreground text-[9px]">
          {formatDate(first.date)}
        </text>
        <text x={W - PAD.right} y={H - 2} textAnchor="end" className="fill-muted-foreground text-[9px]">
          {formatDate(last.date)}
        </text>
      </svg>
      <p className="flex flex-wrap gap-x-2 text-[10px] text-muted-foreground">
        {points.map((p) => (
          <button key={p.citation} type="button" onClick={() => open?.(p.citation)} className="hover:text-foreground hover:underline">
            {formatDate(p.date)} {fmt(p.value)}
            {p.interpretation && <> ({p.interpretation === 'H' ? '↑' : '↓'})</>}
          </button>
        ))}
        {refLow !== undefined && refHigh !== undefined && (
          <span>
            · norma {fmt(refLow)}–{fmt(refHigh)}
            {unit}
          </span>
        )}
      </p>
    </figure>
  );
}

/** Které řady patří do sekce odbornosti (FR-B2, FR-B5): markery a krevní obraz onkologovi, PROMs pacientovi. */
const ROLE_SERIES: Partial<Record<RoleId, string[]>> = {
  oncologist: ['2039-6', '24108-3', '6875-3', '718-7', '2951-2'],
  cardiologist: ['lvef'],
  pulmonologist: ['2951-2'],
  patient: ['29463-7', 'proms:brneni', 'proms:unava', 'proms:bolest', 'proms:dusnost', 'proms:psychika'],
};

export function seriesForRole(role: RoleId, all: ObservationSeries[]): ObservationSeries[] {
  const codes = ROLE_SERIES[role] ?? [];
  const byCode = new Map(all.map((s) => [s.code, s]));
  return codes
    .map((c) => byCode.get(c))
    .filter((s): s is ObservationSeries => !!s && s.points.length >= 2)
    // u PROMs jen symptomy, které se změnily nebo jsou výrazné (≥ 4/10), ať sekce nezahltí projektor
    .filter((s) => !s.code.startsWith('proms:') || Math.max(...s.points.map((p) => p.value)) >= 4 || Math.abs(s.points[s.points.length - 1].value - s.points[0].value) >= 2);
}

const PROMS_LABEL: Record<string, string> = {
  'proms:brneni': 'Brnění rukou a nohou (0–10)',
  'proms:unava': 'Únava (0–10)',
  'proms:bolest': 'Bolest (0–10)',
  'proms:dusnost': 'Dušnost (0–10)',
  'proms:psychika': 'Psychická zátěž (0–10)',
};

/** Čitelnější název řady PROMs (API vrací „PROMs: brneni“). */
export function withReadableLabel(s: ObservationSeries): ObservationSeries {
  return PROMS_LABEL[s.code] ? { ...s, label: `Pacient: ${PROMS_LABEL[s.code]}` } : s;
}
