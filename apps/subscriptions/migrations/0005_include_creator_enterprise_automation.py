from django.db import migrations


def include_automation(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    label = "DM Automation included (no add-on required)"
    for plan in Plan.objects.using(schema_editor.connection.alias).filter(code__in=["creator", "enterprise"]):
        features = [feature for feature in (plan.features or [])
                    if not (isinstance(feature, str) and feature.startswith("DM Automation included"))]
        features.append(label)
        plan.can_use_automations = True
        plan.features = features
        plan.save(using=schema_editor.connection.alias, update_fields=["can_use_automations", "features"])


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0004_plan_automation_run_limit_and_more")]
    operations = [migrations.RunPython(include_automation, migrations.RunPython.noop)]
