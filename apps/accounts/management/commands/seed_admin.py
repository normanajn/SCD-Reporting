import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Create the initial SCD admin user if one does not already exist'

    def handle(self, *args, **options):
        username = os.environ.get('SCD_INITIAL_ADMIN_USERNAME', 'scd-admin')
        email = os.environ.get('SCD_INITIAL_ADMIN_EMAIL', 'scd-admin@fnal.gov')
        password = os.environ.get('SCD_INITIAL_ADMIN_PASSWORD', '')

        if not password:
            self.stdout.write(self.style.WARNING(
                'SCD_INITIAL_ADMIN_PASSWORD not set — skipping seed_admin.'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Admin user "{username}" already exists — skipping.')
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role=User.Role.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f'Created admin user: {username} ({email})'))
