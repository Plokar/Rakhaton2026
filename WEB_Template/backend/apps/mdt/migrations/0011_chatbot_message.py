import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mdt", "0010_fact_template_titles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatbotMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "Lékař"), ("ai", "AI")], max_length=4)),
                ("text", models.TextField(blank=True)),
                ("claims", models.JSONField(blank=True, default=list)),
                ("uncertain", models.JSONField(blank=True, default=list)),
                ("model", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="chatbot_messages", to="mdt.mdtcase")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="chatbot_messages", to="mdt.mdtsession")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="mdt_chatbot_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["id"]},
        ),
    ]
