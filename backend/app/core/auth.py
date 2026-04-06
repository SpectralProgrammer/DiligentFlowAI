import logging
from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@lru_cache
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()
    if not settings.auth0_jwks_url:
        raise RuntimeError(
            "AUTH0_DOMAIN and AUTH0_AUDIENCE must be configured before protected API routes can be used."
        )
    return PyJWKClient(settings.auth0_jwks_url)


def verify_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.auth0_enabled or not settings.auth0_issuer or not settings.auth0_audience:
        raise RuntimeError(
            "AUTH0_DOMAIN and AUTH0_AUDIENCE must be configured before protected API routes can be used."
        )

    signing_key = get_jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.auth0_audience,
        issuer=settings.auth0_issuer,
    )


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return verify_access_token(credentials.credentials)
    except RuntimeError as exc:
        logger.exception("Auth0 verification is unavailable because backend configuration is incomplete.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyJWKClientConnectionError as exc:
        logger.exception("The backend could not reach the Auth0 JWKS endpoint.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The backend could not reach the Auth0 JWKS endpoint to validate the access token. "
                "Check internet access and confirm AUTH0_DOMAIN points to the correct tenant."
            ),
        ) from exc
    except PyJWKClientError as exc:
        logger.warning("Auth0 token validation failed before signature verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "The Auth0 access token could not be matched to a signing key. "
                "Verify AUTH0_DOMAIN and AUTH0_AUDIENCE match the same Auth0 tenant and API, "
                "and that the API is configured to use RS256."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Auth0 access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Auth0 access token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while validating the Auth0 access token.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The backend could not validate the Auth0 access token against the JWKS endpoint.",
        ) from exc
