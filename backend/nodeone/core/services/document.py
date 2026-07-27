"""DocumentService — archivos adjuntos (Etapa 11 stub → core_attachment)."""

from __future__ import annotations


class DocumentServiceNotReadyError(NotImplementedError):
    pass


class DocumentService:
    @staticmethod
    def attach(*_args, **_kwargs):
        raise DocumentServiceNotReadyError(
            'DocumentService pendiente de core_attachment (Etapa 10b). Usar media_admin / uploads Core.'
        )
