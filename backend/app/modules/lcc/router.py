from fastapi import APIRouter

from app.modules.auth.dependencies import CurrentUser
from app.modules.lcc.dependencies import LccServiceDep
from app.modules.lcc.schemas import LccAnalysisOut, LccAnalyzeRequest
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/lcc", tags=["leaf-colour-chart"])


@router.post("/analyze", response_model=SuccessResponse[LccAnalysisOut])
async def analyze_lcc(payload: LccAnalyzeRequest, user: CurrentUser, service: LccServiceDep):
    """Estimate an LCC panel using local colour math; never calls an AI provider."""
    return success(await service.analyze(user, payload), message="LCC screening complete")
