from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_bodystats'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meal',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meal_type',  models.CharField(max_length=10, choices=[('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner'), ('snack', 'Snack')])),
                ('food_name',  models.CharField(max_length=200)),
                ('calories',   models.FloatField(default=0)),
                ('protein',    models.FloatField(default=0)),
                ('carbs',      models.FloatField(default=0)),
                ('fat',        models.FloatField(default=0)),
                ('emoji',      models.CharField(max_length=10, default='🍽️')),
                ('timestamp',  models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'meals',
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='Hydration',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_ml',  models.FloatField()),
                ('timestamp',  models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'hydration',
                'ordering': ['timestamp'],
            },
        ),
    ]
