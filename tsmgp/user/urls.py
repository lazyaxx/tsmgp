# myapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_before, name='login_before'),
    path('base/', views.base, name='base'),
    path('login/', views.login_view, name='login'),
    path('home/', views.home_view, name='home'),
    path('login_register/', views.login_register_view, name='login_register'),
    path('register/', views.register_view, name='register'),
    path('citizen_home/', views.citizen_home, name='citizen_home'),
    path('update_user_roles/', views.update_user_roles, name='update_user_roles'),
    path('admin_home/', views.admin_home, name='admin_home'),
    path('government_monitors/', views.government_monitors, name='government_monitors'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/',views.dashboard, name='dashboard'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path("add-complaint/", views.add_complaint, name="add_complaint"),
    path("remove-complaint/", views.remove_complaint, name="remove_complaint"),
    path('village_info/<int:user_id>/', views.view_village_info, name='view_village_info'),
]



# Add this to your project's urls.py
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('myapp.urls')),
# ]