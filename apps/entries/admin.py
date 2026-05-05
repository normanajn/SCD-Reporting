from django.contrib import admin

from .models import WorkItem


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'project', 'category',
                    'period_start', 'period_end', 'is_private', 'created_at')
    list_filter = ('project', 'category', 'is_private')
    search_fields = ('title', 'description', 'author__email', 'author__display_name')
    raw_id_fields = ('author',)
    filter_horizontal = ('tags',)
    date_hierarchy = 'period_start'
    readonly_fields = ('created_at', 'updated_at')
