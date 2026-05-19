from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_add_division_head_role"),
        ("taxonomy", "0003_labpriority"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="managed_projects",
            field=models.ManyToManyField(
                blank=True, related_name="functional_leads", to="taxonomy.project"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("user", "User"),
                    ("group_leader", "Group Leader"),
                    ("division_head", "Division Head"),
                    ("functional_lead", "Functional Lead"),
                    ("auditor", "Auditor"),
                    ("admin", "Administrator"),
                ],
                db_index=True,
                default="user",
                max_length=16,
            ),
        ),
    ]
