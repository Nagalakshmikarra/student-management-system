
import os
import sys

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.APP_NAME = os.getenv(
            "APP_NAME",
            "GIST - Student Management System"
        ).strip()

        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "sqlite:///./sms.db"
        )

        self.SECRET_KEY = os.getenv("SECRET_KEY", "")

        self.ACCESS_TOKEN_MINUTES = int(
            os.getenv("ACCESS_TOKEN_MINUTES", "60")
        )

        self.ADMISSION_YEAR = int(
            os.getenv("ADMISSION_YEAR", "2026")
        )

        if len(self.SECRET_KEY) < 32:
            sys.exit(
                "ERROR: SECRET_KEY in .env must be at least 32 characters long."
            )


settings = Settings()
