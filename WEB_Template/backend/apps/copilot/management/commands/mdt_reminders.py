"""Připomínky lékařům e-mailem (T-384), spouští cron: `manage.py mdt_reminders` (denně ráno) a
`manage.py mdt_reminders --only new-results` (každou hodinu). `--dry-run` jen vypíše, komu by co šlo.

Druhy: `day-before` (zítřejší zasedání: co chybí, co je nového), `tasks` (úkoly po termínu), `re-mdt`
(plánované re-MDT bez zařazení), `new-results` (nové výsledky pacienta před zasedáním). Pacient jen jako `Pxx`.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.mdt import roles
from services import followup
from services.email_service import send_email

KINDS = {
    'day-before': ('Zítra máte pacienty na MDT', 'Zítra jsou na MDT vaši pacienti. Před zasedáním zkontrolujte:'),
    'tasks': ('Úkoly z MDT po termínu', 'Tyto úkoly z MDT jsou po termínu:'),
    're-mdt': ('Plánované re-MDT', 'U těchto pacientů komise naplánovala opětovné projednání a zatím nejsou zařazení:'),
    'new-results': ('Nové výsledky pacientů před MDT', 'U pacientů na nejbližším MDT přibyly výsledky:'),
}


class Command(BaseCommand):
    help = 'Pošle připomínky lékařům (zítřejší MDT, úkoly po termínu, re-MDT, nové výsledky).'

    def add_arguments(self, parser):
        parser.add_argument('--only', choices=sorted(KINDS), action='append')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, only, dry_run, **options):
        base = (getattr(settings, 'MDT_FRONTEND_URL', '') or 'http://localhost:3000').rstrip('/')
        sent = 0
        for kind in only or list(KINDS):
            if kind == 're-mdt':
                lines = {}
                for item in followup.re_mdt_due():
                    if item['requester']:
                        when = 'po termínu ' if item['overdue'] else ''
                        lines.setdefault(item['requester']['user_id'], []).append(
                            f'{item["patient_id"]}: re-MDT {when}{item["date"]} ({item["reason"] or "bez důvodu"})')
            elif kind == 'day-before':
                lines = followup.day_before()
            elif kind == 'tasks':
                lines = followup.overdue_tasks()
            else:
                lines = followup.new_results(record=not dry_run)
            subject, intro = KINDS[kind]
            for uid, user in followup.users(lines).items():
                body = '\n'.join([f'Dobrý den, {roles.display_name(user)},', '', intro, '',
                                  *[f'• {line}' for line in lines[uid]], '', f'MDTcore: {base}/dashboard'])
                if dry_run:
                    self.stdout.write(f'[{kind}] {user.username}: {len(lines[uid])} položek')
                elif user.email and send_email(user.email, f'MDTcore: {subject}', body):
                    sent += 1
        self.stdout.write(f'Odesláno {sent} e-mailů.' if not dry_run else 'Bez odeslání (--dry-run).')
