import type { Metadata } from 'next';
import { LegalPage, PilotContact, Placeholder } from '@/components/legal/LegalPage';

export const metadata: Metadata = { title: 'Podmínky užití' };

/** Podmínky užití pilotu MDTcore (T-371, docs/PILOT.md §1 a §5). */
export default function TermsOfUsePage() {
  return (
    <LegalPage
      title="Podmínky užití"
      updated="11. 11. 2026"
      intro={
        <p>
          MDTcore připravuje podklady pro multidisciplinární onkologickou komisi s citacemi zdrojů. V pilotním provozu ho
          lékaři zkoušejí na fiktivních pacientech a říkají nám, co pomáhá a co chybí. Používáním aplikace s těmito
          podmínkami souhlasíte.
        </p>
      }
    >
      <section>
        <h2>Co pilot je a co není</h2>
        <ul>
          <li>MDTcore v pilotu <strong className="text-foreground">není zdravotnický prostředek</strong> a jeho výstupy se
            nepoužívají k rozhodování o léčbě skutečných pacientů.</li>
          <li>Pracuje se jen s fiktivními pacienty. Do aplikace nezadávejte ani nenahrávejte údaje skutečných pacientů.</li>
          <li>Rozhoduje vždy lékař. AI navrhuje s citací zdroje, barvy léčebných postupů počítají pravidla, ne AI.</li>
        </ul>
      </section>

      <section>
        <h2>Účet</h2>
        <ul>
          <li>Účet zakládá správce MDT pozvánkou. Je osobní, nepůjčujte ho a heslo nesdílejte.</li>
          <li>Na sdíleném počítači se odhlaste; aplikace vás po delší nečinnosti odhlásí sama.</li>
          <li>Správce může účet zablokovat, když hrozí zneužití, nebo po skončení pilotu.</li>
        </ul>
      </section>

      <section>
        <h2>AI a její omezení</h2>
        <ul>
          <li>AI se může mýlit. Každé tvrzení má citaci; neověřené je označené. Zkontrolujte zdroj, než se na tvrzení
            spolehnete.</li>
          <li>Přepis diskuse (AI zapisovatel) jen se souhlasem všech přítomných.</li>
          <li>Generování podkladu může trvat desítky sekund, ve špičce i déle.</li>
        </ul>
      </section>

      <section>
        <h2>Dostupnost</h2>
        <p>
          Pilot běží bez záruky dostupnosti. Aktualizace probíhají po domluvě mimo termíny zasedání. Data se zálohují
          denně; o ztrátě dat vás budeme informovat.
        </p>
      </section>

      <section>
        <h2>Odpovědnost</h2>
        <p>
          Provozovatel <Placeholder>název provozovatele</Placeholder> neodpovídá za rozhodnutí učiněná na základě
          výstupů aplikace v pilotu, protože se týkají jen fiktivních pacientů.
        </p>
      </section>

      <section>
        <h2>Hlášení problémů a kontakt</h2>
        <p>
          Co vás zarazí, nahlaste odkazem „Nahlásit problém nebo nápad“ v aplikaci nebo napište: <PilotContact />. Uveďte
          pacienta (Pxx), obrazovku a co se stalo; žádné údaje skutečných pacientů.
        </p>
      </section>
    </LegalPage>
  );
}
