from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def timezone_validator(value):
    """Timezone validator."""
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, AttributeError):
        raise ValidationError(
            _("Timezone validation error: %(value)s"),
            code="timezone_error",
            params={"value": value},
        )
