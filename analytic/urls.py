from django.urls import path

from . import views


app_name = "analytic"

urlpatterns = [
    path("", views.index, name="index"),
]
