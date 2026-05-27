from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0005_add_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='workitem',
            name='is_division_head_only',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
