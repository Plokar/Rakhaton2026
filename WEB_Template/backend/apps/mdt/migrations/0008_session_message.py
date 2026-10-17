import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mdt", "0007_case_projector_layout"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SessionMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(max_length=2000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                             related_name="mdt_messages", to=settings.AUTH_USER_MODEL)),
                ("case", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="messages", to="mdt.mdtcase")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages",
                                              to="mdt.mdtsession")),
            ],
            options={"ordering": ["id"]},
        ),
    ]
