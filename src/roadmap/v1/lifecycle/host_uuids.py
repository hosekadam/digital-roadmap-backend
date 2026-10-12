import logging
import typing as t

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncResult

from roadmap.common import query_accessible_host_uuids
from roadmap.models import Meta


logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/lifecycle",
    tags=["Lifecycle"],
)


class AccessibleHostUuidsResponse(BaseModel):
    """Host UUIDs the caller is permitted to read from host inventory."""

    meta: Meta
    data: list[UUID]


@router.get(
    "/host-uuids",
    summary="Host UUIDs the caller is permitted to read",
    response_model=AccessibleHostUuidsResponse,
)
async def get_accessible_host_uuids(
    hosts: t.Annotated[AsyncResult[t.Any], Depends(query_accessible_host_uuids)],
) -> AccessibleHostUuidsResponse:
    """Return every host UUID this user can access.

    Authorization happens in the inventory dependency: RBAC or Kessel decides
    which host groups are visible, and dev mode skips that remote check.
    The query itself only reads host ids.
    """
    logger.info("Listing accessible host UUIDs")

    # The stream yields one row per host, and each row is just the id.
    uuids = [row["id"] async for row in hosts.mappings()]
    return AccessibleHostUuidsResponse(meta=Meta(count=len(uuids), total=len(uuids)), data=uuids)
