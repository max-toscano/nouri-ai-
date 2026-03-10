from django.urls import path, include

urlpatterns = [
    path('api/', include('api.urls')),
    path('api/quiz/', include('workout_quiz.urls')),   # Workout quiz sections
]
