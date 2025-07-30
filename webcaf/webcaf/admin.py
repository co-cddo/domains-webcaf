from django.contrib import admin

from webcaf.webcaf.models import Organisation, System, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    model = UserProfile
    search_fields = ["organisation__name", "user__email"]
    list_display = ["user__email", "organisation__name", "role"]


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    model = Organisation
    search_fields = ["name", "systems__name"]
    list_display = ["name"]


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    model = System
    search_fields = ["name"]
    list_display = ["name"]
