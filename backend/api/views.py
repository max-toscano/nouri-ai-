import requests
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services.food_router import search as router_search, get_provider
from .services.cache import get_cached, set_cached
from .services.ai.modules import workout_quiz
from .services import calculator
from .models import BodyStats, Meal, Hydration, DailyGoals, DailySummary
from .serializers import (
    BodyStatsSerializer, MealSerializer, HydrationSerializer,
    DailyGoalsSerializer, DailySummarySerializer,
)

_VALID_SOURCES = {"openfoodfacts", "usda", "fatsecret"}


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def food_search(request):
    query = request.query_params.get("q", "").strip()

    if not query:
        return Response(
            {"error": "Query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(query) < 2:
        return Response(
            {"error": "Query must be at least 2 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = router_search(query)
    except Exception as exc:
        return Response(
            {"error": f"Search failed: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(result)


@api_view(["GET"])
def food_details(request, source, food_id):
    if source not in _VALID_SOURCES:
        return Response(
            {"error": f"Unknown source '{source}'. Valid: {sorted(_VALID_SOURCES)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Serve from cache when available
    cached = get_cached(source, food_id)
    if cached:
        return Response(cached)

    try:
        provider = get_provider(source)
        details  = provider.get_details(food_id)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except requests.RequestException as exc:
        return Response(
            {"error": f"Provider request failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    set_cached(source, food_id, details)
    return Response(details)


@api_view(["GET"])
def meals_today(request):
    today = timezone.now().date()
    meals = Meal.objects.filter(timestamp__date=today)
    return Response(MealSerializer(meals, many=True).data)


@api_view(["POST"])
def meals_create(request):
    serializer = MealSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def hydration_today(request):
    today = timezone.now().date()
    entries = Hydration.objects.filter(timestamp__date=today)
    total_ml = sum(e.amount_ml for e in entries)
    return Response({
        "total_ml": total_ml,
        "entries": HydrationSerializer(entries, many=True).data,
    })


@api_view(["POST"])
def hydration_create(request):
    serializer = HydrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def body_stats(request):
    if request.method == "GET":
        entry = BodyStats.objects.first()
        if not entry:
            return Response(None)
        return Response(BodyStatsSerializer(entry).data)

    # POST: upsert — update the existing singleton row or create the first one
    entry = BodyStats.objects.first()
    if entry:
        serializer = BodyStatsSerializer(entry, data=request.data)
    else:
        serializer = BodyStatsSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
def daily_goals(request):
    if request.method == "GET":
        entry = DailyGoals.objects.first()
        if not entry:
            return Response(None)
        return Response(DailyGoalsSerializer(entry).data)

    # POST: upsert — update the singleton row or create the first one
    entry = DailyGoals.objects.first()
    if entry:
        serializer = DailyGoalsSerializer(entry, data=request.data)
    else:
        serializer = DailyGoalsSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Date-parameterized endpoints ─────────────────────────────────────────────

def _parse_date(request):
    """Extract and validate the ?date=YYYY-MM-DD query param."""
    from datetime import datetime as dt
    raw = request.query_params.get("date", "").strip()
    if not raw:
        return timezone.now().date(), None
    try:
        return dt.strptime(raw, "%Y-%m-%d").date(), None
    except ValueError:
        return None, Response(
            {"error": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def daily_summary(request):
    """
    GET /api/daily-summary/?date=YYYY-MM-DD
    Returns aggregated totals for the given date (defaults to today).
    """
    date, err = _parse_date(request)
    if err:
        return err
    obj = DailySummary.rebuild(date)
    return Response(DailySummarySerializer(obj).data)


@api_view(["GET"])
def meals_by_date(request):
    """
    GET /api/meals/by-date/?date=YYYY-MM-DD
    Returns all meal entries for the given date.
    """
    date, err = _parse_date(request)
    if err:
        return err
    meals = Meal.objects.filter(timestamp__date=date)
    return Response(MealSerializer(meals, many=True).data)


@api_view(["GET"])
def hydration_by_date(request):
    """
    GET /api/hydration/by-date/?date=YYYY-MM-DD
    Returns total + entries for the given date.
    """
    date, err = _parse_date(request)
    if err:
        return err
    entries = Hydration.objects.filter(timestamp__date=date)
    total_ml = sum(e.amount_ml for e in entries)
    return Response({
        "date": str(date),
        "total_ml": total_ml,
        "entries": HydrationSerializer(entries, many=True).data,
    })


@api_view(["GET"])
def workout_quiz_questions(request):
    """
    GET /api/workout/quiz/          → returns the gateway question (pick your goal)
    GET /api/workout/quiz/?goal=X   → returns core + path-specific questions for goal X
    """
    goal = request.query_params.get("goal", "").strip() or None

    try:
        data = workout_quiz.get_questions(goal)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data)


@api_view(["POST"])
def workout_quiz_submit(request):
    """
    POST /api/workout/generate/
    Body: {
      quiz_answers: {
        goal, fitness_level, days_per_week, session_length, equipment,
        injuries, preferences,
        // + path-specific: loss_rate, cardio_preference, bulk_approach, priority_muscles
      },
      body_data: {
        weight, weight_unit, height_feet, height_inches, height_cm, height_unit,
        age, sex, activity_level, goal_weight
      }
    }

    1. Saves body_data → BodyStats (auto-computes BMR/TDEE/BMI)
    2. Calculates calorie target + macros based on goal
    3. Auto-saves to DailyGoals
    4. Sends everything to OpenAI → returns workout program + nutrition
    """
    quiz_answers = request.data.get("quiz_answers")
    if not quiz_answers:
        return Response(
            {"error": "quiz_answers is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── 0. Validate all inputs before doing anything ──
    quiz_errors = workout_quiz.validate_quiz_answers(quiz_answers)
    if quiz_errors:
        return Response(
            {"error": "Invalid quiz answers.", "fields": quiz_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    body_data = request.data.get("body_data")
    body_errors = workout_quiz.validate_body_data(body_data)
    if body_errors:
        return Response(
            {"error": "Invalid body data.", "fields": body_errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    goal = quiz_answers.get("goal")

    # ── 1. Upsert body stats (triggers save() → computes BMR/TDEE/BMI) ──
    if body_data:
        entry = BodyStats.objects.first()
        if entry:
            serializer = BodyStatsSerializer(entry, data=body_data)
        else:
            serializer = BodyStatsSerializer(data=body_data)

        if serializer.is_valid():
            serializer.save()

    # Pull the (possibly updated) body stats from DB
    body_stats_entry = BodyStats.objects.first()
    body_stats_dict = BodyStatsSerializer(body_stats_entry).data if body_stats_entry else None

    # ── 2. Calculate calorie target + macros ──
    nutrition = None
    if body_stats_dict and goal:
        # Determine the rate_or_approach based on goal path
        rate_or_approach = None
        if goal == "lose_weight":
            rate_or_approach = quiz_answers.get("loss_rate", "1.0")
        elif goal == "gain_weight":
            rate_or_approach = quiz_answers.get("gain_rate", "0.5")

        nutrition = calculator.recommend(body_stats_dict, goal, rate_or_approach)

    # ── 3. Auto-save to DailyGoals ──
    if nutrition:
        goal_type_map = {
            "lose_weight": "lose",
            "gain_weight": "gain",
            "maingain": "maintain",
        }
        goals_data = {
            "calories_goal": nutrition["calorie_target"],
            "protein_goal": nutrition["protein"],
            "carbs_goal": nutrition["carbs"],
            "fat_goal": nutrition["fat"],
            "goal_type": goal_type_map.get(goal, "maintain"),
            "calculated_bmr": nutrition["bmr"],
            "calculated_tdee": nutrition["tdee"],
        }
        if goal == "lose_weight":
            goals_data["goal_rate"] = quiz_answers.get("loss_rate", "1.0")

        goals_entry = DailyGoals.objects.first()
        if goals_entry:
            goals_serializer = DailyGoalsSerializer(goals_entry, data=goals_data)
        else:
            goals_serializer = DailyGoalsSerializer(data=goals_data)

        if goals_serializer.is_valid():
            goals_serializer.save()

    # ── 4. Generate workout program via AI ──
    try:
        program = workout_quiz.generate(quiz_answers, body_stats_dict, nutrition)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    response_data = {"program": program}
    if nutrition:
        response_data["nutrition"] = nutrition

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET"])
def week_summary(request):
    """
    GET /api/week-summary/?start=YYYY-MM-DD
    Returns daily summaries for 7 consecutive days starting from `start`.
    Includes weekly_calories, avg_daily, total_cal, and goal_days.
    goal_days = number of days where the user met ALL of their daily goals
    (calories + protein + carbs + fat). Days with no data count as 0 (not met).
    If no daily goals are set, goal_days is 0.
    """
    from datetime import timedelta
    from datetime import datetime as dt
    raw = request.query_params.get("start", "").strip()
    if not raw:
        today = timezone.now().date()
        start = today - timedelta(days=today.weekday())
    else:
        try:
            start = dt.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Fetch the user's daily goals (singleton)
    goals = DailyGoals.objects.first()

    days = []
    total_cal = 0
    goal_days = 0

    for i in range(7):
        d = start + timedelta(days=i)
        obj = DailySummary.rebuild(d)
        data = DailySummarySerializer(obj).data
        days.append(data)

        day_calories = data.get('total_calories', 0) or 0
        total_cal += day_calories

        # Count goal days: did the user meet ALL macro + calorie goals this day?
        # If no goals are set, goal_days stays 0.
        if goals and goals.calories_goal:
            met_calories = day_calories >= goals.calories_goal
            met_protein = (data.get('total_protein', 0) or 0) >= (goals.protein_goal or 0)
            met_carbs = (data.get('total_carbs', 0) or 0) >= (goals.carbs_goal or 0)
            met_fat = (data.get('total_fat', 0) or 0) >= (goals.fat_goal or 0)

            if met_calories and met_protein and met_carbs and met_fat:
                goal_days += 1

    avg_daily = total_cal / 7

    return Response({
        "start": str(start),
        "days": days,
        "weekly_calories": round(total_cal, 1),
        "avg_daily": round(avg_daily, 1),
        "total_cal": round(total_cal, 1),
        "goal_days": goal_days,
    })
