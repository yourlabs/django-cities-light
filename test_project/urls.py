from django.contrib import admin
from django.urls import path, include

urlpatterns = [
  path('admin/', admin.site.urls),
  path('cities_light/api/', include('cities_light.contrib.restframework3')),
]
