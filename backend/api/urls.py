from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.UploadDocumentView.as_view(), name='upload'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/memory/clear/', views.ClearSessionMemoryView.as_view(), name='clear_session_memory'),
    path('status/', views.StatusView.as_view(), name='status'),
    path('clear/', views.ClearVectorStoreView.as_view(), name='clear'),
    path('chunk-strategy/evaluate/', views.ChunkStrategyEvaluationView.as_view(), name='chunk_strategy_evaluate'),
]
