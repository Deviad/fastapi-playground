from enum import Enum, auto

from typing import Dict, Any


class DomainErrorType(Enum):
    """Types of domain errors following DDD principles"""
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    DOMAIN_VALIDATION = "DOMAIN_VALIDATION"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"

class DomainError(Enum):
    """Domain errors with their type and HTTP mapping"""

    # Entity Not Found Errors
    USER_NOT_FOUND = (DomainErrorType.ENTITY_NOT_FOUND, 404)
    COURSE_NOT_FOUND = (DomainErrorType.ENTITY_NOT_FOUND, 404)
    ORDER_NOT_FOUND = (DomainErrorType.ENTITY_NOT_FOUND, 404)
    PRODUCT_NOT_FOUND = (DomainErrorType.ENTITY_NOT_FOUND, 404)
    ENROLLMENT_NOTFOUND = (DomainErrorType.ENTITY_NOT_FOUND, 404)


    # Domain Validation Errors
    INVALID_ARGUMENT = (DomainErrorType.DOMAIN_VALIDATION, 400)
    INVALID_EMAIL_FORMAT = (DomainErrorType.DOMAIN_VALIDATION, 400)
    INVALID_PASSWORD_FORMAT = (DomainErrorType.DOMAIN_VALIDATION, 400)
    INVALID_ENTITY_STATE = (DomainErrorType.DOMAIN_VALIDATION, 400)

    # Business Rule Violations
    INSUFFICIENT_PERMISSIONS = (DomainErrorType.BUSINESS_RULE_VIOLATION, 403)
    COURSE_ENROLLMENT_LIMIT_EXCEEDED = (DomainErrorType.BUSINESS_RULE_VIOLATION, 409)
    DUPLICATE_ENROLLMENT_ATTEMPT = (DomainErrorType.BUSINESS_RULE_VIOLATION, 409)
    PAYMENT_PROCESSING_FAILED = (DomainErrorType.BUSINESS_RULE_VIOLATION, 402)
    BUSINESS_INVARIANT_VIOLATED = (DomainErrorType.BUSINESS_RULE_VIOLATION, 422)

    # Infrastructure Errors
    REPOSITORY_ACCESS_FAILED = (DomainErrorType.INFRASTRUCTURE, 500)
    EXTERNAL_SERVICE_UNAVAILABLE = (DomainErrorType.INFRASTRUCTURE, 503)
    DATABASE_CONNECTION_FAILED = (DomainErrorType.INFRASTRUCTURE, 500)

    def __init__(self, error_type: DomainErrorType, http_status: int):
        self.error_type = error_type
        self.http_status = http_status

    @property
    def code(self) -> str:
        """Returns the enum name as the error code"""
        return self.name

    def __str__(self):
        return self.code

class DomainException(Exception):
    """Domain exception following DDD principles"""

    def __init__(self,
                 domain_error: DomainError,
                 message: str,
                 cause: Exception = None,
                 context: Dict[str, Any] = None):
        super().__init__(message)
        self.domain_error = domain_error
        self.message = message
        self.cause = cause
        self.context = context or {}

        # Domain error metadata from enum
        self.error_type = domain_error.error_type
        self.http_status = domain_error.http_status
        self.error_code = domain_error.code

    def __str__(self):
        base = f"[{self.error_code}] {self.message}"
        if self.cause:
            base += f" | Caused by: {str(self.cause)}"
        return base

    @property
    def is_entity_not_found(self) -> bool:
        return self.error_type == DomainErrorType.ENTITY_NOT_FOUND

    @property
    def is_business_rule_violation(self) -> bool:
        return self.error_type == DomainErrorType.BUSINESS_RULE_VIOLATION

    @property
    def is_validation_error(self) -> bool:
        return self.error_type == DomainErrorType.DOMAIN_VALIDATION

    @property
    def is_infrastructure_error(self) -> bool:
        return self.error_type == DomainErrorType.INFRASTRUCTURE