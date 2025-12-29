from django.db import models

class FuelStation(models.Model):
    
    truckstop_id = models.IntegerField()
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['retail_price']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

class RouteCache(models.Model):
    
    start_location = models.CharField(max_length=200)
    end_location = models.CharField(max_length=200)
    route_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['start_location', 'end_location']
        indexes = [
            models.Index(fields=['start_location', 'end_location']),
        ]
    
    def __str__(self):
        return f"{self.start_location} to {self.end_location}"