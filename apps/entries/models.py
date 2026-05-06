from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models


class WorkItem(models.Model):
    class PeriodKind(models.TextChoices):
        WEEK       = 'week',       'Week'
        FORTNIGHT  = 'fortnight',  '2 Weeks'
        MONTH      = 'month',      'Month'
        CUSTOM     = 'custom',     'Custom'

    author    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='work_items',
    )
    title     = models.CharField(max_length=200)
    project   = models.ForeignKey(
        'taxonomy.Project',
        on_delete=models.PROTECT,
        related_name='work_items',
    )
    category  = models.ForeignKey(
        'taxonomy.Category',
        on_delete=models.PROTECT,
        related_name='work_items',
    )
    group     = models.ForeignKey(
        'taxonomy.WorkGroup',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='work_items',
    )
    tags      = models.ManyToManyField('taxonomy.Tag', blank=True)
    description  = models.TextField()
    period_kind  = models.CharField(
        max_length=12,
        choices=PeriodKind.choices,
        default=PeriodKind.WEEK,
    )
    period_start = models.DateField(db_index=True)
    period_end   = models.DateField(db_index=True)
    is_private   = models.BooleanField(default=False, db_index=True)
    is_critical  = models.BooleanField(default=False, db_index=True)
    is_highlight = models.BooleanField(default=False, db_index=True)
    highlight_stars = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(5)],
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', '-created_at']
        indexes = [
            models.Index(fields=['author', '-period_end']),
            models.Index(fields=['project', '-period_end']),
            models.Index(fields=['category', '-period_end']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['is_private', '-period_end']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F('period_start')),
                name='entries_workitem_end_gte_start',
            )
        ]

    def __str__(self):
        return f'{self.title} ({self.author})'
