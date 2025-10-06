from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from webcaf.webcaf.models import Organisation, System, UserProfile

SUPERUSER_NAME = "admin"
SUPERUSER_PASSWORD = "password"  # pragma: allowlist secret
DEX_USER_NAMES = ["admin@example.gov.uk", "alice@example.gov.uk"]
DEX_USERS_PASSWORD = "password"  # pragma: allowlist secret
ORG_NAME = "An Organisation"
SYSTEM_NAMES = ["Big System", "Little System"]


class Command(BaseCommand):
    help = "Creates a superuser, standard user, organisation, and systems"

    def handle(self, *args, **options):
        if not User.objects.filter(username=SUPERUSER_NAME).exists():
            superuser = User.objects.create_superuser(
                username=SUPERUSER_NAME, email=f"{SUPERUSER_NAME}@example.com", password=SUPERUSER_PASSWORD
            )

            UserProfile.objects.create(user=superuser)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{SUPERUSER_NAME}' created"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{SUPERUSER_NAME}' already exists"))

        organisation, org_created = Organisation.objects.get_or_create(name=ORG_NAME)
        if not org_created:
            self.stdout.write(self.style.WARNING(f"Organisation '{ORG_NAME}' already exists"))

        for system_name in SYSTEM_NAMES:
            _, sys_created = System.objects.get_or_create(name=system_name, organisation=organisation)
            if not sys_created:
                self.stdout.write(
                    self.style.WARNING(f"System '{system_name}' already exists for organisation '{ORG_NAME}'")
                )

        for i, dex_username in enumerate(DEX_USER_NAMES):
            try:
                user = User.objects.get(username=dex_username)
                UserProfile.objects.create(user=user, organisation=organisation, role=UserProfile.ROLE_CHOICES[i][0])
                self.stdout.write(self.style.WARNING(f"User '{dex_username}' found and profile added"))
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"User '{dex_username}' does not exist. Login using DEX to create it.")
                )
