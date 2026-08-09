import os
import sys
import django
sys.path.append("d:/v4-studio")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from apps.analytics.services import AnalyticsService, AnalyticsDateRange
try:
    dr = AnalyticsDateRange.from_params(preset="this_month")
    res = AnalyticsService.get_dashboard_summary(dr)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
