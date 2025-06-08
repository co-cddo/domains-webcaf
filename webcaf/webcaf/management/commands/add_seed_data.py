from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from webcaf.webcaf.models import Organisation, System, UserProfile

SUPERUSER_NAME = "admin"
SUPERUSER_PASSWORD = SUPERUSER_NAME
USER_NAME = "user"
USER_PASSWORD = USER_NAME
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

        if not User.objects.filter(username=USER_NAME).exists():
            user = User.objects.create_user(
                username=USER_NAME, email=f"{USER_NAME}@example.com", password=USER_PASSWORD
            )

            UserProfile.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f"Standard user '{USER_NAME}' created"))
        else:
            user = User.objects.get(username=USER_NAME)
            self.stdout.write(self.style.WARNING(f"Standard user '{USER_NAME}' already exists"))

        organisation, org_created = Organisation.objects.get_or_create(name=ORG_NAME)
        if not org_created:
            self.stdout.write(self.style.WARNING(f"Organisation '{ORG_NAME}' already exists"))

        profile = UserProfile.objects.get(user__username=USER_NAME)
        profile.organisation = organisation
        profile.save()

        for system_name in SYSTEM_NAMES:
            _, sys_created = System.objects.get_or_create(name=system_name, organisation=organisation)
            if not sys_created:
                self.stdout.write(
                    self.style.WARNING(f"System '{system_name}' already exists for organisation '{ORG_NAME}'")
                )
