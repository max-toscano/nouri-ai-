"""
General Recommendations Module (stub)

Future home of AI-powered general workout and diet recommendations
based on the user's tracked data (meals, body stats, daily goals).

Not yet implemented — will be built out after the workout quiz is complete.
"""
from ..engine import AIEngine


SYSTEM_PROMPT = """\
You are a certified personal trainer and registered dietitian.
Given the user's body stats, daily nutrition data, and fitness goals,
provide short, actionable recommendations to help them stay on track.

Keep recommendations specific, practical, and encouraging.
Limit your response to 3-5 bullet points.

Return valid JSON:
{
  "recommendations": [
    {
      "category": "workout" | "diet" | "recovery" | "hydration",
      "title": "Short title",
      "detail": "1-2 sentence recommendation"
    }
  ]
}

Return ONLY the JSON — no markdown fences, no extra text.
"""


def generate(body_stats=None, daily_summary=None, daily_goals=None):
    """
    Generate general workout/diet recommendations.

    TODO: Implement after workout quiz is complete.
    """
    raise NotImplementedError(
        "General recommendations module is not yet implemented."
    )
