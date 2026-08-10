"""
URL configuration for newcell project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static

from .views import index_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('newcell.apps.expression.urls')),
    path('api/', include('newcell.apps.records.urls')),
    path('api/', include('newcell.apps.physio.urls')),
    # SPA 兜底：非 api/media/static/admin 的路径都返回前端入口（支持 vue-router history 刷新）
    re_path(r'^(?!admin/|api/|media/|static/).*$', index_view, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
