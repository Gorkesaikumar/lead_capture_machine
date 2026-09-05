from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = "Creates or promotes a Super Admin user for Nextora Control Panel access."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, required=True, help="Super admin email address")
        parser.add_argument("--password", type=str, default="Admin12345!", help="Super admin password")
        parser.add_argument("--name", type=str, default="Super Admin", help="Full name")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        name = options["name"]

        user = User.objects.filter(email=email).first()
        if user:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Promoted existing user {email} to Super Admin."))
        else:
            User.objects.create_superuser(email=email, password=password, full_name=name)
            self.stdout.write(self.style.SUCCESS(f"Created new Super Admin {email}."))
