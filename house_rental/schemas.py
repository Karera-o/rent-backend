from ninja import Schema

# Common response schemas that can be used across multiple apps
class MessageResponse(Schema):
    message: str

class ErrorResponse(Schema):
    error: str
    detail: str = None

class PaginatedResponse(Schema):
    total: int
    page: int
    page_size: int
    total_pages: int