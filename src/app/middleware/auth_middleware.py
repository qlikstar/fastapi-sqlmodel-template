from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import jwt
from typing import List, Optional
import re

from ..core.security import CLERK_PUBLIC_KEY, CLERK_JWT_ISSUER, ClerkUser


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
                return False
                
        # Then check if path is in protected paths
        for pattern in self.protected_regexes:
            if pattern.match(path):
                return True
                
        return False
    
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
        # Check if this path requires authentication
        if not self.is_path_protected(request.url.path):
            return await call_next(request)
            
        # Get the authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
            
        # Extract the token
        token = auth_header.split(" ")[1]
        
        try:
            # Verify the token using the local public key
            payload = jwt.decode(
                token,
                CLERK_PUBLIC_KEY,
                algorithms=["RS256"],
                audience="your-audience",  # TODO: Replace with your audience if needed
                issuer=CLERK_JWT_ISSUER,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["sub", "exp", "iat"]
                }
            )
            
            # Validate required claims for user creation
            if not payload.get("sub"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject claim"
                )
                
            if not payload.get("email"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing email claim"
                )
            
            # Extract user data from Clerk JWT
            user_data = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "username": payload.get("username"),
                "profile_image_url": payload.get("image_url")
            }
            
            # Create ClerkUser instance
            clerk_user = ClerkUser(**user_data)
            
            # Attach the user to the request state
            request.state.clerk_user = clerk_user
            
            # Continue with the request
            return await call_next(request)
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to validate token: {str(e)}"
            )
