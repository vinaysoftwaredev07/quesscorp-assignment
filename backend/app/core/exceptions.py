class AppException(Exception):
    def __init__(self, status_code: int, message: str, details: dict | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(status_code=404, message=message, details=details)


class ConflictException(AppException):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(status_code=409, message=message, details=details)


class BadRequestException(AppException):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(status_code=400, message=message, details=details)
