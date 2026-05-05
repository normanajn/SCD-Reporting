from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SCD Info', {'fields': ('role', 'employee_id', 'display_name')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('SCD Info', {'fields': ('role', 'employee_id', 'display_name')}),
    )
    search_fields = ('email', 'username', 'display_name', 'employee_id')
    ordering = ('email',)
