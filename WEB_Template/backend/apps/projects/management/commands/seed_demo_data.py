from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.projects.models import Project, Task, Notification
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Naplní databázi realistickými demo daty pro okamžité testování na hackathonu'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🌱 Začínám seedovat demo data..."))

        # 1. Uživatelé
        users = [
            {
                'username': 'admin',
                'email': 'admin@hackathon.local',
                'first_name': 'Sebastian',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'password': 'admin123456',
            },
            {
                'username': 'alice',
                'email': 'alice@hackathon.local',
                'first_name': 'Alice',
                'last_name': 'Smith',
                'is_staff': False,
                'is_superuser': False,
                'password': 'demo123456',
            },
            {
                'username': 'bob',
                'email': 'bob@hackathon.local',
                'first_name': 'Bob',
                'last_name': 'Jenkins',
                'is_staff': False,
                'is_superuser': False,
                'password': 'demo123456',
            },
            {
                'username': 'charlie',
                'email': 'charlie@hackathon.local',
                'first_name': 'Charlie',
                'last_name': 'Brown',
                'is_staff': False,
                'is_superuser': False,
                'password': 'demo123456',
            },
        ]

        user_instances = {}
        for u in users:
            user, created = User.objects.get_or_create(
                username=u['username'],
                defaults={
                    'email': u['email'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'is_staff': u['is_staff'],
                    'is_superuser': u['is_superuser'],
                }
            )
            user.set_password(u['password'])
            user.save()
            user_instances[u['username']] = user
            status_text = "vytvořen" if created else "aktualizován"
            self.stdout.write(f"   👤 Uživatel '{u['username']}' ({status_text})")

        admin_user = user_instances['admin']
        alice = user_instances['alice']
        bob = user_instances['bob']
        charlie = user_instances['charlie']

        # 2. Projekty
        projects_data = [
            {
                'title': 'VoiceAgent Copilot',
                'category': 'ai',
                'status': 'in_progress',
                'priority': 'urgent',
                'progress': 70,
                'description': 'Real-time obousměrný hlasový AI asistent s latencí pod 200 ms pro zákaznickou podporu.',
                'github_repo': 'https://github.com/hackathon-team/voice-copilot',
                'demo_url': 'https://voice-copilot.demo.local',
                'created_by': alice,
            },
            {
                'title': 'FinTech Fraud Sentinel',
                'category': 'fintech',
                'status': 'in_progress',
                'priority': 'high',
                'progress': 45,
                'description': 'Detekce podvodných transakcí v reálném čase využívající machine learning a grafovou analýzu.',
                'github_repo': 'https://github.com/hackathon-team/fraud-sentinel',
                'demo_url': '',
                'created_by': bob,
            },
            {
                'title': 'Autonomous Logistics Grid',
                'category': 'infra',
                'status': 'planning',
                'priority': 'medium',
                'progress': 20,
                'description': 'Optimalizace rozvozových tras a synchronizace autonomních kurýrů přes WebSocket event bus.',
                'github_repo': 'https://github.com/hackathon-team/logistics-grid',
                'demo_url': '',
                'created_by': admin_user,
            },
            {
                'title': 'HealthScan Vision AI',
                'category': 'ai',
                'status': 'completed',
                'priority': 'high',
                'progress': 100,
                'description': 'Automatizovaná analýza rentgenových snímků a CT skenů s 98.4% přesností detekce anomálií.',
                'github_repo': 'https://github.com/hackathon-team/healthscan',
                'demo_url': 'https://healthscan.demo.local',
                'created_by': alice,
            },
        ]

        project_instances = []
        for p in projects_data:
            proj, _ = Project.objects.update_or_create(
                title=p['title'],
                defaults=p
            )
            project_instances.append(proj)
            self.stdout.write(f"   🚀 Projekt '{proj.title}'")

        p_voice, p_fraud, p_logistics, p_health = project_instances

        # 3. Úkoly
        today = date.today()
        tasks_data = [
            # VoiceAgent
            {
                'project': p_voice,
                'title': 'Streaming audio pipeline přes WebSockets',
                'description': 'Připojit mikrofon z browseru přes WebAudio API na Django Channels /ws/room/audio/.',
                'status': 'done',
                'priority': 'urgent',
                'due_date': today - timedelta(days=1),
                'assignee': bob,
            },
            {
                'project': p_voice,
                'title': 'Integrace Gemini 2.0 Flash Audio streamu',
                'description': 'Přímé napojení na Gemini Multimodal Live API pro nulovou prodlevu.',
                'status': 'in_progress',
                'priority': 'urgent',
                'due_date': today + timedelta(days=1),
                'assignee': alice,
            },
            {
                'project': p_voice,
                'title': 'Audio visualizer waveform komponenta',
                'description': 'Krásná plynulá animace zvukové vlny v Reactu bez lagování.',
                'status': 'done',
                'priority': 'medium',
                'due_date': today,
                'assignee': charlie,
            },
            {
                'project': p_voice,
                'title': 'Zátěžový test latence (< 200 ms)',
                'description': 'Změřit round-trip čas z browseru přes Traefik do modelu a zpět.',
                'status': 'todo',
                'priority': 'high',
                'due_date': today + timedelta(days=2),
                'assignee': alice,
            },

            # FinTech
            {
                'project': p_fraud,
                'title': 'Architektura anomálního modelu (Isolation Forest)',
                'description': 'Předtrénovaný lehký model pro rychlou klasifikaci transakčních rizik.',
                'status': 'done',
                'priority': 'high',
                'due_date': today - timedelta(days=2),
                'assignee': alice,
            },
            {
                'project': p_fraud,
                'title': 'Interaktivní Fraud Alert Dashboard tabulka',
                'description': 'Tabulka s live badge indikátory (Bezpečné, Podezřelé, Blokováno).',
                'status': 'in_progress',
                'priority': 'high',
                'due_date': today + timedelta(days=1),
                'assignee': charlie,
            },
            {
                'project': p_fraud,
                'title': 'PostgreSQL Timeseries partitioning',
                'description': 'Optimalizace dotazů na miliony transakcí za vteřinu.',
                'status': 'todo',
                'priority': 'medium',
                'due_date': today + timedelta(days=3),
                'assignee': bob,
            },

            # Logistics
            {
                'project': p_logistics,
                'title': 'Heuristický algoritmus pro TSP (Travelling Salesperson)',
                'description': 'Výpočet nejkratší cesty pro flotilu 50 vozidel.',
                'status': 'in_progress',
                'priority': 'high',
                'due_date': today + timedelta(days=2),
                'assignee': bob,
            },
            {
                'project': p_logistics,
                'title': 'Mapová vrstva s živou telemetrií',
                'description': 'Zobrazení markerů aut na interaktivní mapě.',
                'status': 'todo',
                'priority': 'medium',
                'due_date': today + timedelta(days=4),
                'assignee': charlie,
            },

            # HealthScan
            {
                'project': p_health,
                'title': 'Modelové váhy pro rentgenovou klasifikaci',
                'description': 'Trénink na open-source datasetu NIH Chest X-ray.',
                'status': 'done',
                'priority': 'urgent',
                'due_date': today - timedelta(days=5),
                'assignee': alice,
            },
            {
                'project': p_health,
                'title': 'Generování PDF lékařského posudku',
                'description': 'Export výsledků diagnózy se signaturou a QR kódem.',
                'status': 'done',
                'priority': 'medium',
                'due_date': today - timedelta(days=3),
                'assignee': admin_user,
            },
        ]

        for t in tasks_data:
            Task.objects.update_or_create(
                title=t['title'],
                project=t['project'],
                defaults=t
            )

        self.stdout.write(f"   📋 Vytvořeno/aktualizováno {len(tasks_data)} úkolů.")

        # 4. Notifikace
        notifications_data = [
            {
                'user': admin_user,
                'title': '🚀 Vítejte v Hackathon OS!',
                'message': 'Váš stack je připraven. Všechny služby běží v Dockeru s hot-reloadem.',
                'type': 'success',
                'link': '/dashboard',
                'is_read': False,
            },
            {
                'user': admin_user,
                'title': '🤖 AI Studio aktivní',
                'message': 'Mock Provider je připraven pro okamžité generování odpovědí bez API klíčů.',
                'type': 'info',
                'link': '/dashboard/ai',
                'is_read': False,
            },
            {
                'user': admin_user,
                'title': '⚡ WebSocket spojení navázáno',
                'message': 'Kanál pro real-time události na /ws/echo/ a /ws/room/ je dostupný.',
                'type': 'info',
                'link': '/dashboard/realtime',
                'is_read': True,
            },
            {
                'user': admin_user,
                'title': '⏰ Hackathon odpočet běží',
                'message': 'Nezapomeňte připravit prezentaci a nahrát demo video.',
                'type': 'warning',
                'link': '/dashboard/projects',
                'is_read': False,
            },
            {
                'user': alice,
                'title': '🎉 Úkol dokončen',
                'message': 'Streaming audio pipeline byla úspěšně otestována.',
                'type': 'success',
                'link': '/dashboard/projects',
                'is_read': False,
            }
        ]

        for n in notifications_data:
            Notification.objects.get_or_create(
                user=n['user'],
                title=n['title'],
                defaults=n
            )

        self.stdout.write(f"   🔔 Vytvořeno {len(notifications_data)} ukázkových notifikací.")
        self.stdout.write(self.style.SUCCESS("✨ Demo data byla úspěšně naseedována! Přihlášení: admin / admin123456"))
