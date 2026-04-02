from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.UploadDocumentView.as_view(), name='upload'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/stream/', views.ChatStreamView.as_view(), name='chat_stream'),
    path('chat/memory/clear/', views.ClearSessionMemoryView.as_view(), name='clear_session_memory'),
    path('status/', views.StatusView.as_view(), name='status'),
    path('clear/', views.ClearVectorStoreView.as_view(), name='clear'),
    path('documents/delete/', views.DeleteDocumentByFilenameView.as_view(), name='delete_document_by_filename'),
    path('chunk-strategy/evaluate/', views.ChunkStrategyEvaluationView.as_view(), name='chunk_strategy_evaluate'),
    path('retrieval/benchmark/', views.RetrievalBenchmarkView.as_view(), name='retrieval_benchmark'),
    path('self-rag/calibrate/', views.SelfRAGCalibrationView.as_view(), name='self_rag_calibrate'),
]
