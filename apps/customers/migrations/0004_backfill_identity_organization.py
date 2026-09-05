from django.db import migrations

def backfill(apps, schema_editor):
    Identity = apps.get_model("customers", "CustomerIdentity")
    for identity in Identity.objects.select_related("customer").filter(organization__isnull=True).iterator():
        if identity.customer.organization_id:
            Identity.objects.filter(pk=identity.pk).update(organization_id=identity.customer.organization_id)

class Migration(migrations.Migration):
    dependencies = [("customers", "0003_remove_customeridentity_unique_channel_external_user_id_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
