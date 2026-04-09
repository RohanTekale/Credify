from django.db import migrations


def fix_original_credit_limit(apps, schema_editor):
    CreditCard = apps.get_model('cards', 'CreditCard')
    for card in CreditCard.objects.all():
        card.original_credit_limit = card.credit_limit
        card.save()


class Migration(migrations.Migration):
    dependencies = [
        ('cards', '0009_alter_creditcard_effective_card_type'),  # Matches your provided dependency
    ]

    operations = [
        migrations.RunPython(
            code=fix_original_credit_limit,
            reverse_code=lambda apps, schema_editor: None,  # No reverse, as this is a data migration
        ),
    ]