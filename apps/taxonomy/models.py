from django.db import models
from django.utils.text import slugify


class TaxonomyBase(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    short_code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Project(TaxonomyBase):
    class Meta(TaxonomyBase.Meta):
        pass


class Category(TaxonomyBase):
    class Meta(TaxonomyBase.Meta):
        verbose_name_plural = 'categories'


class WorkGroup(TaxonomyBase):
    class Meta(TaxonomyBase.Meta):
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    use_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['-use_count', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.lower().strip()
        super().save(*args, **kwargs)
