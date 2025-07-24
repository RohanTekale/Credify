import environ
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

env = environ.Env()
env.read_env()

User = get_user_model()

class Command(BaseCommand):
    help = "Create a superuser"
    def handle(self, *args, **kwargs):
        username = env('DJANGO_SUPERUSER_USERNAME')
        email = env('DJANGO_SUPERUSER_EMAIL')
        password = env('DJANGO_SUPERUSER_PASSWORD')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"✅ Superuser '{username}' created"))

        else:
            self.stdout.write(self.style.WARNING(f"⚠️ Superuser '{username}' already exists"))
