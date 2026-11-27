from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from webcaf.webcaf.models import Organisation, System, UserProfile

SUPERUSER_NAME = "admin"
SUPERUSER_PASSWORD = "password"  # pragma: allowlist secret
DEX_USER_NAMES = ["admin@example.gov.uk", "alice@example.gov.uk"]
DEX_USERS_PASSWORD = "password"  # pragma: allowlist secret
ORG_NAME = "An Organisation"
ORG_GSS_CODE = "E06000001"
SYSTEM_NAMES = ["Big System", "Little System"]


class Command(BaseCommand):
    help = "Creates a superuser, standard user, organisation, and systems"

    def handle(self, *args, **options):
        if not Organisation.objects.exists():
            Organisation.objects.create(name=ORG_NAME, organisation_type="council", gss_code=ORG_GSS_CODE)
            self.stdout.write(self.style.SUCCESS(f"Organisation '{ORG_NAME}' created"))

        if not User.objects.filter(username=SUPERUSER_NAME).exists():
            User.objects.create_superuser(
                username=SUPERUSER_NAME, email=f"{SUPERUSER_NAME}@admin.org", password=SUPERUSER_PASSWORD
            )

            # The superuser signs in to /admin/ only, which does not need a UserProfile.
            # Its access to organisations is not decided by seed data.
            self.stdout.write(self.style.SUCCESS(f"Superuser '{SUPERUSER_NAME}' created"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{SUPERUSER_NAME}' already exists"))

        organisation = Organisation.objects.first()

        for system_name in SYSTEM_NAMES:
            _, sys_created = System.objects.get_or_create(name=system_name, organisation=organisation)
            if not sys_created:
                self.stdout.write(
                    self.style.WARNING(f"System '{system_name}' already exists for organisation '{ORG_NAME}'")
                )

        for i, dex_username in enumerate(DEX_USER_NAMES):
            try:
                user = User.objects.get(username=dex_username)
                if not UserProfile.objects.filter(user=user).exists():
                    UserProfile.objects.create(
                        user=user, organisation=organisation, role=UserProfile.ROLE_CHOICES[i][0]
                    )
                    self.stdout.write(self.style.SUCCESS(f"UserProfile for '{dex_username}' created"))
                else:
                    self.stdout.write(self.style.WARNING(f"UserProfile for '{dex_username}' already exists"))
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"User '{dex_username}' does not exist. Login using DEX to create it.")
                )
