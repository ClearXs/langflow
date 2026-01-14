import os

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

import base64
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.connector import Connector, ConnectorType
from langflow.services.database.models.user import User
from langflow.services.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
# Use getattr with default to avoid errors when config is not set
REDIRECT_URI = getattr(settings, "GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:7860/api/v1/connector/google-calendar/callback")


def get_google_flow():
    try:
        # Use getattr with defaults for optional OAuth settings
        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
        client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)

        if not client_id or not client_secret:
            raise ValueError("Google OAuth credentials not configured")

        return Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create Google flow: {e!s}"
        ) from e


@router.get("/auth/google/calendar/connector/add")
async def connect_calendar(space_id: int, current_user: CurrentActiveUser):
    try:
        if not space_id:
            raise HTTPException(status_code=400, detail="space_id is required")

        flow = get_google_flow()

        # Encode space_id and user_id in state
        state_payload = json.dumps(
            {
                "space_id": space_id,
                "user_id": str(current_user.id),
            }
        )
        state_encoded = base64.urlsafe_b64encode(state_payload.encode()).decode()

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
            state=state_encoded,
        )
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate Google OAuth: {e!s}"
        ) from e


@router.get("/auth/google/calendar/connector/callback")
async def calendar_callback(
    request: Request,
    code: str,
    state: str,
    db: DbSession = None,
):
    try:
        # Decode and parse the state
        decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
        data = json.loads(decoded_state)

        user_id = UUID(data["user_id"])
        space_id = data["space_id"]

        flow = get_google_flow()
        flow.fetch_token(code=code)

        creds = flow.credentials
        creds_dict = json.loads(creds.to_json())

        try:
            # Check if a connector with the same type already exists for this search space and user
            result = await db.execute(
                select(Connector).filter(
                    Connector.search_space_id == space_id,
                    Connector.user_id == user_id,
                    Connector.connector_type
                    == ConnectorType.GOOGLE_CALENDAR_CONNECTOR,
                )
            )
            existing_connector = result.scalars().first()
            if existing_connector:
                raise HTTPException(
                    status_code=409,
                    detail="A GOOGLE_CALENDAR_CONNECTOR connector already exists in this search space. Each search space can have only one connector of each type per user.",
                )
            db_connector = Connector(
                name="Google Calendar Connector",
                connector_type=ConnectorType.GOOGLE_CALENDAR_CONNECTOR,
                config=creds_dict,
                search_space_id=space_id,
                user_id=user_id,
                is_indexable=True,
            )
            db.add(db_connector)
            await db.commit()
            await db.refresh(db_connector)
            return RedirectResponse(
                f"{settings.NEXT_FRONTEND_URL}/dashboard/{space_id}/connectors/add/google-calendar-connector?success=true"
            )
        except ValidationError as e:
            await db.rollback()
            raise HTTPException(
                status_code=422, detail=f"Validation error: {e!s}"
            ) from e
        except IntegrityError as e:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Integrity error: A connector with this type already exists. {e!s}",
            ) from e
        except HTTPException:
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to create connector: {e!s}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create connector: {e!s}",
            ) from e

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to complete Google OAuth: {e!s}"
        ) from e
