from datetime import timedelta

from django.utils.timezone import now


def time_since(dt):
    time_difference = now() - dt

    # If more than 2 days, show days, weeks, or months
    if time_difference > timedelta(days=2):
        days = time_difference.days
        if days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"

    # If less than 2 days, show hours
    hours = time_difference.seconds // 3600
    return f"{hours} hour{'s' if hours != 1 else ''} ago"
