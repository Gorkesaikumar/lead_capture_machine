from django.db import migrations

def backfill(apps, schema_editor):
    Conversation = apps.get_model("conversations", "Conversation")
    for conversation in Conversation.objects.select_related("customer").filter(organization__isnull=True).iterator():
        if conversation.customer.organization_id:
            Conversation.objects.filter(pk=conversation.pk).update(organization_id=conversation.customer.organization_id)

class Migration(migrations.Migration):
    dependencies = [("conversations", "0006_remove_message_unique_external_message_id_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
