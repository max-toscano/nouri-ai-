from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_meal_hydration'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyGoals',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calories_goal',    models.FloatField(null=True, blank=True)),
                ('protein_goal',     models.FloatField(null=True, blank=True)),
                ('carbs_goal',       models.FloatField(null=True, blank=True)),
                ('fat_goal',         models.FloatField(null=True, blank=True)),
                ('water_goal',       models.FloatField(null=True, blank=True, default=2000)),
                ('goal_type',        models.CharField(
                    max_length=10, null=True, blank=True,
                    choices=[('lose', 'Lose Weight'), ('maintain', 'Maintain Weight'), ('gain', 'Gain Weight')],
                )),
                ('goal_rate',        models.CharField(
                    max_length=5, null=True, blank=True,
                    choices=[('0.5', '0.5 lb/week'), ('1.0', '1.0 lb/week'), ('1.5', '1.5 lb/week'), ('2.0', '2.0 lb/week')],
                )),
                ('calculated_bmr',   models.FloatField(null=True, blank=True)),
                ('calculated_tdee',  models.FloatField(null=True, blank=True)),
                ('is_customized',    models.BooleanField(default=False)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'daily_goals',
                'ordering': ['-updated_at'],
            },
        ),
    ]
