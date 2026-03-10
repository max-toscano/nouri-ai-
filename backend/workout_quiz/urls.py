# ──────────────────────────────────────────────────────────────────────────────
# urls.py  —  workout_quiz
#
# All quiz endpoints live under /api/quiz/.
#
# CURRENT
#   POST /api/quiz/submit/   ← combined endpoint (goal + training_availability)
#   POST /api/quiz/goal/     ← isolated goal section (dev/testing)
#
# ADDING A NEW SECTION
#   1. Build the serializer in serializers.py.
#   2. Add the field to QuizSerializer.
#   3. If you want an isolated endpoint for it, add a view + path() here.
#   4. The combined /submit/ endpoint automatically includes it — no URL change needed.
# ──────────────────────────────────────────────────────────────────────────────

from django.urls import path
from . import views

urlpatterns = [
    # ── Combined submit — all sections in one request ─────────────────────────
    path("submit/", views.submit_quiz, name="quiz-submit"),

    # ── Isolated section endpoints ────────────────────────────────────────────
    path("goal/", views.submit_goal, name="quiz-goal"),

    # Future isolated endpoints (uncomment as sections are built):
    # path("availability/", views.submit_availability, name="quiz-availability"),
    # path("experience/",   views.submit_experience,   name="quiz-experience"),
    # path("equipment/",    views.submit_equipment,    name="quiz-equipment"),
    # path("injuries/",     views.submit_injuries,     name="quiz-injuries"),
    # path("preferences/",  views.submit_preferences,  name="quiz-preferences"),
    # path("adherence/",    views.submit_adherence,    name="quiz-adherence"),
]
