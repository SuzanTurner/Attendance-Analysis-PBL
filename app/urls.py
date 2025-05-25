from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view),
    path("cgpa/", views.cgpa),
    path("mail/", views.mail),
    path("error/", views.error)
]
