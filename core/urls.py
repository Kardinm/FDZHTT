from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("c/<slug:slug>/", views.channel_view, name="channel"),
    path("api/terms.json", views.terms_json, name="terms_json"),
    path("api/auth", views.api_auth, name="api_auth"),
    path("api/logout", views.api_logout, name="api_logout"),
    path("api/post/create", views.api_post_create, name="api_post_create"),
    path("api/post/<int:pk>/update", views.api_post_update, name="api_post_update"),
    path("api/post/<int:pk>/delete", views.api_post_delete, name="api_post_delete"),
    path("api/term/create", views.api_term_create, name="api_term_create"),
    path("api/term/<int:pk>/update", views.api_term_update, name="api_term_update"),
    path("api/term/<int:pk>/delete", views.api_term_delete, name="api_term_delete"),
    path("api/podsos/create", views.api_podsos_create, name="api_podsos_create"),
    path("api/podsos/<int:pk>/update", views.api_podsos_update, name="api_podsos_update"),
    path("api/podsos/<int:pk>/delete", views.api_podsos_delete, name="api_podsos_delete"),
    path("api/punishment/create", views.api_punishment_create, name="api_punishment_create"),
    path("api/punishment/<int:pk>/update", views.api_punishment_update, name="api_punishment_update"),
    path("api/punishment/<int:pk>/delete", views.api_punishment_delete, name="api_punishment_delete"),
    path("api/spin", views.api_spin, name="api_spin"),
    path("api/session/create", views.api_session_create, name="api_session_create"),
    path("api/session/<int:pk>/update", views.api_session_update, name="api_session_update"),
    path("api/session/<int:pk>/delete", views.api_session_delete, name="api_session_delete"),
    path("api/sentence/create", views.api_sentence_create, name="api_sentence_create"),
    path("api/sentence/<int:pk>/update", views.api_sentence_update, name="api_sentence_update"),
    path("api/sentence/<int:pk>/delete", views.api_sentence_delete, name="api_sentence_delete"),
]
