from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from labshare import views

urlpatterns = [
    path('admin/', include(admin.site.urls[:2], namespace=admin.site.urls[-1])),
    path('', views.index, name="index"),
    path('reserve', views.reserve, name="reserve"),
    path('message', views.send_message, name="send_message"),
    path('gpus', views.gpus, name="gpus_for_device"),
    path('gpu/<int:gpu_id>/done', views.gpu_done, name="done_with_gpu"),
    path('gpu/<int:gpu_id>/cancel', views.gpu_cancel, name="cancel_gpu"),
    path('gpu/<int:gpu_id>/extend', views.gpu_extend, name="extend_gpu"),
    path('gpu/info', views.gpu_info, name="gpu_info"),

    path('accounts/login', auth_views.LoginView.as_view(template_name='login.html')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html')),
    path('view-as', views.view_as, name="view_as"),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('', include('django.contrib.auth.urls')),
]
