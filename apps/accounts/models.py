import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        FUNCTIONAL_LEAD = 'functional_lead', 'Functional Lead'
        GROUP_LEADER = 'group_leader', 'Group Leader'
        DIVISION_HEAD = 'division_head', 'Division Head'
        AUDITOR = 'auditor', 'Auditor'
        ADMIN = 'admin', 'Administrator'

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
    managed_groups = models.ManyToManyField(
        'taxonomy.WorkGroup',
        blank=True,
        related_name='division_heads',
    )
    managed_projects = models.ManyToManyField(
        'taxonomy.Project',
        blank=True,
        related_name='functional_leads',
    )

    def __str__(self):
        return self.display_name or self.email or self.username

    @property
    def is_scd_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_auditor(self):
        return self.role in (self.Role.ADMIN, self.Role.AUDITOR)

    @property
    def is_group_leader(self):
        return self.role == self.Role.GROUP_LEADER

    @property
    def is_division_head(self):
        return self.role == self.Role.DIVISION_HEAD

    @property
    def is_functional_lead(self):
        return self.role == self.Role.FUNCTIONAL_LEAD


class APIToken(models.Model):
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='api_token',
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"APIToken({self.user})"

    @classmethod
    def rotate(cls, user):
        """Replace (or create) the token for user and return it."""
        new_key = secrets.token_hex(32)
        obj, _ = cls.objects.update_or_create(
            user=user,
            defaults={'key': new_key},
        )
        return obj


class SiteSettings(models.Model):
    allow_signup = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Site Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'allow_signup': False})
        return obj
