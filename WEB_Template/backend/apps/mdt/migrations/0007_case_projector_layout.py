from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mdt", "0006_user_practitioner"),
    ]

    operations = [
        migrations.AddField(
            model_name="mdtcase",
            name="projector_layout",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
