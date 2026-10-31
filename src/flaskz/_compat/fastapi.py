try:
    from starlette.requests import Request

    FASTAPI_AVAILABLE = True

except ImportError:
    Request = None
    FASTAPI_AVAILABLE = False
