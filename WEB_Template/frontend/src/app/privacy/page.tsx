import type { Metadata } from 'next';
import { LegalPage, PilotContact, Placeholder } from '@/components/legal/LegalPage';

export const metadata: Metadata = { title: 'Zásady ochrany osobních údajů' };

/** Zásady soukromí pilotu MDTcore (T-371, docs/PILOT.md §1 a §5). */
export default function PrivacyPolicyPage() {
  return (
    <LegalPage
      title="Zásady ochrany osobních údajů"
      updated="11. 11. 2026"
      intro={
        <p>
          MDTcore je v pilotním provozu. Lékaři onkologických komisí ho zkoušejí <strong className="text-foreground">jen na
          fiktivních pacientech</strong>. Do aplikace se nezadávají ani nenahrávají údaje skutečných pacientů (jména, rodná
          čísla, zprávy). Tady popisujeme, jaké údaje o vás jako uživateli aplikace ukládáme a proč.
        </p>
      }
    >
      <section>
        <h2>Kdo údaje zpracovává</h2>
        <p>
          Správcem je provozovatel pilotu: <Placeholder>název, sídlo a IČO</Placeholder>. S dotazy a žádostmi se obracejte
          na <PilotContact />.
        </p>
      </section>

      <section>
        <h2>Jaké údaje ukládáme</h2>
        <ul>
          <li><strong className="text-foreground">Účet:</strong> uživatelské jméno, jméno a tituly, e-mail, odbornost, role
            v komisi, nemocnice a komise, kam jste pozvaní.</li>
          <li><strong className="text-foreground">Nastavení:</strong> vaše šablona okna pro projektor, požadavky na podklad
            a normy pro řešení.</li>
          <li><strong className="text-foreground">Práce v aplikaci:</strong> co jste zapsali (závěry, úkoly, zprávy v chatu
            zasedání, dotazy na AI) a kdy.</li>
          <li><strong className="text-foreground">Záznam přístupů:</strong> kdo kdy otevřel kterého pacienta, stáhl export
            nebo zapsal (uživatel, ID pacienta, čas, IP adresa). Slouží k dohledatelnosti a vidí ho jen správce MDT.</li>
          <li><strong className="text-foreground">Technické záznamy serveru:</strong> chyby a přístupy kvůli provozu a
            bezpečnosti.</li>
        </ul>
      </section>

      <section>
        <h2>Proč a na jakém základě</h2>
        <p>
          Údaje potřebujeme, abyste se mohli přihlásit, pracovat v komisi a aby bylo dohledatelné, kdo co v aplikaci
          udělal. Právním základem je oprávněný zájem provozovatele na zajištění a vyhodnocení pilotu (čl. 6 odst. 1
          písm. f GDPR) <Placeholder>potvrdit právní základ, případně smlouvu s nemocnicí</Placeholder>.
        </p>
      </section>

      <section>
        <h2>Umělá inteligence</h2>
        <p>
          Podklady, přepis diskuse a odpovědi chatbotu připravuje AI u externích poskytovatelů (jazykový model NVIDIA,
          přepis řeči Groq). V pilotu jim odcházejí <strong className="text-foreground">jen data fiktivních pacientů</strong>.
          Aplikace sama blokuje odeslání dat pacienta, který není označený jako fiktivní. Vaše jméno ani e-mail
          poskytovatelům AI neposíláme. Výstupy AI nejsou podkladem pro léčbu a nic se nestane záznamem bez potvrzení lékařem.
        </p>
      </section>

      <section>
        <h2>Cookies a úložiště prohlížeče</h2>
        <p>Používáme jen nezbytné cookies, bez nich se nelze přihlásit. Analytické ani reklamní cookies nepoužíváme.</p>
        <ul>
          <li><code>access_token</code>, <code>refresh_token</code>: přihlášení (httpOnly, 15 minut a 7 dní).</li>
          <li><code>csrftoken</code>: ochrana formulářů proti podvrženým požadavkům.</li>
          <li>Úložiště prohlížeče (localStorage): světlý nebo tmavý vzhled, rozložení panelů, poslední pacient na
            projektoru. Zůstává jen ve vašem prohlížeči.</li>
        </ul>
      </section>

      <section>
        <h2>Jak dlouho</h2>
        <p>
          Účty se po skončení pilotu deaktivují; údaje a zálohy se smažou podle dohody s provozovatelem
          <Placeholder>lhůta pro smazání</Placeholder>. Zálohy serveru se drží 14 dní.
        </p>
      </section>

      <section>
        <h2>Vaše práva</h2>
        <p>
          Máte právo na přístup ke svým údajům, jejich opravu, výmaz, omezení zpracování a vznést námitku. Napište
          koordinátorovi pilotu (<PilotContact />). Stížnost můžete podat u Úřadu pro ochranu osobních údajů (uoou.gov.cz).
        </p>
      </section>
    </LegalPage>
  );
}
