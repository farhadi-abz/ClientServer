"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from ticketing.views import (
    CustomAuthToken,
    SubmitTicketAPI,
    OrganizationalChartAPI,
    UserTicketsListView,
    SendReplyAPIView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # اندپوینتی که کلاینت با آن لاگین می‌کند و توکن می‌گیرد:
    path("api/api-token-auth/", CustomAuthToken.as_view(), name="api_token_auth"),
    # اندپوینتی که کلاینت تیکت و سخت‌افزار را به آن ارسال می‌کند:
    path("api/tickets/", SubmitTicketAPI.as_view(), name="submit_ticket"),
    path("api/org-chart/", OrganizationalChartAPI.as_view(), name="org_chart"),
    path("api/my-tickets/", UserTicketsListView.as_view(), name="user_tickets_list"),
    path(
        "api/tickets/<int:ticket_id>/reply/",
        SendReplyAPIView.as_view(),
        name="send_reply",
    ),
]
