from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ['id', 'phone', 'first_name', 'last_name', 'user_type', 'is_active', 'is_staff']
    list_filter = ['user_type', 'is_active', 'is_staff']
    search_fields = ['phone', 'first_name', 'last_name']
    ordering = ['-date_joined']  # Changed from 'username' to '-date_joined'
    
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'fathers_first_name')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'first_name', 'last_name', 'fathers_first_name', 'user_type', 'password1', 'password2'),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['date_joined', 'last_login']
        return []

# Register the User model
admin.site.register(User, CustomUserAdmin)