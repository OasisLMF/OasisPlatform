from django.conf import settings
from django.db import models


class KeycloakUserId(models.Model):
    """
    This model is used to persist a Keycloak user id (uuid) and helps us verify our django user still represents
    the user in Keycloak it once was created for. I changed Keycloak user id would tell us that the user in
    Keycloak with this username has been replaced by a new account.
    """
    # Django user
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE)

    # Keycloak user ID (uuid)
    keycloak_user_id = models.CharField(max_length=100, default='')
