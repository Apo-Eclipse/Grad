import os
import django
import json
from django.test import TestCase, Client
from django.conf import settings

# 1. Setup Django standalone environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Import models after setup
from core.models import ChatConversation, Profile
from django.contrib.auth.models import User


class EndpointTests(TestCase):
    """
    Automated tests for API endpoints.
    Inheriting from TestCase ensures all database changes are rolled back
    after each test, keeping the database clean.
    """

    def setUp(self):
        self.client = Client()
        self.headers = {"CONTENT_TYPE": "application/json"}

    def test_health_check(self):
        """Verify the health endpoint returns 200 OK."""
        print("\nTesting /api/personal_assistant/health ...")
        response = self.client.get("/api/personal_assistant/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "healthy", "service": "PersonalAssistantAPI"}
        )
        print("OK")

    def test_create_conversation_rollback(self):
        """
        Test creating a conversation.
        Data is created within this test transaction but rolled back afterwards.
        """
        print("\nTesting /api/personal_assistant/conversations/start ...")

        # 1. Create a dummy user first (needed for FK)
        user = User.objects.create(
            username="test_user", first_name="Test", last_name="User"
        )

        payload = {"user_id": user.id, "channel": "test_script"}

        response = self.client.post(
            "/api/personal_assistant/conversations/start",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("conversation_id", data)
        self.assertEqual(data["user_id"], user.id)

        # Verify it exists in DB *now*
        self.assertTrue(
            ChatConversation.objects.filter(id=data["conversation_id"]).exists()
        )
        print("OK (Conversation created in test transaction)")

    def test_create_user_rollback(self):
        """Test creating a new user via API."""
        print("\nTesting /api/database/users/ ...")

        payload = {
            "first_name": "Rollback",
            "last_name": "Tester",
            "job_title": "Engineer",
            "address": "123 Test Ln",
            "birthday": "1990-01-01",
            "gender": "Male",
            "employment_status": "Employed",
            "education_level": "Bachelor",
        }

        response = self.client.post(
            "/api/database/users/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["first_name"], "Rollback")

        # Verify in DB
        self.assertTrue(User.objects.filter(first_name="Rollback").exists())
        self.assertTrue(Profile.objects.filter(user__first_name="Rollback").exists())
        print("OK (User created in test transaction)")


if __name__ == "__main__":
    # This block allows running the script directly with: python test_endpoints.py
    # However, for Django TestCase to work correctly with the test database,
    # it's best run via the test runner.
    # But since we set up Django above, we can run unittest.main() which will
    # use the properly configured test environment.

    from django.core.management import call_command
    import sys

    print("Running tests... (Data changes will be rolled back)")

    # We use 'test' management command to run THIS file as the test suite.
    # This ensures the test database is created and destroyed properly.
    sys.argv = ["manage.py", "test", "test_endpoints"]
    call_command("test", "test_endpoints")
