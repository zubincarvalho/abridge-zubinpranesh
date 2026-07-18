"""Typed errors for the data layer.

Every loader failure raises a `DataError` subclass with an actionable
message (which file, which record, which id) so intake failures surface as
useful diagnostics instead of bare KeyErrors.
"""


class DataError(Exception):
    """Base class for all data-layer errors."""


class DatasetNotFoundError(DataError):
    """A dataset or fixture file/directory does not exist on disk."""


class MalformedDataError(DataError):
    """A file exists but its content cannot be parsed or is structurally invalid."""


class DuplicateIdError(DataError):
    """Two records or resources carry the same id where uniqueness is required."""


class UnresolvedReferenceError(DataError):
    """A FHIR reference does not resolve to any indexed resource."""


class FixtureNotFoundError(DataError):
    """No fixture is registered under the requested fixture_id."""


class SourceNotFoundError(DataError):
    """No evidence source exists for the requested source_id."""
