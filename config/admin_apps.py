from django.contrib.admin.apps import AdminConfig


class BCUAdminConfig(AdminConfig):
    default_site = "shop.admin_site.BCUAdminSite"
