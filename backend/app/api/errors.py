"""Uniform API error envelope and exception translation.

Every non-2xx response body is the frozen ``ApiError`` contract
(``docs/API_CONTRACT.md``). API code raises ``ApiException`` with a stable
``error_code``; ``install_error_handlers`` translates it — plus the known
repository/data-layer error types and anything unexpected — into the
envelope. Error bodies never echo request payloads, stack traces, prompts,
or credentials.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts import ApiError, CaseStatus
from app.data.errors import FixtureNotFoundError, SourceNotFoundError
from app.repositories.errors import CaseNotFoundError


class ApiException(Exception):
    """Raised anywhere in the API layer to produce a contract-shaped error."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        *,
        detail: str | None = None,
        case_id: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error = ApiError(
            error_code=error_code, message=message, detail=detail, case_id=case_id
        )


# --- Factories for the documented error codes ------------------------------


def case_not_found(case_id: str) -> ApiException:
    return ApiException(
        404,
        "case_not_found",
        f"No case exists with case_id '{case_id}'.",
        case_id=case_id,
    )


def fixture_not_found(fixture_id: str) -> ApiException:
    return ApiException(
        404,
        "fixture_not_found",
        f"No synthetic fixture is registered under fixture_id '{fixture_id}'.",
        detail="Known fixtures: 'lumbar_mri_prior_auth' and 'abridge:<record_id>'.",
    )


def source_not_found(case_id: str, source_id: str) -> ApiException:
    return ApiException(
        404,
        "source_not_found",
        f"No evidence source '{source_id}' is resolvable for this case.",
        case_id=case_id,
    )


def question_not_found(case_id: str, question_id: str) -> ApiException:
    return ApiException(
        404,
        "question_not_found",
        f"No clarification question '{question_id}' exists on this case.",
        case_id=case_id,
    )


def question_already_answered(case_id: str, question_id: str) -> ApiException:
    return ApiException(
        409,
        "question_already_answered",
        f"Clarification question '{question_id}' has already been answered.",
        detail="Each question is answered at most once; refetch the case to see the recorded answer.",
        case_id=case_id,
    )


def invalid_state_transition(
    case_id: str, current: CaseStatus, operation: str, required: str
) -> ApiException:
    return ApiException(
        409,
        "invalid_state_transition",
        f"Cannot {operation} while the case is in status '{current.value}'.",
        detail=f"This operation requires status {required}.",
        case_id=case_id,
    )


def packet_not_verified(case_id: str, current: CaseStatus) -> ApiException:
    return ApiException(
        409,
        "packet_not_verified",
        "Cannot draft the payer form until the packet has passed verification.",
        detail=(
            f"Case status is '{current.value}'; form drafting requires status "
            "'verified' with a stored passing verification result."
        ),
        case_id=case_id,
    )


# --- Handler installation --------------------------------------------------


def _error_response(status_code: int, error: ApiError) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api_exception(request: Request, exc: ApiException) -> JSONResponse:
        return _error_response(exc.status_code, exc.error)

    @app.exception_handler(CaseNotFoundError)
    async def _repo_case_not_found(
        request: Request, exc: CaseNotFoundError
    ) -> JSONResponse:
        wrapped = case_not_found(exc.case_id)
        return _error_response(wrapped.status_code, wrapped.error)

    @app.exception_handler(FixtureNotFoundError)
    async def _data_fixture_not_found(
        request: Request, exc: FixtureNotFoundError
    ) -> JSONResponse:
        return _error_response(
            404,
            ApiError(error_code="fixture_not_found", message=str(exc)),
        )

    @app.exception_handler(SourceNotFoundError)
    async def _data_source_not_found(
        request: Request, exc: SourceNotFoundError
    ) -> JSONResponse:
        return _error_response(
            404,
            ApiError(error_code="source_not_found", message=str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field locations and messages only — never the submitted values.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', []))}: {error.get('msg', 'invalid')}"
            for error in exc.errors()
        )
        return _error_response(
            422,
            ApiError(
                error_code="validation_error",
                message="Request body failed contract validation.",
                detail=problems or None,
            ),
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(
            500,
            ApiError(
                error_code="internal_error",
                message="Unexpected server error. The case state was not changed.",
            ),
        )
