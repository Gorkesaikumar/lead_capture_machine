"""Permit embeds only on the unauthenticated, write-only lead form endpoint."""
import re


def public_form_cors(sender, request, **kwargs):
    return request.method in ("POST", "OPTIONS") and bool(re.fullmatch(r"/api/v1/forms/[0-9a-fA-F-]{36}/submit/", request.path))
