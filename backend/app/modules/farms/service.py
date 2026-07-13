"""Farm service — business logic for farm registration and management.

API → Service → Repository (docs/BACKEND_ARCHITECTURE.md). Owns validation
(duplicate names, boundary geometry), area resolution (computed vs manual
override), and the assembly of a farm with its location, boundary and media.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.constants import AreaSource
from app.modules.farms.exceptions import (
    DuplicateFarmError,
    FarmNotFoundError,
    InvalidBoundaryError,
)
from app.modules.farms.geo import (
    InvalidPolygonError,
    centroid,
    extract_ring,
    geodesic_area_sqm,
    perimeter_m,
    sqm_to_hectares,
    validate_ring,
)
from app.modules.farms.models import Farm, FarmBoundary, FarmLocation, FarmMedia
from app.modules.farms.repositories import FarmMediaRepository, FarmRepository
from app.modules.farms.schemas import (
    BoundaryIn,
    FarmMediaCreate,
    FarmWrite,
    LocationIn,
)

logger = get_logger("farms.service")


class FarmService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.farms = FarmRepository(session)
        self.media = FarmMediaRepository(session)

    # ----- Queries -----
    async def list_farms(
        self,
        user: User,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        district: str | None = None,
        crop: str | None = None,
        search: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> tuple[list[Farm], int]:
        offset = (page - 1) * page_size
        items = await self.farms.list_for_user(
            user.id,
            limit=page_size,
            offset=offset,
            status=status,
            district=district,
            crop=crop,
            search=search,
            sort=sort,
            order=order,
        )
        total = await self.farms.count_for_user(
            user.id, status=status, district=district, crop=crop, search=search
        )
        return items, total

    async def get_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        return farm

    # ----- Commands -----
    async def create_farm(self, user: User, data: FarmWrite) -> Farm:
        if await self.farms.name_exists(user.id, data.name):
            raise DuplicateFarmError()

        farm = Farm(user_id=user.id, name=data.name.strip())
        self._apply_scalars(farm, data)
        self.session.add(farm)

        if data.location is not None:
            farm.location = self._build_location(data.location)
        if data.boundary is not None:
            farm.boundary = self._build_boundary(data.boundary)
        self._resolve_area(farm, data)

        await self.session.flush()
        logger.info("Farm created id=%s user=%s", farm.id, user.id)
        return await self.get_farm(user, farm.id)

    async def update_farm(
        self, user: User, farm_id: uuid.UUID, data: FarmWrite
    ) -> Farm:
        farm = await self.get_farm(user, farm_id)
        if await self.farms.name_exists(user.id, data.name, exclude_id=farm.id):
            raise DuplicateFarmError()

        farm.name = data.name.strip()
        self._apply_scalars(farm, data)

        if data.location is not None:
            if farm.location is None:
                farm.location = self._build_location(data.location)
            else:
                self._update_location(farm.location, data.location)
        if data.boundary is not None:
            if farm.boundary is None:
                farm.boundary = self._build_boundary(data.boundary)
            else:
                self._update_boundary(farm.boundary, data.boundary)
        self._resolve_area(farm, data)

        await self.session.flush()
        return await self.get_farm(user, farm.id)

    async def delete_farm(self, user: User, farm_id: uuid.UUID) -> None:
        farm = await self.get_farm(user, farm_id)
        farm.is_deleted = True
        farm.deleted_at = datetime.now(UTC)
        await self.session.flush()
        logger.info("Farm soft-deleted id=%s user=%s", farm_id, user.id)

    # ----- Boundary -----
    async def get_boundary(
        self, user: User, farm_id: uuid.UUID
    ) -> FarmBoundary | None:
        farm = await self.get_farm(user, farm_id)
        return farm.boundary

    async def update_boundary(
        self, user: User, farm_id: uuid.UUID, data: BoundaryIn
    ) -> FarmBoundary:
        farm = await self.get_farm(user, farm_id)
        if farm.boundary is None:
            farm.boundary = self._build_boundary(data)
        else:
            self._update_boundary(farm.boundary, data)
        # Drawing/replacing a boundary refreshes the computed area unless the
        # farmer has explicitly entered a manual area override.
        if farm.area_source == AreaSource.AUTO.value:
            farm.area_hectares = farm.boundary.area_hectares
        await self.session.flush()
        return farm.boundary

    # ----- Media -----
    async def list_images(self, user: User, farm_id: uuid.UUID) -> list[FarmMedia]:
        await self.get_farm(user, farm_id)  # ownership check
        return await self.media.list_for_farm(farm_id)

    async def add_image(
        self, user: User, farm_id: uuid.UUID, data: FarmMediaCreate
    ) -> FarmMedia:
        await self.get_farm(user, farm_id)
        return await self.media.add(
            FarmMedia(
                farm_id=farm_id,
                file_url=data.file_url,
                file_name=data.file_name,
                mime_type=data.mime_type,
                file_size=data.file_size,
                caption=data.caption,
                uploaded_by=user.id,
            )
        )

    # ----- Helpers -----
    def _apply_scalars(self, farm: Farm, data: FarmWrite) -> None:
        farm.crop = data.crop
        farm.crop_variety = data.crop_variety
        farm.sowing_date = data.sowing_date
        farm.soil_type = data.soil_type.value if data.soil_type else None
        farm.irrigation_type = (
            data.irrigation_type.value if data.irrigation_type else None
        )
        farm.water_source = data.water_source.value if data.water_source else None
        farm.notes = data.notes
        farm.status = data.status.value
        farm.area_source = data.area_source.value

    def _build_location(self, loc: LocationIn) -> FarmLocation:
        return FarmLocation(
            latitude=loc.latitude,
            longitude=loc.longitude,
            accuracy=loc.accuracy,
            elevation=loc.elevation,
            address=loc.address,
            district=loc.district,
            block=loc.block,
            village=loc.village,
            source=loc.source.value,
        )

    def _update_location(self, entity: FarmLocation, loc: LocationIn) -> None:
        entity.latitude = loc.latitude
        entity.longitude = loc.longitude
        entity.accuracy = loc.accuracy
        entity.elevation = loc.elevation
        entity.address = loc.address
        entity.district = loc.district
        entity.block = loc.block
        entity.village = loc.village
        entity.source = loc.source.value

    def _build_boundary(self, data: BoundaryIn) -> FarmBoundary:
        metrics = self._boundary_metrics(data.geojson)
        return FarmBoundary(geojson=data.geojson, source=data.source.value, **metrics)

    def _update_boundary(self, entity: FarmBoundary, data: BoundaryIn) -> None:
        metrics = self._boundary_metrics(data.geojson)
        entity.geojson = data.geojson
        entity.source = data.source.value
        entity.area_hectares = metrics["area_hectares"]
        entity.perimeter_m = metrics["perimeter_m"]
        entity.centroid_lat = metrics["centroid_lat"]
        entity.centroid_lng = metrics["centroid_lng"]
        entity.vertex_count = metrics["vertex_count"]

    def _boundary_metrics(self, geojson: dict) -> dict:
        try:
            ring = validate_ring(extract_ring(geojson))
        except InvalidPolygonError as exc:
            raise InvalidBoundaryError(str(exc)) from exc
        lat, lng = centroid(ring)
        return {
            "area_hectares": sqm_to_hectares(geodesic_area_sqm(ring)),
            "perimeter_m": perimeter_m(ring),
            "centroid_lat": lat,
            "centroid_lng": lng,
            "vertex_count": len(ring),
        }

    def _resolve_area(self, farm: Farm, data: FarmWrite) -> None:
        """Effective farm area: manual override wins, else computed boundary area."""
        if data.area_source == AreaSource.MANUAL:
            if data.area_hectares is not None:
                farm.area_hectares = data.area_hectares
            elif farm.boundary is not None:
                farm.area_hectares = farm.boundary.area_hectares
            return
        if farm.boundary is not None:
            farm.area_hectares = farm.boundary.area_hectares
        else:
            farm.area_hectares = data.area_hectares
