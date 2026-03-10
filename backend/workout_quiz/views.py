# ──────────────────────────────────────────────────────────────────────────────
# views.py  —  workout_quiz
#
# ENDPOINTS
# ---------
# POST /api/quiz/submit/   ← full quiz submission (all 8 sections)
# POST /api/quiz/goal/     ← isolated goal section (dev / testing only)
#
# PIPELINE (submit_quiz)
# ----------------------
# 1. QuizSerializer validates the raw request body.
# 2. normalize_quiz_data() transforms validated_data into a UserWorkoutProfile.
# 3. The response returns both the validated data and the normalized profile.
#
# When OpenAI integration is added, step 3 becomes:
#   3. Pass normalized_profile to the AI service layer.
#   4. Receive generated workout plan.
#   5. Return the plan (and optionally store it).
# ──────────────────────────────────────────────────────────────────────────────

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import QuizSerializer, GoalSerializer
from .services import normalize_quiz_data


@api_view(["POST"])
def submit_quiz(request):
    """
    POST /api/quiz/submit/

    Accepts all 8 quiz sections, validates them, normalizes them into a
    UserWorkoutProfile, and returns both representations.

    Success response (200):
        {
            "status": "success",
            "data": {
                "normalized_profile": {
                    "goal": "lose_weight",
                    "goal_weight_delta_kg": -12,
                    "available_training_days": ["monday", "tuesday", "thursday", "saturday"],
                    "training_days_per_week": 4,
                    ...
                }
            }
        }

    Validation error response (400):
        {
            "training_availability": {
                "monday": { "end_time": ["end_time must be later than start_time."] }
            }
        }
    """
    serializer = QuizSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Transform validated data into the normalized profile.
    # The profile is a flat, derived object ready for the AI service layer.
    profile = normalize_quiz_data(serializer.validated_data)

    return Response(
        {
            "status": "success",
            "data": {
                "normalized_profile": profile.to_dict(),
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def submit_goal(request):
    """
    POST /api/quiz/goal/

    Standalone endpoint for the goal section only.
    Kept for isolated development and section-level testing.

    Request body:
        { "goal": "other", "goal_other_text": "Train for a marathon",
          "goal_details": { "current_weight_kg": 80 } }

    Success response (200):
        { "section": "goal", "data": { ... } }
    """
    serializer = GoalSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "section": "goal",
            "data": serializer.validated_data,
        },
        status=status.HTTP_200_OK,
    )
