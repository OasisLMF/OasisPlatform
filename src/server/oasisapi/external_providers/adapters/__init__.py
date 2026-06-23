from .base import ExposureProvider
from .gxm import GXMAdapter

ADAPTER_REGISTRY = {
    'gxm': GXMAdapter,
}

SUPPORTED_PROVIDERS = frozenset(ADAPTER_REGISTRY)


def get_adapter(provider: str, provider_settings) -> ExposureProvider:
    cls = ADAPTER_REGISTRY.get(provider)
    if cls is None:
        raise ValueError(f'Unknown provider: {provider!r}')
    return cls(provider_settings)
