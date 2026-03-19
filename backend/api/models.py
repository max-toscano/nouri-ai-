from django.db import models


class FoodCache(models.Model):
    source     = models.CharField(max_length=20)
    food_id    = models.CharField(max_length=200)
    data       = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source", "food_id")
        db_table        = "food_cache"

    def __str__(self):
        return f"{self.source}:{self.food_id}"


class BodyStats(models.Model):
    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary"),
        ("light",     "Lightly Active"),
        ("moderate",  "Moderately Active"),
        ("active",    "Very Active"),
        ("extra",     "Extra Active"),
    ]
    SEX_CHOICES         = [("M", "Male"),  ("F", "Female")]
    WEIGHT_UNIT_CHOICES = [("lbs", "lbs"), ("kg", "kg")]
    HEIGHT_UNIT_CHOICES = [("ft", "ft/in"), ("cm", "cm")]

    # ── Raw user-entered values (stored as-entered for lossless round-trip) ──
    weight        = models.FloatField(null=True, blank=True)
    weight_unit   = models.CharField(max_length=3, choices=WEIGHT_UNIT_CHOICES, default="lbs")
    height_feet   = models.IntegerField(null=True, blank=True)
    height_inches = models.FloatField(null=True, blank=True)
    height_cm     = models.FloatField(null=True, blank=True)
    height_unit   = models.CharField(max_length=2, choices=HEIGHT_UNIT_CHOICES, default="ft")
    age           = models.IntegerField(null=True, blank=True)
    sex           = models.CharField(max_length=1, choices=SEX_CHOICES, null=True, blank=True)
    activity_level = models.CharField(
        max_length=20, choices=ACTIVITY_CHOICES, null=True, blank=True
    )
    goal_weight   = models.FloatField(null=True, blank=True)

    # ── Computed / derived (calculated on save) ───────────────────────────────
    current_bmi   = models.FloatField(null=True, blank=True)
    bmr           = models.FloatField(null=True, blank=True)
    tdee          = models.FloatField(null=True, blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "body_stats"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"BodyStats @ {self.updated_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        """Auto-compute BMR, TDEE, and BMI from raw user values on every save."""
        from .services.calculator import (
            calc_bmr, calc_tdee, calc_bmi, get_weight_kg, get_height_cm,
        )

        stats = {
            "weight": self.weight,
            "weight_unit": self.weight_unit,
            "height_feet": self.height_feet,
            "height_inches": self.height_inches,
            "height_cm": self.height_cm,
            "height_unit": self.height_unit,
        }
        weight_kg = get_weight_kg(stats)
        height_cm = get_height_cm(stats)

        self.current_bmi = calc_bmi(weight_kg, height_cm)
        self.bmr = calc_bmr(weight_kg, height_cm, self.age, self.sex)
        self.tdee = calc_tdee(self.bmr, self.activity_level)

        super().save(*args, **kwargs)


class Meal(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Breakfast'),
        ('lunch',     'Lunch'),
        ('dinner',    'Dinner'),
        ('snack',     'Snack'),
    ]

    meal_type  = models.CharField(max_length=10, choices=MEAL_TYPES)
    food_name  = models.CharField(max_length=200)
    calories   = models.FloatField(default=0)
    protein    = models.FloatField(default=0)
    carbs      = models.FloatField(default=0)
    fat        = models.FloatField(default=0)
    emoji      = models.CharField(max_length=10, default='🍽️')
    timestamp  = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meals'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.meal_type}: {self.food_name} ({self.calories} kcal)"


class Hydration(models.Model):
    amount_ml  = models.FloatField()
    timestamp  = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hydration'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.amount_ml}ml @ {self.timestamp}"


class DailySummary(models.Model):
    """
    Cached daily totals — regenerated from Meal + Hydration entries.
    One row per date. Acts as a read-optimized cache, not source of truth.
    """
    date          = models.DateField(unique=True)
    total_calories = models.FloatField(default=0)
    total_protein  = models.FloatField(default=0)
    total_carbs    = models.FloatField(default=0)
    total_fat      = models.FloatField(default=0)
    total_water_ml = models.FloatField(default=0)
    meal_count     = models.IntegerField(default=0)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_summaries'
        ordering = ['-date']

    def __str__(self):
        return f"Summary {self.date}: {self.total_calories} kcal"

    @classmethod
    def rebuild(cls, date):
        """Rebuild summary from source Meal + Hydration rows for a given date."""
        from django.db.models import Sum, Count
        meal_agg = Meal.objects.filter(timestamp__date=date).aggregate(
            cal=Sum('calories'), pro=Sum('protein'),
            carb=Sum('carbs'), ft=Sum('fat'), cnt=Count('id'),
        )
        hydration_agg = Hydration.objects.filter(timestamp__date=date).aggregate(
            water=Sum('amount_ml'),
        )
        obj, _ = cls.objects.update_or_create(
            date=date,
            defaults={
                'total_calories': meal_agg['cal'] or 0,
                'total_protein':  meal_agg['pro'] or 0,
                'total_carbs':    meal_agg['carb'] or 0,
                'total_fat':      meal_agg['ft'] or 0,
                'total_water_ml': hydration_agg['water'] or 0,
                'meal_count':     meal_agg['cnt'] or 0,
            },
        )
        return obj


class DailyGoals(models.Model):
    GOAL_TYPE_CHOICES = [
        ('lose',     'Lose Weight'),
        ('maintain', 'Maintain Weight'),
        ('gain',     'Gain Weight'),
    ]
    GOAL_RATE_CHOICES = [
        ('0.5', '0.5 lb/week'),
        ('1.0', '1.0 lb/week'),
        ('1.5', '1.5 lb/week'),
        ('2.0', '2.0 lb/week'),
    ]

    # ── User goal targets ─────────────────────────────────────────────────────
    calories_goal   = models.FloatField(null=True, blank=True)
    protein_goal    = models.FloatField(null=True, blank=True)
    carbs_goal      = models.FloatField(null=True, blank=True)
    fat_goal        = models.FloatField(null=True, blank=True)
    water_goal      = models.FloatField(null=True, blank=True, default=2000)  # ml

    # ── Goal context (from questionnaire) ─────────────────────────────────────
    goal_type       = models.CharField(
        max_length=10, choices=GOAL_TYPE_CHOICES, null=True, blank=True
    )
    goal_rate       = models.CharField(
        max_length=5, choices=GOAL_RATE_CHOICES, null=True, blank=True
    )

    # ── Calculated values (stored for reference) ──────────────────────────────
    calculated_bmr  = models.FloatField(null=True, blank=True)
    calculated_tdee = models.FloatField(null=True, blank=True)

    # ── Meta ──────────────────────────────────────────────────────────────────
    is_customized   = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_goals'
        ordering = ['-updated_at']

    def __str__(self):
        return f"DailyGoals @ {self.updated_at:%Y-%m-%d %H:%M}"
