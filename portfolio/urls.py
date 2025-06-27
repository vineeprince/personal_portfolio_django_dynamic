from django.urls import path
from . import views

urlpatterns = [
    path('', views.portfolio_view, name='portfolio'),
    path('upload-resume/', views.upload_resume_view, name='upload_resume'),
]