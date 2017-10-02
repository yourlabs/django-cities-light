import django

from django.contrib import admin

try:
    from django.urls import path
except ImportError:
    from django.conf.urls import include, url
    urlpatterns = [
        url(r'^admin/', include(admin.site.urls)),
    ]
else:
    urlpatterns = [
        path('admin/', admin.site.urls),
    ]
