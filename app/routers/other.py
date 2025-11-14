"""
Router for other non-LLM services.

Future services can be added here:
- Authentication endpoints
- User management endpoints
- Database operations
- Analytics endpoints
- File processing endpoints

Example:
    from fastapi import APIRouter
    router = APIRouter(prefix="/api/other", tags=["Other Services"])

    @router.get("/example")
    async def example():
        return {"message": "Example endpoint"}
"""
