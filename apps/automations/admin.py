from django.contrib import admin
from .models import Automation, AutomationAction, AutomationExecution

admin.site.register([Automation, AutomationAction, AutomationExecution])
