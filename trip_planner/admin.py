from django.contrib import admin
from .models import FuelStation, RouteCache

@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'retail_price')
    list_filter = ('state',)
    search_fields = ('name', 'city', 'address')
    ordering = ('retail_price',)

@admin.register(RouteCache)
class RouteCacheAdmin(admin.ModelAdmin):
    list_display = ('start_location', 'end_location', 'created_at')
    search_fields = ('start_location', 'end_location')
    readonly_fields = ('created_at',)