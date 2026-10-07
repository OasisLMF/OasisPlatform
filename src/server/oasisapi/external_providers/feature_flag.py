from django.conf import settings


def is_enabled() -> bool:
    return bool(getattr(settings, 'EXTERNAL_PROVIDERS_ENABLED', False))
