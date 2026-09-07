"""Give the source_type index the name Django derives for it.

0003 hand-wrote the index name, which did not match the hash Django generates,
so every `makemigrations` reported an outstanding change. Cosmetic in the
database, but a permanent "you have unmade migrations" warning is exactly the
noise that hides a real one later.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_stockledgerentry_source_type'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='stockledgerentry',
            new_name='inventory_s_source__4eaadc_idx',
            old_name='inventory_s_source__6d7e0a_idx',
        ),
    ]
