import random
import string
from temp_mail import TempMail

from app.core.logging import get_logger

logger = get_logger(__name__)


class AccountCreator:
    def __init__(self):
        self.temp_mail = TempMail()

    def generate_temp_email(self) -> str:
        """Generate a temporary email address."""
        # TempMail creates a random email when instantiated
        return self.temp_mail.email

    def generate_password(self, length: int = 12) -> str:
        """Generate a random password."""
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(chars) for _ in range(length))

    def create_temp_account(self) -> tuple[str, str]:
        """
        Create a temporary account by generating email and password.
        Note: This doesn't create a real Google account, just generates credentials.
        For YouTube authentication, a real Google account is needed.
        """
        email = self.generate_temp_email()
        password = self.generate_password()
        logger.info(f"Generated temp account: {email}")
        return email, password

    def get_verification_code(self, email: str) -> str | None:
        """Check for verification emails and extract code."""
        messages = self.temp_mail.get_messages()
        for msg in messages:
            if 'verification' in msg.subject.lower() or 'code' in msg.subject.lower():
                # Extract code from body (this is simplistic)
                body = msg.body
                # Look for 6-digit code
                import re
                match = re.search(r'\b\d{6}\b', body)
                if match:
                    return match.group(0)
        return None