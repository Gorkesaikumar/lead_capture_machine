import os
import requests
import dotenv
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Diagnoses the current Instagram integration configuration."

    def handle(self, *args, **options):
        env_path = os.path.join(settings.BASE_DIR, ".env")
        if os.path.exists(env_path):
            dotenv.load_dotenv(env_path)

        access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", getattr(settings, "INSTAGRAM_ACCESS_TOKEN", ""))
        account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", getattr(settings, "INSTAGRAM_ACCOUNT_ID", ""))

        self.stdout.write(self.style.WARNING("=== Instagram Integration Diagnostics ==="))

        # Validate Account ID format
        if not account_id:
            self.stdout.write(self.style.ERROR("Instagram Professional Account ID: MISSING"))
            return
        
        if not account_id.isdigit():
            self.stdout.write(self.style.ERROR(f"Instagram Professional Account ID: {account_id} (INVALID - Must be numeric, not a username)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Instagram Professional Account ID: {account_id}"))

        if not access_token:
            self.stdout.write(self.style.ERROR("Token valid: MISSING"))
            return

        # Check Token and Account Info
        url = f"https://graph.instagram.com/v20.0/{account_id}"
        response = requests.get(url, params={
            "fields": "id,username,name",
            "access_token": access_token
        })

        if response.status_code == 200:
            data = response.json()
            self.stdout.write(self.style.SUCCESS("Token valid: True"))
            self.stdout.write(self.style.SUCCESS(f"Instagram username: {data.get('username')}"))
        else:
            self.stdout.write(self.style.ERROR("Token valid: False (Or Account ID is incorrect)"))
            self.stdout.write(self.style.ERROR(f"API Error: {response.json()}"))
            return

        app_id = os.environ.get("META_APP_ID", getattr(settings, "META_APP_ID", ""))
        app_secret = os.environ.get("META_APP_SECRET", getattr(settings, "META_APP_SECRET", ""))

        # Check token expiration
        token_info_url = "https://graph.instagram.com/debug_token"
        token_response = requests.get(token_info_url, params={
            "input_token": access_token,
            "access_token": f"{app_id}|{app_secret}"
        })

        if token_response.status_code == 200:
            t_data = token_response.json().get("data", {})
            expires_at = t_data.get("expires_at")
            if expires_at:
                from datetime import datetime
                expiration_date = datetime.fromtimestamp(expires_at)
                self.stdout.write(self.style.SUCCESS(f"Token expiration: {expiration_date}"))
            else:
                self.stdout.write(self.style.WARNING("Token expiration: Never / Unknown"))
            
            scopes = t_data.get("scopes", [])
            self.stdout.write(self.style.SUCCESS(f"Required permissions: {', '.join(scopes)}"))
        else:
            self.stdout.write(self.style.ERROR("Could not fetch token debug info"))

        # Check webhook subscriptions for the account
        sub_url = f"https://graph.instagram.com/v20.0/{account_id}/subscribed_apps"
        sub_response = requests.get(sub_url, params={
            "access_token": access_token
        })

        if sub_response.status_code == 200:
            sub_data = sub_response.json().get("data", [])
            self.stdout.write(self.style.SUCCESS(f"Webhook callback: Configured in App Dashboard"))
            if sub_data:
                app_info = sub_data[0]
                fields = app_info.get("subscribed_fields", [])
                self.stdout.write(self.style.SUCCESS(f"Webhook subscription: Found (App ID: {app_info.get('id')})"))
                if "messages" in fields:
                    self.stdout.write(self.style.SUCCESS("Messages subscribed: True"))
                else:
                    self.stdout.write(self.style.ERROR("Messages subscribed: False"))
            else:
                self.stdout.write(self.style.ERROR("Webhook subscription: None found for this account"))
                self.stdout.write(self.style.ERROR("Messages subscribed: False"))
        else:
            self.stdout.write(self.style.ERROR("Could not fetch subscribed apps status"))

        self.stdout.write(self.style.WARNING("========================================="))
