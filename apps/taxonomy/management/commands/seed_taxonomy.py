from django.core.management.base import BaseCommand

from apps.taxonomy.models import Category, LabPriority, Project

PROJECTS = [
    {'name': 'DUNE',       'short_code': 'DUNE',   'sort_order': 10},
    {'name': 'NOvA',       'short_code': 'NOvA',   'sort_order': 20},
    {'name': 'MicroBooNE', 'short_code': 'uBooNE', 'sort_order': 30},
    {'name': 'CMS',        'short_code': 'CMS',    'sort_order': 40},
    {'name': 'LSST',       'short_code': 'LSST',   'sort_order': 50},
]

CATEGORIES = [
    {'name': 'Scientific', 'short_code': 'SCI', 'sort_order': 10},
    {'name': 'Operations', 'short_code': 'OPS', 'sort_order': 20},
    {'name': 'Outreach',   'short_code': 'OUT', 'sort_order': 30},
    {'name': 'Training',   'short_code': 'TRN', 'sort_order': 40},
]

LAB_PRIORITIES = [
    {'name': 'Science Mission',  'short_code': 'SCI-MISS', 'sort_order': 10},
    {'name': 'DUNE/LBNF',        'short_code': 'DUNE',     'sort_order': 20},
    {'name': 'AI',               'short_code': 'AI',       'sort_order': 30},
    {'name': 'HL-LHC Upgrades',  'short_code': 'HL-LHC',   'sort_order': 40},
    {'name': 'Others',           'short_code': 'OTHER',    'sort_order': 50},
]


class Command(BaseCommand):
    help = 'Seed initial projects and categories (idempotent)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding projects…')
        for data in PROJECTS:
            name = data['name']
            defaults = {k: v for k, v in data.items() if k != 'name'}
            _, created = Project.objects.get_or_create(name=name, defaults=defaults)
            status = 'created' if created else 'exists '
            self.stdout.write(f'  [{status}] {name}')

        self.stdout.write('Seeding categories…')
        for data in CATEGORIES:
            name = data['name']
            defaults = {k: v for k, v in data.items() if k != 'name'}
            _, created = Category.objects.get_or_create(name=name, defaults=defaults)
            status = 'created' if created else 'exists '
            self.stdout.write(f'  [{status}] {name}')

        self.stdout.write('Seeding lab priorities…')
        for data in LAB_PRIORITIES:
            name = data['name']
            defaults = {k: v for k, v in data.items() if k != 'name'}
            _, created = LabPriority.objects.get_or_create(name=name, defaults=defaults)
            status = 'created' if created else 'exists '
            self.stdout.write(f'  [{status}] {name}')

        self.stdout.write(self.style.SUCCESS('Taxonomy seeded.'))
