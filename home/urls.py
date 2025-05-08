from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required 
from .views import custom_login_required 

urlpatterns = [
    # General Pages
    path('', views.index, name='index'),
    path('home/', views.home, name='home'), 
    path('about/', views.about, name='about'),
    path('admin_page/', views.admin, name='admin_page'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('team/', views.team, name='team'),
    path('service/', views.service, name='service'),
    path('terms_condition/', views.terms_condition, name='terms_condition'),
    path('sample/', views.sample, name='sample'),
    path('through/', views.through, name= 'through'), 
    path('user_login/', views.user_login, name= 'user_login'),
    # Authentication & Registration
    path('login/', views.user_login, name='login'), 
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'), # Main registration choice page
    path('register/student/', views.register_student, name='register_student'), # Student form page
    path('register/worker/', views.register_worker, name='register_worker'), # Worker form page
    path('insertstudent/', views.insertstudent, name='insertstudent'), # Handles student form submission
    path('insertworker/', views.insertworker, name='insertworker'), # Handles worker form submission
    path('api/change-password/', views.change_password, name='change_password'),

    # User Account & Profiles
    path('myaccount/', custom_login_required(views.myaccount), name='myaccount'),
    path('verify/<int:user_id>/<str:user_type>/', views.verify_user, name='verify_user'), 
    path('student_profile/', views.student_profile, name='student_profile'), # Display list of students
    path('worker_profile/', views.worker_profile, name='worker_profile'), # Display list of workers

    # Scanner Pages
    path('scanner/', views.scanner, name='scanner'), # Library Scanner Page
    path('scannerw/', views.scannerw, name='scannerw'), # Door Scanner Page

    # API Endpoints
    path('api/verify-user/', views.verify_user_api, name='verify_user_api'), # API for verifying user from QR data (used by both scanners)
    path('api/verify-qr/', views.verify_qr, name='verify_qr'), # Alternative/redundant API? Consolidate if possible.
    path('api/log-access/', views.log_access, name='log_access'), # API for Door Scanner logs
    path('api/checkout-book/', views.checkout_book, name='checkout_book'), # API for Library book checkout
    path('return_book/', views.return_books, name='return_book'),

    # Removed send_email path as it's a helper function called internally now
    path('api/send_email/', views.send_checkout_email, name='send_email'),
    path('api/send_access_email/', views.send_access_email, name='send_access_email'), # Not typically exposed directly
]