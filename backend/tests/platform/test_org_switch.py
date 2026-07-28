"""Multi-empresa: vinculación + cambio de contexto sin re-login."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class TestLinkExistingUserToOrganization(unittest.TestCase):
    def test_not_found(self):
        from nodeone.services.organization_invites import link_existing_user_to_organization

        with patch(
            'nodeone.services.organization_invites.find_user_by_email',
            return_value=None,
        ):
            out = link_existing_user_to_organization(2, 'nuevo@x.com', 1)
        self.assertEqual(out['status'], 'not_found')

    def test_already_member(self):
        from nodeone.services.organization_invites import link_existing_user_to_organization

        user = MagicMock(id=9)
        with patch(
            'nodeone.services.organization_invites.find_user_by_email',
            return_value=user,
        ), patch(
            'nodeone.services.user_organization.user_has_active_membership',
            return_value=True,
        ):
            out = link_existing_user_to_organization(2, 'ya@x.com', 1)
        self.assertEqual(out['status'], 'already_member')
        self.assertEqual(out['user_id'], 9)

    def test_linked(self):
        from nodeone.services.organization_invites import link_existing_user_to_organization

        user = MagicMock(id=9)
        inv = MagicMock(id=55)
        with patch(
            'nodeone.services.organization_invites.find_user_by_email',
            return_value=user,
        ), patch(
            'nodeone.services.user_organization.user_has_active_membership',
            return_value=False,
        ), patch(
            'nodeone.services.organization_invites.create_invite_record',
            return_value=inv,
        ) as create, patch(
            'nodeone.services.organization_invites.accept_invite_for_user',
        ) as accept, patch(
            'nodeone.core.db.db.session.flush',
        ):
            out = link_existing_user_to_organization(2, 'user@x.com', 1, role='admin')
        self.assertEqual(out['status'], 'linked')
        self.assertEqual(out['invite_id'], 55)
        create.assert_called_once()
        accept.assert_called_once_with(inv, user)


class TestSyncUserOrganizationMemberships(unittest.TestCase):
    def test_adds_and_sets_primary(self):
        from app import app
        from nodeone.services.user_organization import sync_user_organization_memberships

        user = MagicMock(id=7, organization_id=1)
        with app.app_context():
            with patch('models.users.User.query') as uq, patch(
                'models.users.UserOrganization.query'
            ) as oq, patch(
                'nodeone.services.user_organization.ensure_membership'
            ) as ensure, patch(
                'nodeone.services.user_organization.deactivate_membership'
            ) as deact:
                uq.get.return_value = user
                oq.filter_by.return_value.all.return_value = [MagicMock(organization_id=1)]
                primary = sync_user_organization_memberships(
                    7, [1, 9], primary_organization_id=9
                )
        self.assertEqual(primary, 9)
        self.assertEqual(user.organization_id, 9)
        ensure.assert_any_call(7, 9)
        deact.assert_not_called()


class TestUserCanSwitchOrganization(unittest.TestCase):
    def test_anonymous_false(self):
        from nodeone.services.user_organization import user_can_switch_organization

        self.assertFalse(user_can_switch_organization(None))
        anon = MagicMock(is_authenticated=False)
        self.assertFalse(user_can_switch_organization(anon))

    def test_admin_true(self):
        from nodeone.services.user_organization import user_can_switch_organization

        admin = MagicMock(is_authenticated=True, is_admin=True, id=1)
        self.assertTrue(user_can_switch_organization(admin))

    def test_single_membership_false(self):
        from nodeone.services.user_organization import user_can_switch_organization

        user = MagicMock(is_authenticated=True, is_admin=False, id=9)
        with patch(
            'nodeone.services.user_organization.active_organization_ids_for_user',
            return_value={1},
        ):
            self.assertFalse(user_can_switch_organization(user))

    def test_multi_membership_true(self):
        from nodeone.services.user_organization import user_can_switch_organization

        user = MagicMock(is_authenticated=True, is_admin=False, id=9)
        with patch(
            'nodeone.services.user_organization.active_organization_ids_for_user',
            return_value={1, 5},
        ):
            self.assertTrue(user_can_switch_organization(user))


class TestGetCurrentOrgRespectsSessionForMultiMember(unittest.TestCase):
    def test_single_tenant_multi_member_uses_session(self):
        from utils.organization import get_current_organization_id

        user = MagicMock(
            is_authenticated=True,
            is_admin=False,
            organization_id=1,
            id=42,
        )
        with patch('utils.organization.has_request_context', return_value=True), patch(
            'utils.organization.current_user', user
        ), patch('utils.organization.single_tenant_default_only', return_value=True), patch(
            'utils.organization.session', {'organization_id': 5}
        ), patch(
            'app._organization_id_from_request_host', return_value=None
        ), patch(
            'nodeone.services.user_organization.user_can_switch_organization',
            return_value=True,
        ), patch(
            'utils.organization.user_has_access_to_organization',
            return_value=True,
        ):
            self.assertEqual(get_current_organization_id(), 5)

    def test_single_tenant_single_member_stays_home(self):
        from utils.organization import get_current_organization_id

        user = MagicMock(
            is_authenticated=True,
            is_admin=False,
            organization_id=3,
            id=7,
        )
        with patch('utils.organization.has_request_context', return_value=True), patch(
            'utils.organization.current_user', user
        ), patch('utils.organization.single_tenant_default_only', return_value=True), patch(
            'utils.organization.session', {'organization_id': 99}
        ), patch(
            'app._organization_id_from_request_host', return_value=None
        ), patch(
            'nodeone.services.user_organization.user_can_switch_organization',
            return_value=False,
        ):
            self.assertEqual(get_current_organization_id(), 3)


if __name__ == '__main__':
    unittest.main()
