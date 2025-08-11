from django.urls import path
from .views import QuestionListCreateView, QuestionRetrieveUpdateDestroyView

urlpatterns = [
    path('', QuestionListCreateView.as_view(), name="question-list-create"),
    path('<int:pk>', QuestionRetrieveUpdateDestroyView.as_view(), name='question-details')
]
