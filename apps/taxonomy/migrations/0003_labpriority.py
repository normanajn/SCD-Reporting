from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taxonomy", "0002_workgroup"),
    ]

    operations = [
        migrations.CreateModel(
            name="LabPriority",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=100, unique=True)),
                ("short_code", models.CharField(blank=True, max_length=20)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(db_index=True, default=0),
                ),
            ],
            options={
                "verbose_name": "Lab Priority",
                "verbose_name_plural": "Lab Priorities",
                "ordering": ["sort_order", "name"],
                "abstract": False,
            },
        ),
    ]
