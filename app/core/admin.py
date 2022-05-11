from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as CaseUserAdmin

from core import models


class UserAdmin(CaseUserAdmin):
    ordering = ['id']
    list_display = ['email', 'name']


admin.site.register(models.User, UserAdmin)

a = 2
