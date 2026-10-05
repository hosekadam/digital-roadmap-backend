import typing as t

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from roadmap.common import decode_header
from roadmap.common import get_allowed_host_groups
from roadmap.common import query_host_inventory_by_ids
from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import HostIdsRequest
from roadmap.v1.lifecycle.rhel import relevant_systems
from roadmap.v1.lifecycle.rhel import RelevantSystemsResponse


router = APIRouter(
    prefix="/relevant/lifecycle/rhel",
    tags=["Relevant", "RHEL"],
)


@router.post(
    "/hosts",
    summary="RHEL lifecycle dates for a specified list of hosts",
    response_model=RelevantSystemsResponse,
)
async def get_relevant_rhel_for_hosts(
    body: HostIdsRequest,
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    host_groups: t.Annotated[set[str | None], Depends(get_allowed_host_groups)],
    related: bool = False,
):
    """Return RHEL lifecycle data for the given hosts.

    Same payload as the v1 relevant RHEL endpoint. The inventory query is
    limited to these ids and to the groups this caller may read. Ids the
    caller cannot read are omitted. Only the OS version and installed products
    are read; package columns are not.
    """
    systems = await query_host_inventory_by_ids(
        org_id=org_id,
        session=session,
        settings=settings,
        host_groups=host_groups,
        host_ids=body.host_ids,
        include_packages=False,
    )
    return await relevant_systems(org_id, systems, related)
