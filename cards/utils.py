import secrets
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import CreditCard


def generate_card_number(max_retries=5):
    def calculate_luhn_check_digit(digits):
        total = 0
        is_even = False
        for digit in digits:
            if is_even:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
            is_even = not is_even
        return (10 - (total % 10)) % 10

    prefix = '9'
    for attempt in range(max_retries):
        try:
            digits = [int(prefix)] + [secrets.randbelow(10) for _ in range(14)]
            check_digit = calculate_luhn_check_digit(digits)
            card_number = ''.join(map(str, digits + [check_digit]))
            hashed_number = make_password(card_number)
            if not CreditCard.objects.filter(card_number=hashed_number).exists():
                return card_number, hashed_number
        except Exception as e:
            from sentry_sdk import capture_exception
            capture_exception(e)
            if attempt == max_retries - 1:
                raise Exception(f"Failed to generate card number after {max_retries} retries")
    raise ValueError(f"Unable to generate unique card number after {max_retries} retries")


def generate_cvv():
    return ''.join(str(secrets.randbelow(10)) for _ in range(3))


def calculate_expiry_date(card_type):
    years = card_type.expiry_years
    return timezone.now().date() + timezone.timedelta(days=years * 365)
