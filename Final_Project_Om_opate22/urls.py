from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Web Routes (for traditional views)
    path('accounts/', include('accounts.urls')),
    path('dishes/', include('dishes.urls')),
    path('swipes/', include('swipes.urls')),
    path('community/', include('community.urls')),
    path('search/', include('search.urls')),           # ← ADD THIS
    path('recommender/', include('recommender.urls')), # ← ADD THIS

    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Swipe&Bite Administration"
admin.site.site_title = "Swipe&Bite Admin Portal"
admin.site.index_title = "Welcome to Swipe&Bite Admin"