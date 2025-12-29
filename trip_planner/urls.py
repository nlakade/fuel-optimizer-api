from django.urls import path
from . import views

urlpatterns = [
    path('plan-trip/', views.CompleteTripAPI.as_view(), name='plan_trip'),
    path('plan-complete/', views.CompleteTripAPI.as_view(), name='plan_complete'),
    path('fuel-stations/', views.FuelStationAPI.as_view(), name='fuel_stations'),
    path('health/', views.HealthCheck.as_view(), name='health_check'),
    
    
]