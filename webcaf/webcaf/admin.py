from django.contrib import admin

from webcaf.webcaf.models import Assessment, Organisation, System, UserProfile


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
    list_display = ["name", "organisation__name"]


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    model = Assessment
    search_fields = ["status", "system__name"]
    list_display = ["status", "system__name", "system__organisation__name", "created_on", "last_updated"]
    list_filter = ["status", "system__organisation__name", "system__name"]
    ordering = ["-created_on"]
    list_select_related = ["system", "system__organisation"]
