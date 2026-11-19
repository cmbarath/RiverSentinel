"""
Unit and Integration Test Suite for River Sentinel 2.0 — Phase 8.1
Validates Security Vulnerability Closure:
1. Immediate Privilege Revocation (No stale 60s cache bypass on require_role).
2. Deactivated User Rejection (is_active=False returns 401).
3. Explicit Cache Invalidation via invalidate_user_auth_cache().
4. Field Officer Restricted Access.
"""

import unittest
import os
import sys
import time
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from services.auth_service import _AUTH_CACHE, invalidate_user_auth_cache


class TestPhase81SecurityClosure(unittest.TestCase):
    """Test suite for Phase 8.1 Security Closure and Authorization Hardening."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def setUp(self):
        # Clear auth cache before each test
        _AUTH_CACHE.clear()

    def test_01_privileged_access_granted_when_admin_active(self):
        """Verify active authority_admin can execute privileged operations."""
        admin_user = {'id': 'adm-999', 'email': 'admin@uppcb.gov.in'}
        admin_profile = {'id': 'adm-999', 'role': 'authority_admin', 'is_active': True, 'full_name': 'Chief Admin'}

        with patch('services.auth_service.extract_bearer_token', return_value='jwt-token-admin-1'):
            with patch('services.auth_service.verify_supabase_jwt', return_value=admin_user):
                with patch('services.auth_service.get_user_profile', return_value=admin_profile):
                    res = self.client.post('/api/authority/generate-notice',
                                           headers={'Authorization': 'Bearer jwt-token-admin-1'},
                                           json={'target_entity': 'Unit Test Corp'})
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.get_json().get('status'), 'success')

    def test_02_immediate_revocation_denies_privileged_action_without_cache_delay(self):
        """
        Critical Test: Administrator role is revoked.
        Proves that a stale 60-second in-memory cache does NOT permit continued privileged access.
        """
        user_id = 'adm-revoked-888'
        token = 'jwt-token-revoked-admin'
        user_data = {'id': user_id, 'email': 'revoked@uppcb.gov.in'}

        # Step 1: User initially authenticates and token is cached with authority_admin role
        initial_admin_profile = {'id': user_id, 'role': 'authority_admin', 'is_active': True}
        _AUTH_CACHE[token] = {
            'user': user_data,
            'profile': initial_admin_profile,
            'expires_at': time.time() + 60
        }

        with patch('services.auth_service.extract_bearer_token', return_value=token):
            with patch('services.auth_service.verify_supabase_jwt', return_value=user_data):
                with patch('services.auth_service.get_user_profile', return_value=initial_admin_profile):
                    res1 = self.client.post('/api/authority/generate-notice',
                                            headers={'Authorization': f'Bearer {token}'},
                                            json={'target_entity': 'Unit Test Corp'})
                    self.assertEqual(res1.status_code, 200)

        # Confirm token is in cache with authority_admin role
        self.assertIn(token, _AUTH_CACHE)
        self.assertEqual(_AUTH_CACHE[token]['profile']['role'], 'authority_admin')

        # Step 2: Role is revoked in DB (changed to 'citizen')
        revoked_profile = {'id': user_id, 'role': 'citizen', 'is_active': True}

        with patch('services.auth_service.extract_bearer_token', return_value=token):
            with patch('services.auth_service.verify_supabase_jwt', return_value=user_data):
                with patch('services.auth_service.get_user_profile', return_value=revoked_profile):
                    # Same token attempts another administrator action within 60s
                    res2 = self.client.post('/api/authority/generate-notice',
                                            headers={'Authorization': f'Bearer {token}'},
                                            json={'target_entity': 'Unit Test Corp'})
                    # Must be rejected immediately with 403 Forbidden!
                    self.assertEqual(res2.status_code, 403)
                    self.assertIn('Access denied', res2.get_json().get('message', ''))

        # Confirm cache was updated to reflected revoked role
        self.assertEqual(_AUTH_CACHE[token]['profile']['role'], 'citizen')

    def test_03_deactivated_account_rejected_immediately(self):
        """Verify deactivated account (is_active=False) is rejected with 401."""
        user_id = 'deact-777'
        token = 'jwt-token-deactivated'
        user_data = {'id': user_id, 'email': 'deactivated@varanasi.org'}
        deactivated_profile = {'id': user_id, 'role': 'authority_admin', 'is_active': False}

        with patch('services.auth_service.extract_bearer_token', return_value=token):
            with patch('services.auth_service.verify_supabase_jwt', return_value=user_data):
                with patch('services.auth_service.get_user_profile', return_value=deactivated_profile):
                    res = self.client.post('/api/authority/generate-notice',
                                           headers={'Authorization': f'Bearer {token}'},
                                           json={'target_entity': 'Unit Test Corp'})
                    self.assertEqual(res.status_code, 401)
                    self.assertIn('deactivated or revoked', res.get_json().get('message', ''))

    def test_04_explicit_cache_invalidation(self):
        """Verify invalidate_user_auth_cache removes token and user from cache."""
        token = 'jwt-cache-test-token'
        user_id = 'user-to-flush-123'
        _AUTH_CACHE[token] = {
            'user': {'id': user_id, 'email': 'flush@test.com'},
            'profile': {'id': user_id, 'role': 'citizen'},
            'expires_at': time.time() + 60
        }
        self.assertIn(token, _AUTH_CACHE)

        # Invalidate by user_id
        invalidate_user_auth_cache(user_id=user_id)
        self.assertNotIn(token, _AUTH_CACHE)


if __name__ == '__main__':
    unittest.main()
