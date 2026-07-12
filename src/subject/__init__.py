"""v1.1 Subject Declaration parsing, validation and provenance."""
from .declaration import SubjectDeclarationError, load_declaration, normalize_declaration, resolve_declarations, subject_ref

__all__ = ["SubjectDeclarationError", "load_declaration", "normalize_declaration", "resolve_declarations", "subject_ref"]
