from django.urls import path
from . import views

urlpatterns = [
    path("", views.chat_page),
    path("login/", views.login_view),
    path("signup/", views.signup_view),
    path("logout/", views.logout_view),
    path("send/", views.send_message),
    path("history/<int:session_id>/", views.chat_history),
    path("session/create/", views.create_session),
    path("sessions/", views.list_sessions),
    path("delete/<int:session_id>/", views.delete_session),
    path("delete_account/", views.delete_account),
    path("upload_pdf/", views.upload_pdf),
]