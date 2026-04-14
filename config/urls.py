from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('sales/', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('finance/', include('finance.urls')),
    path('', home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')