import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Idempotently create (or update the password of) a Django superuser
    from environment variables, so it's safe to run on every deploy.

    Required env vars:
      DJANGO_SUPERUSER_USERNAME
      DJANGO_SUPERUSER_EMAIL
      DJANGO_SUPERUSER_PASSWORD

    If any of these are unset, the command exits quietly without
    creating anyone (so local/dev builds without these vars don't break).
    """

    help = "Create a superuser from DJANGO_SUPERUSER_* env vars if one doesn't already exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not (username and email and password):
            self.stdout.write(
                self.style.WARNING(
                    "Skipping admin creation: DJANGO_SUPERUSER_USERNAME, "
                    "DJANGO_SUPERUSER_EMAIL, or DJANGO_SUPERUSER_PASSWORD not set."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
        else:
            # User already exists — don't silently overwrite an in-use password
            # on every deploy. Just make sure staff/superuser flags are correct.
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Updated flags for existing user '{username}'."))
            else:
                self.stdout.write(f"Superuser '{username}' already exists. Skipping.")