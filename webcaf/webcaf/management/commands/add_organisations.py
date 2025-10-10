import csv

from django.core.management.base import BaseCommand

from webcaf.webcaf.models import Organisation

CSV_PATH = "webcaf/seed/webcaf-orgs.csv"


class Command(BaseCommand):
    help = "Populate the Organisation table from webcaf-orgs.csv if the table is empty"

    def handle(self, *args, **options):
        if Organisation.objects.exists():
            self.stdout.write(self.style.WARNING("Organisation table is not empty. No data loaded."))
            return

        with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for count, row in enumerate(reader):
                pk = int(row["old_organisation_id"])
                name = row["organisation_name"]
                organisation_type = Organisation.get_type_id(row["organisation_type_description"])
                Organisation.objects.create(
                    pk=pk,
                    name=name,
                    organisation_type=organisation_type,
                )

            self.stdout.write(self.style.SUCCESS(f"Seeded {count + 1} organisations from {CSV_PATH}"))
