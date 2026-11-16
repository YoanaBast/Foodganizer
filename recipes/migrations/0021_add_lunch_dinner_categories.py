from django.db import migrations


def add_categories(apps, schema_editor):
    RecipeCategory = apps.get_model('recipes', 'RecipeCategory')
    for name in ('lunch', 'dinner'):
        RecipeCategory.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0020_recipe_photo'),
    ]

    operations = [
        migrations.RunPython(add_categories, migrations.RunPython.noop),
    ]
