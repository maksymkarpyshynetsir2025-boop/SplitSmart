from fastapi import APIRouter

from app.api.v1.groups import router as groups_router
from app.api.v1.invitations import router as invitations_router

router = APIRouter()
router.include_router(groups_router)
router.include_router(invitations_router)
