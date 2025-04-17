from fastapi import Request, Response, HTTPException, status
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from jose import jwt
from jose.exceptions import JWTError
import requests
from typing import List, Optional, Dict, Any, Callable
import re
import logging
import json
import time
import sys
import traceback
from functools import lru_cache
from jwcrypto import jwk

# Configure root logger to output to stderr
root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

# Import Clerk client
from ..core.clerk.client import clerk, get_user_by_id_async
from ..core.service.user_service import create_or_update_user_by_clerk_id
from ..core.db.database import async_get_db

# Import configuration
from ..core.config import settings

# JWKS configuration
# For Clerk, we need to use the instance-specific JWKS URL
CLERK_ISSUER = getattr(settings, "CLERK_JWT_ISSUER", "https://summary-tarpon-14.clerk.accounts.dev")
CLERK_AUDIENCE = getattr(settings, "CLERK_AUDIENCE", "http://localhost:3000")  # Frontend URL

@lru_cache(maxsize=1)
def get_jwks() -> Dict[str, Any]:
    """Fetch and cache the JWKS from Clerk
    
    This function is cached to avoid making repeated requests to the JWKS endpoint.
    The cache is valid for the lifetime of the application or until manually cleared.
    
    Returns:
        Dict[str, Any]: The JWKS response as a dictionary
        
    Raises:
        HTTPException: If the JWKS endpoint returns an error
    """
    # Use the instance-specific JWKS URL based on the issuer
    jwks_url = f"{CLERK_ISSUER}/.well-known/jwks.json"
    try:
        logging.info(f"Fetching JWKS from {jwks_url}")
        response = requests.get(jwks_url, timeout=5)  # Add timeout to prevent hanging
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"Timeout while fetching JWKS from {jwks_url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable"
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch JWKS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to authentication service: {str(e)}"
        )
    except ValueError as e:  # JSON parsing error
        logging.error(f"Invalid JWKS response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from authentication service"
        )

def get_jwk_kid(token: str) -> str:
    """Extract the key ID from the JWT header"""
    headers = jwt.get_unverified_header(token)
    return headers["kid"]

def get_public_key(kid: str) -> str:
    """Get the public key for the given key ID from the JWKS"""
    jwks = get_jwks()
    for key_dict in jwks["keys"]:
        if key_dict["kid"] == kid:
            key = jwk.JWK(**key_dict)
            return key.export_to_pem().decode()
    raise Exception(f"Public key not found for kid: {kid}")

def verify_clerk_token(token: str) -> Dict[str, Any]:
    """Verify a Clerk JWT token using JWKS"""
    try:
        kid = get_jwk_kid(token)
        public_key = get_public_key(kid)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=CLERK_AUDIENCE,
            issuer=CLERK_ISSUER
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Failed to validate token: {str(e)}")

class ClerkUser(BaseModel):
    """Clerk user data model
    
    This model represents the intermediate user data from Clerk's authentication service.
    It is used to create or update the database user (db_user) which is the primary user object
    used throughout the application. Both clerk_user and db_user are attached to the request state,
    but routes should generally use request.state.db_user for application logic.
    """
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Get the full name of the user"""
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or None


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests to specific routes using Clerk JWT.
    
    This middleware validates the JWT token for specified routes and attaches
    the authenticated user to the request state for use in route handlers.
    
    Parameters
    ----------
    app: FastAPI
        The FastAPI application instance.
    protected_paths: List[str], optional
        List of path patterns to protect with authentication.
        Defaults to ["/api/v1/user/me"].
    exclude_paths: List[str], optional
        List of path patterns to exclude from authentication.
        Defaults to ["/api/v1/user/uuid/"].
        
    Attributes
    ----------
    protected_paths: List[str]
        List of path patterns to protect with authentication.
    exclude_paths: List[str]
        List of path patterns to exclude from authentication.
    """
    
    def __init__(
        self, 
        app, 
        protected_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None
    ) -> None:
        super().__init__(app)

        # DO NOT CHANGE DEFAULT VALUES HERE, INSTEAD ADD NEW PATHS IN SETUP.PY
        self.protected_paths = protected_paths or ["/api/v1/user/me"]
        self.exclude_paths = exclude_paths or ["/api/v1/user/uuid/"]
        
        # Convert path patterns to regex for more flexible matching
        self.protected_regexes = [re.compile(pattern) for pattern in self.protected_paths]
        self.exclude_regexes = [re.compile(pattern) for pattern in self.exclude_paths]
    
    def is_path_protected(self, path: str) -> bool:
        """Check if the path should be protected by authentication."""
        # First check if path is in excluded paths
        for pattern in self.exclude_regexes:
            if pattern.match(path):
                logging.info(f"Path {path} is excluded from authentication by pattern {pattern.pattern}")
                return False
                
        # Then check if path is in protected paths
        for pattern in self.protected_regexes:
            if pattern.match(path):
                logging.info(f"Path {path} is protected by pattern {pattern.pattern}")
                return True
            else:
                logging.debug(f"Path {path} did not match protection pattern {pattern.pattern}")
                
        logging.info(f"Path {path} is not protected (no matching patterns)")
        return False
    
    async def _validate_token(self, token: str) -> dict:
        """Validate the JWT token and return the payload.
        
        Parameters
        ----------
        token: str
            The JWT token to validate.
            
        Returns
        -------
        dict
            The JWT payload.
            
        Raises
        ------
        HTTPException
            If the token is invalid.
        """
        # Verify the token using JWKS
        payload = verify_clerk_token(token)
        logging.info(f"JWT Payload: {payload}")
        
        # Validate required claims for user creation
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim"
            )
            
        return payload
    
    async def _get_user_data(self, user_id: str, payload: dict) -> dict:
        """Get user data from Clerk API or fallback to JWT payload.
        
        Parameters
        ----------
        user_id: str
            The user ID from the JWT token.
        payload: dict
            The JWT payload.
            
        Returns
        -------
        dict
            The user data.
        """
        try:
            # Fetch complete user data from Clerk API
            logging.info(f"Fetching user data from Clerk API for user_id: {user_id}")
            clerk_user_response = await get_user_by_id_async(user_id)
            
            # Log the complete clerk_user_response for debugging
            logging.info(f"Clerk API response: {clerk_user_response}")
            
            # Extract user data from Clerk API response
            user_data = {
                "id": user_id,
                "email": clerk_user_response.email,
                "first_name": clerk_user_response.first_name or "",
                "last_name": clerk_user_response.last_name or "",
                "profile_image_url": clerk_user_response.profile_image_url
            }
            logging.info(f"User data from Clerk API: {user_data}")
            return user_data
        except HTTPException as http_ex:
            # Handle HTTP exceptions from the Clerk client
            logging.warning(f"HTTP error from Clerk API: {http_ex.detail} (status: {http_ex.status_code})")
            if http_ex.status_code == 404:
                logging.warning(f"User {user_id} not found in Clerk. Using JWT payload instead.")
            else:
                logging.error(f"Unexpected HTTP error from Clerk API: {http_ex.detail}")
        except Exception as e:
            # Fallback to JWT payload if API call fails
            logging.warning(f"Failed to fetch user data from Clerk API: {str(e)}. Using JWT payload instead.")
        
        # Fallback to JWT payload
        first_name = payload.get("first_name", "")
        last_name = payload.get("last_name", "")
        
        user_data = {
            "id": user_id,
            "email": payload.get("email", ""),
            "first_name": first_name,
            "last_name": last_name,
            "profile_image_url": payload.get("image_url")
        }
        return user_data
    
    async def _create_clerk_user(self, user_data: dict) -> ClerkUser:
        """Create a ClerkUser instance from user data.
        
        Parameters
        ----------
        user_data: dict
            The user data.
            
        Returns
        -------
        ClerkUser
            The ClerkUser instance.
            
        Raises
        ------
        HTTPException
            If the ClerkUser instance cannot be created.
        """
        try:
            clerk_user = ClerkUser(**user_data)
            logging.info(f"Successfully created ClerkUser object: {clerk_user}")
            return clerk_user
        except Exception as e:
            logging.error(f"Error creating ClerkUser object: {str(e)}")
            logging.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user object: {str(e)}"
            )
    
    async def _sync_user_with_database(self, clerk_user: ClerkUser, request: Request):
        """Sync the user with the database and store the db_user in request.state.
        
        This method creates or updates the database user based on the Clerk user data.
        The resulting db_user is the primary user object that should be used by routes
        for application logic, rather than the intermediate clerk_user.
        
        Parameters
        ----------
        clerk_user: ClerkUser
            The ClerkUser instance (intermediate representation).
        request: Request
            The request object to store the db_user in.
            
        Returns
        -------
        Any
            The database user object or None if there was an error.
        """
        try:
            # Get DB session
            db_generator = async_get_db()
            db = await anext(db_generator)
            
            # Create or update user in database using clerk_id
            logging.info(f"Creating or updating user in database with clerk_id: {clerk_user.id}")
            user_data = {
                "first_name": clerk_user.first_name,
                "last_name": clerk_user.last_name,
                "email": clerk_user.email,
                "profile_image_url": clerk_user.profile_image_url
            }
            
            # Use create_or_update_user_by_clerk_id to get a proper db user object
            db_user = await create_or_update_user_by_clerk_id(
                db=db,
                clerk_id=clerk_user.id,
                user_data=user_data
            )
            logging.info(f"User in database: {db_user}")
            
            # Store the db_user in request.state
            # This is the primary user object that should be used by routes
            request.state.db_user = db_user
            
            # Close DB session
            await db_generator.aclose()
            
            return db_user
        except Exception as e:
            logging.error(f"Error checking/updating user in database: {str(e)}")
            logging.error(traceback.format_exc())
            # Don't raise an exception here, continue with authentication
            return None
    
    async def _process_response(self, request: Request, call_next: RequestResponseEndpoint, start_time: float, request_id: str) -> Response:
        """Process the response and add timing information.
        
        Parameters
        ----------
        request: Request
            The incoming request.
        call_next: RequestResponseEndpoint
            The next middleware or route handler in the processing chain.
        start_time: float
            The start time of the request.
        request_id: str
            The unique request ID.
            
        Returns
        -------
        Response
            The response from the route handler.
            
        Raises
        ------
        HTTPException
            If there is an error processing the response.
        """
        try:
            response = await call_next(request)
            
            # Add timing information to response headers
            total_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(total_time)
            response.headers["X-Auth-Time"] = str(request.state.auth_time)
            logging.info(f"[{request_id}] Total request time: {total_time:.3f}s")
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            logging.error(f"[{request_id}] Error during request processing: {str(e)}")
            logging.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and validate JWT token for protected routes.
        
        Parameters
        ----------
        request: Request
            The incoming request.
        call_next: RequestResponseEndpoint
            The next middleware or route handler in the processing chain.
            
        Returns
        -------
        Response
            The response from the route handler.
            
        Raises
        ------
        HTTPException
            If authentication fails for a protected route.
        """
        # Generate a unique request ID for tracing
        request_id = f"req_{int(time.time() * 1000)}"
        request.state.request_id = request_id
        start_time = time.time()
        
        # Always allow OPTIONS requests (for CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Check if this path requires authentication
        if not self.is_path_protected(request.url.path):
            return await call_next(request)
            
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        
        # Log request info for debugging
        logging.info(f"Request path: {request.url.path}, method: {request.method}")
        logging.info(f"Authorization header: {auth_header}" if auth_header else "No Authorization header")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            logging.warning(f"Missing or invalid authorization header for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
            
        # Extract the token
        token = auth_header.split(" ")[1]
        
        try:
            # Validate the token
            payload = await self._validate_token(token)
            
            # Get the user ID from the token
            user_id = payload.get("sub")
            
            # Get user data from Clerk API or fallback to JWT payload
            user_data = await self._get_user_data(user_id, payload)
            
            # Create ClerkUser instance (intermediate representation from Clerk)
            clerk_user = await self._create_clerk_user(user_data)
            request.state.clerk_user = clerk_user
            
            # Sync user with database and store db_user in request.state
            # db_user is the primary user object that should be used by routes
            db_user = await self._sync_user_with_database(clerk_user, request)
            
            # If db_user is None, log a warning but continue
            if db_user is None:
                logging.warning("Could not sync user with database, continuing with authentication")
            
            # Add request timing information
            request.state.auth_time = time.time() - start_time
            logging.info(f"[{request_id}] Authentication completed in {request.state.auth_time:.3f}s")
            
            # Process the response
            return await self._process_response(request, call_next, start_time, request_id)
            
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            # Catch any other exceptions
            logging.error(f"[{request_id}] Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
