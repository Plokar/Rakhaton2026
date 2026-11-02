import type { Decision, Practitioner, RoleId } from '@/types/mdt';

/**
 * Návrh úkolů po zasedání podle doporučeného postupu (T-350): každá modalita dostane úkol pro odbornost, která ho
 * provede, re-MDT a sdělení závěru pacientovi dostane zadávající lékař. Vlastník = přítomný lékař té odbornosti,
 * jinak lékař s účtem v aplikaci, jinak nevybráno. Pravidla, ne AI: předseda návrh upraví a potvrdí se závěrem.
 */

type Task = Decision['tasks'][number];

const MODALITY_TASK: Record<string, { role: RoleId | 'requester'; text: string; days: number }> = {
  chirurgie: { role: 'surgeon', text: 'Naplánovat operaci', days: 14 },
  rt: { role: 'radiation_oncologist', text: 'Plánovací CT a zahájení radioterapie', days: 14 },
  chemoterapie: { role: 'oncologist', text: 'Zahájit chemoterapii', days: 14 },
  hormonalni: { role: 'oncologist', text: 'Zahájit hormonální léčbu', days: 14 },
  cilena: { role: 'oncologist', text: 'Zahájit cílenou léčbu', days: 14 },
  imunoterapie: { role: 'oncologist', text: 'Zahájit imunoterapii', days: 14 },
  'jina-systemova': { role: 'oncologist', text: 'Zahájit systémovou léčbu', days: 14 },
  diagnostika: { role: 'requester', text: 'Objednat doplňující vyšetření', days: 14 },
  sledovani: { role: 'requester', text: 'Naplánovat kontrolu', days: 30 },
};

const addDays = (base: Date, days: number) => {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

const short = (text: string, limit = 120) => (text.length <= limit ? text : `${text.slice(0, limit).replace(/\s+\S*$/, '')} …`);

export function suggestTasks(
  decision: Decision,
  practitioners: Practitioner[],
  requesterUserId: number | null,
  today = new Date(),
): Task[] {
  const byRole = (role: RoleId) => {
    const present = decision.attendees.find((a) => a.role === role && a.user_id);
    if (present) return { owner: present.user_id, owner_name: present.name };
    const known = practitioners.find((p) => p.role === role && p.user) ?? practitioners.find((p) => p.role === role);
    return known ? { owner: known.id, owner_name: known.name } : { owner: '', owner_name: null };
  };
  const requester = () => {
    const p = practitioners.find((x) => x.user?.user_id === requesterUserId);
    return p ? { owner: p.id, owner_name: p.name } : { owner: '', owner_name: null };
  };
  const out: Task[] = [];
  const push = (description: string, who: { owner: string; owner_name: string | null }, due: string) => {
    const known = new Set([...decision.tasks, ...out].map((t) => t.description.trim()));
    if (known.has(description)) return;
    out.push({ id: `task${String(decision.tasks.length + out.length + 1).padStart(2, '0')}-${Date.now() % 10000}`,
      description, ...who, due_date: due, status: 'requested', source: 'human' });
  };
  for (const r of decision.sections.recommendation) {
    const rule = MODALITY_TASK[r.modality];
    if (!rule) continue;
    const description = r.text.trim() ? `${rule.text}: ${short(r.text.trim())}` : rule.text;
    push(description, rule.role === 'requester' ? requester() : byRole(rule.role), addDays(today, rule.days));
  }
  const reMdt = decision.sections.re_mdt;
  if (reMdt?.date) push(`Zařadit na re-MDT ${reMdt.date}${reMdt.reason ? `: ${short(reMdt.reason)}` : ''}`, requester(), reMdt.date);
  push('Seznámit pacienta se závěrem komise', requester(), addDays(today, 7));
  return out;
}
