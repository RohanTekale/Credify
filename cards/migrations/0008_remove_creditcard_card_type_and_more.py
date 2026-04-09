from django.db import migrations, models
import django.db.models.deletion


def set_base_fields(apps, schema_editor):
    CreditCard = apps.get_model('cards', 'CreditCard')
    CardType = apps.get_model('cards', 'CardType')
    try:
        # Fallback to 'Basic' CardType or first available
        default_card_type = CardType.objects.get(name='Basic')
    except CardType.DoesNotExist:
        default_card_type = CardType.objects.first()  # Use first available CardType
    for card in CreditCard.objects.all():
        card.base_card_type = card.effective_card_type or default_card_type
        card.original_credit_limit = card.credit_limit
        card.save()


class Migration(migrations.Migration):
    dependencies = [
        ('cards', '0007_subscription'),  # Matches your provided dependency
    ]

    operations = [
        # Rename card_type to effective_card_type
        migrations.RenameField(
            model_name='CreditCard',
            old_name='card_type',
            new_name='effective_card_type',
        ),
        # Add base_card_type to CreditCard
        migrations.AddField(
            model_name='CreditCard',
            name='base_card_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='base_cards',
                to='cards.cardtype',
                default=1,  # Placeholder, overridden by RunPython
            ),
            preserve_default=False,
        ),
        # Add original_credit_limit to CreditCard
        migrations.AddField(
            model_name='CreditCard',
            name='original_credit_limit',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
                default=0.00,  # Corrected default
            ),
            preserve_default=False,
        ),
        # Add subscription_fee to CardType
        migrations.AddField(
            model_name='CardType',
            name='subscription_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                max_digits=10,
            ),
        ),
        # Add min_income_for_permanent to CardType
        migrations.AddField(
            model_name='CardType',
            name='min_income_for_permanent',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                max_digits=10,
            ),
        ),
        # Populate base_card_type and original_credit_limit for existing rows
        migrations.RunPython(
            code=set_base_fields,
            reverse_code=lambda apps, schema_editor: None,  # No reverse, as this is a data migration
        ),
    ]