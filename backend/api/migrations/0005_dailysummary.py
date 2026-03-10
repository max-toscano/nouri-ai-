from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_dailygoals'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailySummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('total_calories', models.FloatField(default=0)),
                ('total_protein', models.FloatField(default=0)),
                ('total_carbs', models.FloatField(default=0)),
                ('total_fat', models.FloatField(default=0)),
                ('total_water_ml', models.FloatField(default=0)),
                ('meal_count', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'daily_summaries',
                'ordering': ['-date'],
            },
        ),
    ]
