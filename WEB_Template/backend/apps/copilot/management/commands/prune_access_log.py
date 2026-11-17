"""Smaže záznamy přístupů k pacientům starší než N dní (T-379). Cron: `manage.py prune_access_log --days 365`.

Záznam přístupů (T-370) je osobní údaj lékaře; drží se jen po dobu, kterou určí provozovatel (výchozí 365 dní,
`MDT_ACCESS_LOG_DAYS`).
"""
import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.mdt.models import AccessLog


class Command(BaseCommand):
    help = 'Smaže záznamy přístupů k pacientům starší než --days (výchozí MDT_ACCESS_LOG_DAYS nebo 365).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=int(os.environ.get('MDT_ACCESS_LOG_DAYS', '365')))
        parser.add_argument('--dry-run', action='store_true', help='jen spočítat, nic nemazat')

    def handle(self, *args, days, dry_run, **options):
        if days < 30:
            raise CommandError('--days aspoň 30 (záznam přístupů slouží ke kontrole zpětně).')
        old = AccessLog.objects.filter(created_at__lt=timezone.now() - timedelta(days=days))
        count = old.count()
        if not dry_run:
            old.delete()
        self.stdout.write(f'{"Smazalo by se" if dry_run else "Smazáno"} {count} záznamů starších než {days} dní.')
