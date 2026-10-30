from django.test import TestCase
from rest_framework import status

from apps.core.exceptions.exception_handler import custom_exception_handler


class ExceptionHandlerTests(TestCase):
    def test_internal_server_error_hides_details(self):
        # Simulate a 500 error
        exc = Exception("Secret Database Error that should not be visible")

        # Call the exception handler directly since testing the whole middleware is harder
        response = custom_exception_handler(exc, None)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check that the error details are hidden
        self.assertNotIn("Secret Database Error", str(response.data))
        self.assertEqual(
            response.data["message"], "Ha ocurrido un error interno en el servidor."
        )
        self.assertIsNone(response.data["errors"])

    def test_account_locked_exception_includes_meta(self):
        from apps.core.exceptions.custom_exceptions import AccountLockedException

        exc = AccountLockedException(remaining_minutes=12)
        response = custom_exception_handler(exc, None)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "ACCOUNT_LOCKED")
        self.assertEqual(response.data["meta"], {"remaining_minutes": 12})
        self.assertIsNone(response.data["errors"])

    def test_api_response_error_with_meta(self):
        from apps.core.utils.api_response import ApiResponse

        response = ApiResponse.error(
            message="Error con metadata",
            code="TEST_ERROR",
            meta={"retry_after": 60},
        )

        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "TEST_ERROR")
        self.assertEqual(response.data["meta"], {"retry_after": 60})

