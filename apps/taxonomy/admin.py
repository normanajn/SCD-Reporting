from django.contrib import admin

from .models import Category, Project, Tag


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'short_code')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'short_code')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'use_count')
    readonly_fields = ('use_count',)
    search_fields = ('name',)
