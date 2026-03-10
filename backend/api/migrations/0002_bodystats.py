# Generated migration for BodyStats model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BodyStats',
            fields=[
                ('id',             models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                # Raw user values
                ('weight',         models.FloatField(blank=True, null=True)),
                ('weight_unit',    models.CharField(choices=[('lbs', 'lbs'), ('kg', 'kg')], default='lbs', max_length=3)),
                ('height_feet',    models.IntegerField(blank=True, null=True)),
                ('height_inches',  models.FloatField(blank=True, null=True)),
                ('height_cm',      models.FloatField(blank=True, null=True)),
                ('height_unit',    models.CharField(choices=[('ft', 'ft/in'), ('cm', 'cm')], default='ft', max_length=2)),
                ('age',            models.IntegerField(blank=True, null=True)),
                ('sex',            models.CharField(blank=True, choices=[('M', 'Male'), ('F', 'Female')], max_length=1, null=True)),
                ('activity_level', models.CharField(blank=True, choices=[('sedentary', 'Sedentary'), ('light', 'Lightly Active'), ('moderate', 'Moderately Active'), ('active', 'Very Active'), ('extra', 'Extra Active')], max_length=20, null=True)),
                ('goal_weight',    models.FloatField(blank=True, null=True)),
                # Computed
                ('current_bmi',    models.FloatField(blank=True, null=True)),
                ('bmr',            models.FloatField(blank=True, null=True)),
                ('tdee',           models.FloatField(blank=True, null=True)),
                # Timestamps
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'body_stats',
                'ordering': ['-updated_at'],
            },
        ),
    ]
