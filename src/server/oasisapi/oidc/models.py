from django.conf import settings
from django.db import models


class OIDCUserId(models.Model):
    """
    Persist the OIDC subject claim (`sub`) for a Django user.

    Works with both Keycloak and Authentik (or any OIDC provider).
    """
    # Django user
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE)

    # The "sub" (subject) claim from the OIDC provider (Keycloak, Authentik, etc.)
    oidc_sub = models.CharField(max_length=100, default='')

    def __str__(self):
        return f"{self.user.username} -> {self.oidc_sub}"
