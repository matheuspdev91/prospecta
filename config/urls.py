"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path
from leads.views import( 
    dashboard,cadastrar_lead_view, 
    listar_leads, 
    atualizar_status_lead_view,
    relatorios,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("leads/cadastrar/", cadastrar_lead_view, name="cadastrar_lead"),
    path("leads/", listar_leads, name ="listar_leads"),
    path(
        "leads/<int:lead_id>/status/",
        atualizar_status_lead_view,
        name="atualizar_status_lead",
    ),
    path("relatorios/", relatorios, name="relatorios"),
]
