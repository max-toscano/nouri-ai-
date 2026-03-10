from django.apps import AppConfig


class WorkoutQuizConfig(AppConfig):
    # Tells Django this folder is an app named "workout_quiz"
    default_auto_field = "django.db.models.BigAutoField"
    name = "workout_quiz"
    verbose_name = "Workout Quiz"
