from django.urls import path
from .views import QuizCreateView, QuizListView, QuizDetailView, QuizUpdateView, QuizQuestionUpdateView,\
    HostGameSessionView, CreatePlayerAccountView, CreateGuestPlayerView, GameSessionDetailView

urlpatterns = [
    path('', QuizListView.as_view(), name='list_quiz'),
    path('create', QuizCreateView.as_view(), name='create-quiz'),
    path("<int:pk>", QuizDetailView.as_view(), name="quiz-detail"),
    path('update/<int:quiz_id>', QuizUpdateView.as_view(), name='quiz-update'),
    path('<int:quiz_id>/update_questions', QuizQuestionUpdateView.as_view(), name='quiz-update-questions'),
    path('<int:quiz_id>/game-session', HostGameSessionView.as_view(), name='create-game-session'),
    path('players/create-account/', CreatePlayerAccountView.as_view(), name='create-player-account'),
    path('players/create-guest/', CreateGuestPlayerView.as_view(), name='create-guest-player'),
    path('game-session/<str:pin>', GameSessionDetailView.as_view(), name='game-session-detail')
]
