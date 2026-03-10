from rest_framework import serializers
from .models import BodyStats, Meal, Hydration, DailyGoals, DailySummary


# ── Open Food Facts ────────────────────────────────────────────────────────────

class FoodSearchResultSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    brand = serializers.CharField()
    imageUrl = serializers.CharField()
    caloriesKcal = serializers.FloatField()
    proteinG = serializers.FloatField()
    carbsG = serializers.FloatField()
    fatG = serializers.FloatField()


class FoodDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    brand = serializers.CharField()
    imageUrl = serializers.CharField()
    caloriesKcal = serializers.FloatField()
    proteinG = serializers.FloatField()
    carbsG = serializers.FloatField()
    fatG = serializers.FloatField()
    servingSize = serializers.CharField(allow_null=True)


# ── USDA FoodData Central ──────────────────────────────────────────────────────

class UsdaSearchResultSerializer(serializers.Serializer):
    id         = serializers.CharField()
    name       = serializers.CharField()
    brand      = serializers.CharField()
    dataSource = serializers.CharField()


class UsdaFoodDetailsSerializer(serializers.Serializer):
    id           = serializers.CharField()
    name         = serializers.CharField()
    brand        = serializers.CharField()
    caloriesKcal = serializers.FloatField()
    proteinG     = serializers.FloatField()
    carbsG       = serializers.FloatField()
    fatG         = serializers.FloatField()
    dataSource   = serializers.CharField()


# ── Body Stats ────────────────────────────────────────────────────────────────

class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Meal
        fields = ['id', 'meal_type', 'food_name', 'calories', 'protein',
                  'carbs', 'fat', 'emoji', 'timestamp', 'created_at']
        read_only_fields = ['id', 'created_at']


class HydrationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Hydration
        fields = ['id', 'amount_ml', 'timestamp', 'created_at']
        read_only_fields = ['id', 'created_at']


class BodyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BodyStats
        fields = [
            "id",
            # Raw user values
            "weight", "weight_unit",
            "height_feet", "height_inches", "height_cm", "height_unit",
            "age", "sex", "activity_level", "goal_weight",
            # Computed
            "current_bmi", "bmr", "tdee",
            # Timestamps
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DailySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model  = DailySummary
        fields = [
            'id', 'date',
            'total_calories', 'total_protein', 'total_carbs', 'total_fat',
            'total_water_ml', 'meal_count', 'updated_at',
        ]
        read_only_fields = fields


class DailyGoalsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DailyGoals
        fields = [
            "id",
            # User goal targets
            "calories_goal", "protein_goal", "carbs_goal", "fat_goal", "water_goal",
            # Questionnaire context
            "goal_type", "goal_rate",
            # Calculated reference values
            "calculated_bmr", "calculated_tdee",
            # Meta
            "is_customized",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
