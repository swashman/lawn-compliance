# run_task.py
from django.core.management.base import BaseCommand

from lawn_compliance.tasks import (
    send_token_compliance,  # Import your task function here
)


class Command(BaseCommand):
    help = "Manually runs a specific task"

    def handle(self, *args, **kwargs):
        send_token_compliance()  # Call the task function
        self.stdout.write(self.style.SUCCESS("Task has been run manually"))
