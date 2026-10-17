'use client';

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Kbd, KbdGroup } from '@/components/shadcn/kbd';

const SHORTCUTS: { group: string; items: { keys: string[]; label: string }[] }[] = [
  {
    group: 'Všude',
    items: [
      { keys: ['Ctrl', 'K'], label: 'Vyhledat pacienta, zasedání nebo akci' },
      { keys: ['Ctrl', 'B'], label: 'Sbalit nebo rozbalit postranní panel' },
      { keys: ['?'], label: 'Tato nápověda' },
    ],
  },
  {
    group: 'Jednání komise',
    items: [
      { keys: ['↓'], label: 'Další pacient (také J)' },
      { keys: ['↑'], label: 'Předchozí pacient (také K)' },
      { keys: ['D'], label: 'Otevřít detail pacienta' },
      { keys: ['Z'], label: 'Závěr komise' },
      { keys: ['P'], label: 'Okno pro projektor' },
      { keys: ['H'], label: 'Označit jako projednané (předseda)' },
    ],
  },
  {
    group: 'Kalendář',
    items: [
      { keys: ['Mezerník'], label: 'Zvednout nebo položit pacienta při přesunu' },
      { keys: ['← →', '↑ ↓'], label: 'Posunout pacienta na jiný den nebo board' },
      { keys: ['Esc'], label: 'Zrušit přesun, zavřít panel' },
    ],
  },
];

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Klávesové zkratky</DialogTitle>
          <DialogDescription>Jednání komise jde vést jen z klávesnice.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-5">
          {SHORTCUTS.map((section) => (
            <section key={section.group} aria-labelledby={`shortcuts-${section.group}`}>
              <h3 id={`shortcuts-${section.group}`} className="mb-2 text-sm font-medium text-foreground">{section.group}</h3>
              <dl className="flex flex-col gap-1.5">
                {section.items.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-4 text-sm">
                    <dt className="text-muted-foreground">{item.label}</dt>
                    <dd>
                      <KbdGroup>
                        {item.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}
                      </KbdGroup>
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
