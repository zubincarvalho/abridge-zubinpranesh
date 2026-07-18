"""Repository errors (the port specifies raising; these are the types)."""


class CaseRepositoryError(Exception):
    """Base class for case-repository errors."""

    def __init__(self, case_id: str, message: str):
        self.case_id = case_id
        super().__init__(message)


class CaseNotFoundError(CaseRepositoryError):
    def __init__(self, case_id: str):
        super().__init__(case_id, f"no case with case_id {case_id!r}")


class CaseAlreadyExistsError(CaseRepositoryError):
    def __init__(self, case_id: str):
        super().__init__(case_id, f"case {case_id!r} already exists")
