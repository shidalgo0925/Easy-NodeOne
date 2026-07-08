"""SyncCursorService — cursores incrementales (Etapa 13)."""

from __future__ import annotations

from dataclasses import dataclass

from models.platform_sync import PlatformSyncCursor


@dataclass(frozen=True)
class SyncCursorDTO:
    organization_id: int
    client_id: str
    domain: str
    cursor_value: str

    def to_dict(self) -> dict:
        return {
            'organization_id': self.organization_id,
            'client_id': self.client_id,
            'domain': self.domain,
            'cursor_value': self.cursor_value,
        }


class SyncCursorService:
    @staticmethod
    def get(organization_id: int, domain: str, *, client_id: str = 'default') -> SyncCursorDTO:
        row = PlatformSyncCursor.query.filter_by(
            organization_id=int(organization_id),
            client_id=(client_id or 'default').strip() or 'default',
            domain=(domain or '').strip(),
        ).first()
        if row is None:
            return SyncCursorDTO(
                organization_id=int(organization_id),
                client_id=(client_id or 'default').strip() or 'default',
                domain=(domain or '').strip(),
                cursor_value='0',
            )
        return SyncCursorDTO(
            organization_id=int(row.organization_id),
            client_id=str(row.client_id),
            domain=str(row.domain),
            cursor_value=str(row.cursor_value or '0'),
        )

    @staticmethod
    def set_cursor(
        organization_id: int,
        domain: str,
        cursor_value: str,
        *,
        client_id: str = 'default',
    ) -> SyncCursorDTO:
        from app import db

        cid = (client_id or 'default').strip() or 'default'
        dom = (domain or '').strip()
        row = PlatformSyncCursor.query.filter_by(
            organization_id=int(organization_id),
            client_id=cid,
            domain=dom,
        ).first()
        if row is None:
            row = PlatformSyncCursor(
                organization_id=int(organization_id),
                client_id=cid,
                domain=dom,
                cursor_value=str(cursor_value or '0'),
            )
            db.session.add(row)
        else:
            row.cursor_value = str(cursor_value or '0')
        db.session.commit()
        return SyncCursorService.get(int(organization_id), dom, client_id=cid)
