from abc import ABC, abstractmethod
from io import IOBase
from typing import Literal, Optional


class ExposureProvider(ABC):
    @abstractmethod
    def get_token(self) -> str:
        """Return a valid bearer token, refreshing if necessary."""

    @abstractmethod
    def fetch_country(
        self,
        country_code: str,
        *,
        format: Literal['csv', 'parquet'] = 'csv',
        as_of: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> IOBase:
        """Stream OED exposure for an entire country. Returns a file-like object."""

    @abstractmethod
    def fetch_bbox(
        self,
        bbox: list,
        *,
        format: Literal['csv', 'parquet'] = 'csv',
        as_of: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> IOBase:
        """Stream OED exposure within a bounding box [min_lon, min_lat, max_lon, max_lat]."""

    @abstractmethod
    def lookup(
        self,
        locations_stream: IOBase,
        fields: list,
        *,
        input_format: Literal['csv', 'parquet'] = 'csv',
        output_format: Literal['csv', 'parquet'] = 'csv',
        match_radius_m: Optional[float] = None,
    ) -> IOBase:
        """
        Per-point attribute lookup.

        Input: OED locations stream (minimum columns: LocNumber, Latitude, Longitude).
        Output: same rows with provider-sourced fields filled.
        """
