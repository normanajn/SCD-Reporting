from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ADMIN = 'admin', 'Administrator'
        AUDITOR = 'auditor', 'Auditor'

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    employee_id = models.CharField(max_length=32, blank=True, db_index=True)
    display_name = models.CharField(max_length=128, blank=True)
    group = models.ForeignKey(
        'taxonomy.WorkGroup',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='members',
    )

    def __str__(self):
        return self.display_name or self.email or self.username

    @property
    def is_scd_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_auditor(self):
        return self.role in (self.Role.ADMIN, self.Role.AUDITOR)


class SiteSettings(models.Model):
    allow_signup = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Site Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'allow_signup': False})
        return obj
