import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webcaf", "0038_organisation_email_domain"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisationemaildomain",
            name="domain",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="organisation_links",
                to="webcaf.allowedemaildomain",
            ),
        ),
    ]
