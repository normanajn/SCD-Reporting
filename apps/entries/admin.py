from django.contrib import admin

from .models import WorkItem


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'projects_list', 'categories_list', 'entry_type',
                    'period_start', 'period_end', 'is_private', 'created_at')
    list_filter = ('projects', 'categories', 'entry_type', 'is_private')
    search_fields = ('title', 'description', 'author__email', 'author__display_name')
    raw_id_fields = ('author',)
    filter_horizontal = ('projects', 'categories', 'lab_priorities', 'tags')
    date_hierarchy = 'period_start'
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Projects')
    def projects_list(self, obj):
        return ', '.join(p.name for p in obj.projects.all())

    @admin.display(description='Categories')
    def categories_list(self, obj):
        return ', '.join(c.name for c in obj.categories.all())
