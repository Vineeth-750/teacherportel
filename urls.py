from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.teacher_login, name='teacher_login'),
    path('register/', views.teacher_register, name='teacher_register'),
    path('logout/', views.logout, name='logout'),

    # Dashboard and Student Management
    path('dashboard/', views.handle_student_list, name='handle_student_list'),
    path('add/', views.add_student, name='add_student'),
    path('edit/<int:student_id>/', views.update_student, name='edit_mark'),
    path('delete/<int:student_id>/', views.delete_student, name='delete_student'),
]

