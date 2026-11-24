from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower


class Command(BaseCommand):
    help = "Report case-only duplicate user emails without changing accounts or exposing email addresses."

    def handle(self, *args, **options):
        groups = list(
            User.objects.exclude(email="")
            .annotate(normalised_email=Lower("email"))
            .values("normalised_email")
            .annotate(email_variant_count=Count("email", distinct=True))
            .filter(email_variant_count__gt=1)
            .order_by("normalised_email")
        )
        self.stdout.write(f"Found {len(groups)} duplicate email groups.")
        for index, group in enumerate(groups, start=1):
            self.stdout.write(f"Group {index}:")
            users = (
                User.objects.annotate(normalised_email=Lower("email"))
                .filter(normalised_email=group["normalised_email"])
                .prefetch_related("profiles")
                .order_by("pk")
            )
            for user in users:
                self.stdout.write(f"  user_id={user.pk} active={user.is_active} staff={user.is_staff}")
                for profile in user.profiles.all():
                    self.stdout.write(
                        f"    profile_id={profile.pk} organisation_id={profile.organisation_id} role={profile.role}"
                    )
