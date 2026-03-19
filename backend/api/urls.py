from django.urls import path
from . import views

urlpatterns = [
    path("health/",                           views.health_check,     name="health-check"),
    path("foods/search/",                     views.food_search,      name="food-search"),
    path("foods/<str:source>/<str:food_id>/", views.food_details,     name="food-details"),
    path("body-stats/",                       views.body_stats,       name="body-stats"),
    path("daily-goals/",                      views.daily_goals,      name="daily-goals"),
    path("meals/today/",                      views.meals_today,      name="meals-today"),
    path("meals/",                            views.meals_create,     name="meals-create"),
    path("hydration/today/",                  views.hydration_today,  name="hydration-today"),
    path("hydration/",                        views.hydration_create, name="hydration-create"),

    # ── AI Workout Quiz ──
    path("workout/quiz/",                       views.workout_quiz_questions, name="workout-quiz"),
    path("workout/generate/",                   views.workout_quiz_submit,    name="workout-generate"),

    # ── Date-parameterized endpoints ──
    path("daily-summary/",                    views.daily_summary,    name="daily-summary"),
    path("meals/by-date/",                    views.meals_by_date,    name="meals-by-date"),
    path("hydration/by-date/",                views.hydration_by_date, name="hydration-by-date"),
    path("week-summary/",                     views.week_summary,     name="week-summary"),
]
