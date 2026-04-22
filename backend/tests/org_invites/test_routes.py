"""Smoke: rutas de invitaciones a organización."""
import secrets
import sys
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestOrgInviteRoutes(unittest.TestCase):
    def test_endpoints_registered(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('api_admin_organization_invites', endpoints)
        self.assertIn('api_admin_revoke_organization_invite', endpoints)
        self.assertIn('accept_invite', endpoints)

    def test_paths_and_methods(self):
        from app import app

        rules = {r.endpoint: r for r in app.url_map.iter_rules()}
        inv = rules['api_admin_organization_invites']
        self.assertEqual(inv.rule, '/api/admin/organization-invites')
        self.assertIn('GET', inv.methods)
        self.assertIn('POST', inv.methods)
        rev = rules['api_admin_revoke_organization_invite']
        self.assertEqual(rev.rule, '/api/admin/organization-invites/<int:invite_id>')
        self.assertIn('DELETE', rev.methods)
        self.assertEqual(rules['accept_invite'].rule, '/accept-invite/<token>')

    def test_get_requires_login(self):
        from app import app

        with app.test_client() as c:
            r = c.get('/api/admin/organization-invites', headers={'Accept': 'application/json'})
        self.assertIn(r.status_code, (302, 401))

    def test_post_requires_login(self):
        from app import app

        with app.test_client() as c:
            r = c.post(
                '/api/admin/organization-invites',
                json={'email': 'a@b.com', 'role': 'user'},
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            )
        self.assertIn(r.status_code, (302, 401))

    def test_get_authenticated_returns_filter_and_invites(self):
        from app import app, db
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        email = f'invite_api_get_{suffix}@example.invalid'
        with app.app_context():
            u = User(
                email=email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=1,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.get(
                    '/api/admin/organization-invites?status=all&limit=5',
                    headers={'Accept': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertTrue(data.get('success'))
            self.assertEqual(data.get('filter'), 'all')
            self.assertIsInstance(data.get('invites'), list)
        finally:
            with app.app_context():
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_post_success_omits_token_by_default(self):
        """POST no debe exponer `token` salvo debug o ORG_INVITE_API_INCLUDE_TOKEN."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_api_post_adm_{suffix}@example.invalid'
        invited_email = f'invited_{suffix}@example.invalid'
        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=1,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        invite_id = None
        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.post(
                    '/api/admin/organization-invites',
                    json={'email': invited_email, 'role': 'user'},
                    headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertTrue(data.get('success'))
            self.assertNotIn('token', data)
            invite_id = data.get('invite_id')
        finally:
            with app.app_context():
                if invite_id:
                    OrganizationInvite.query.filter_by(id=invite_id).delete()
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_post_includes_token_when_org_invite_api_include_token(self):
        """Con ORG_INVITE_API_INCLUDE_TOKEN, POST puede devolver el token (p. ej. soporte)."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_api_tok_adm_{suffix}@example.invalid'
        invited_email = f'invited_tok_{suffix}@example.invalid'
        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=1,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        invite_id = None
        prev_flag = app.config.get('ORG_INVITE_API_INCLUDE_TOKEN')
        try:
            app.config['ORG_INVITE_API_INCLUDE_TOKEN'] = True
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.post(
                    '/api/admin/organization-invites',
                    json={'email': invited_email, 'role': 'user'},
                    headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('token', data)
            self.assertTrue(isinstance(data.get('token'), str) and len(data['token']) >= 8)
            invite_id = data.get('invite_id')
        finally:
            if prev_flag is None:
                app.config.pop('ORG_INVITE_API_INCLUDE_TOKEN', None)
            else:
                app.config['ORG_INVITE_API_INCLUDE_TOKEN'] = prev_flag
            with app.app_context():
                if invite_id:
                    OrganizationInvite.query.filter_by(id=invite_id).delete()
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_get_status_filters_pending_accepted_revoked(self):
        """GET ?status= pending|accepted|revoked solo devuelve filas de ese estado (org en scope)."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_filter_adm_{suffix}@example.invalid'
        em_p = f'flt_p_{suffix}@example.invalid'
        em_a = f'flt_a_{suffix}@example.invalid'
        em_r = f'flt_r_{suffix}@example.invalid'
        our_emails = {em_p, em_a, em_r}
        oid = 1

        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=oid,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id

            def row(email, status, token):
                inv = OrganizationInvite(
                    organization_id=oid,
                    email=email,
                    token=token,
                    role='user',
                    status=status,
                    expires_at=datetime.utcnow() + timedelta(days=7),
                )
                if status == 'accepted':
                    inv.accepted_at = datetime.utcnow()
                return inv

            t1 = secrets.token_urlsafe(32)[:48]
            t2 = secrets.token_urlsafe(32)[:48]
            t3 = secrets.token_urlsafe(32)[:48]
            db.session.add(row(em_p, 'pending', t1))
            db.session.add(row(em_a, 'accepted', t2))
            db.session.add(row(em_r, 'revoked', t3))
            db.session.commit()

        def ours_subset(data):
            return {i['email'] for i in (data.get('invites') or []) if i.get('email') in our_emails}

        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True

                r_p = c.get(
                    '/api/admin/organization-invites?status=pending&limit=200',
                    headers={'Accept': 'application/json'},
                )
                r_a = c.get(
                    '/api/admin/organization-invites?status=accepted&limit=200',
                    headers={'Accept': 'application/json'},
                )
                r_v = c.get(
                    '/api/admin/organization-invites?status=revoked&limit=200',
                    headers={'Accept': 'application/json'},
                )
                r_all = c.get(
                    '/api/admin/organization-invites?status=all&limit=200',
                    headers={'Accept': 'application/json'},
                )

            self.assertEqual(r_p.status_code, 200)
            self.assertEqual(r_a.status_code, 200)
            self.assertEqual(r_v.status_code, 200)
            self.assertEqual(r_all.status_code, 200)

            d_p, d_a, d_v, d_all = r_p.get_json(), r_a.get_json(), r_v.get_json(), r_all.get_json()
            self.assertEqual(d_p.get('filter'), 'pending')
            self.assertEqual(d_a.get('filter'), 'accepted')
            self.assertEqual(d_v.get('filter'), 'revoked')
            self.assertEqual(d_all.get('filter'), 'all')

            self.assertEqual(ours_subset(d_p), {em_p})
            self.assertEqual(ours_subset(d_a), {em_a})
            self.assertEqual(ours_subset(d_v), {em_r})
            self.assertEqual(ours_subset(d_all), our_emails)

            for inv in d_p.get('invites', []):
                if inv.get('email') in our_emails:
                    self.assertEqual(inv.get('status'), 'pending')
            for inv in d_a.get('invites', []):
                if inv.get('email') in our_emails:
                    self.assertEqual(inv.get('status'), 'accepted')
            for inv in d_v.get('invites', []):
                if inv.get('email') in our_emails:
                    self.assertEqual(inv.get('status'), 'revoked')
        finally:
            with app.app_context():
                OrganizationInvite.query.filter(
                    OrganizationInvite.organization_id == oid,
                    OrganizationInvite.email.in_(list(our_emails)),
                ).delete(synchronize_session=False)
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_get_invalid_status_defaults_to_pending_filter(self):
        """status desconocido → misma query que pending (filter en JSON = pending)."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_badst_adm_{suffix}@example.invalid'
        em_p = f'bad_p_{suffix}@example.invalid'
        em_a = f'bad_a_{suffix}@example.invalid'
        our_emails = {em_p, em_a}
        oid = 1

        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=oid,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id

            db.session.add(
                OrganizationInvite(
                    organization_id=oid,
                    email=em_p,
                    token=secrets.token_urlsafe(32)[:48],
                    role='user',
                    status='pending',
                    expires_at=datetime.utcnow() + timedelta(days=7),
                )
            )
            db.session.add(
                OrganizationInvite(
                    organization_id=oid,
                    email=em_a,
                    token=secrets.token_urlsafe(32)[:48],
                    role='user',
                    status='accepted',
                    expires_at=datetime.utcnow() + timedelta(days=7),
                    accepted_at=datetime.utcnow(),
                )
            )
            db.session.commit()

        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.get(
                    '/api/admin/organization-invites?status=not-a-real-status&limit=200',
                    headers={'Accept': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(data.get('filter'), 'pending')
            ours = {i['email'] for i in (data.get('invites') or []) if i.get('email') in our_emails}
            self.assertEqual(ours, {em_p})
        finally:
            with app.app_context():
                OrganizationInvite.query.filter(
                    OrganizationInvite.organization_id == oid,
                    OrganizationInvite.email.in_(list(our_emails)),
                ).delete(synchronize_session=False)
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_delete_requires_login(self):
        from app import app

        with app.test_client() as c:
            r = c.delete(
                '/api/admin/organization-invites/1',
                headers={'Accept': 'application/json'},
            )
        self.assertIn(r.status_code, (302, 401))

    def test_delete_revoke_pending_then_nonpending_fails(self):
        """DELETE marca pending como revoked; repetir o borrar accepted → 400."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_del_adm_{suffix}@example.invalid'
        em_p = f'del_p_{suffix}@example.invalid'
        em_a = f'del_a_{suffix}@example.invalid'
        oid = 1

        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=oid,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id

            inv_p = OrganizationInvite(
                organization_id=oid,
                email=em_p,
                token=secrets.token_urlsafe(32)[:48],
                role='user',
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            inv_a = OrganizationInvite(
                organization_id=oid,
                email=em_a,
                token=secrets.token_urlsafe(32)[:48],
                role='user',
                status='accepted',
                expires_at=datetime.utcnow() + timedelta(days=7),
                accepted_at=datetime.utcnow(),
            )
            db.session.add(inv_p)
            db.session.add(inv_a)
            db.session.commit()
            pid, aid = inv_p.id, inv_a.id

        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True

                r_ok = c.delete(
                    f'/api/admin/organization-invites/{pid}',
                    headers={'Accept': 'application/json'},
                )
                self.assertEqual(r_ok.status_code, 200)
                self.assertTrue(r_ok.get_json().get('success'))

                r_dup = c.delete(
                    f'/api/admin/organization-invites/{pid}',
                    headers={'Accept': 'application/json'},
                )
                self.assertEqual(r_dup.status_code, 400)

                r_acc = c.delete(
                    f'/api/admin/organization-invites/{aid}',
                    headers={'Accept': 'application/json'},
                )
                self.assertEqual(r_acc.status_code, 400)
                self.assertIn('pendientes', (r_acc.get_json() or {}).get('error', ''))

            with app.app_context():
                again = OrganizationInvite.query.filter_by(id=pid).first()
                self.assertEqual(again.status, 'revoked')
        finally:
            with app.app_context():
                OrganizationInvite.query.filter(
                    OrganizationInvite.organization_id == oid,
                    OrganizationInvite.email.in_([em_p, em_a]),
                ).delete(synchronize_session=False)
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_delete_not_found(self):
        from app import app, db
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_del404_{suffix}@example.invalid'
        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=1,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.delete(
                    '/api/admin/organization-invites/999999991',
                    headers={'Accept': 'application/json'},
                )
            self.assertEqual(r.status_code, 404)
            self.assertFalse((r.get_json() or {}).get('success', True))
        finally:
            with app.app_context():
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_get_limit_invalid_string_uses_default(self):
        """limit no numérico → default 100 (ruta no falla)."""
        from app import app, db
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_lim_adm_{suffix}@example.invalid'
        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=1,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.get(
                    '/api/admin/organization-invites?status=pending&limit=not-a-number',
                    headers={'Accept': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertTrue(data.get('success'))
            self.assertIsInstance(data.get('invites'), list)
        finally:
            with app.app_context():
                User.query.filter_by(id=uid).delete()
                db.session.commit()

    def test_get_limit_zero_clamps_to_one_row_max(self):
        """limit=0 se acota a mínimo 1 (max(1, min(0,200)))."""
        from app import app, db
        from models.organization_invite import OrganizationInvite
        from models.users import User
        from werkzeug.security import generate_password_hash

        suffix = uuid.uuid4().hex[:12]
        admin_email = f'invite_lim0_adm_{suffix}@example.invalid'
        em = f'lim0_{suffix}@example.invalid'
        oid = 1

        with app.app_context():
            u = User(
                email=admin_email,
                password_hash=generate_password_hash('x'),
                first_name='T',
                last_name='Test',
                organization_id=oid,
                is_admin=True,
                must_change_password=False,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
            db.session.add(
                OrganizationInvite(
                    organization_id=oid,
                    email=em,
                    token=secrets.token_urlsafe(32)[:48],
                    role='user',
                    status='pending',
                    expires_at=datetime.utcnow() + timedelta(days=7),
                )
            )
            db.session.commit()

        try:
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess['_user_id'] = str(uid)
                    sess['_fresh'] = True
                r = c.get(
                    f'/api/admin/organization-invites?status=pending&limit=0',
                    headers={'Accept': 'application/json'},
                )
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            ours = [i for i in (data.get('invites') or []) if i.get('email') == em]
            self.assertEqual(len(ours), 1)
        finally:
            with app.app_context():
                OrganizationInvite.query.filter_by(email=em).delete(synchronize_session=False)
                User.query.filter_by(id=uid).delete()
                db.session.commit()


if __name__ == '__main__':
    unittest.main()
