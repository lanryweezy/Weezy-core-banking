# Common utility functions shared across the application/agents

import uuid
from datetime import datetime, timezone
# import re

def generate_unique_id(prefix: str = "id_") -> str:
    """Generates a unique ID with an optional prefix."""
    return f"{prefix}{uuid.uuid4().hex}"

def get_current_utc_timestamp() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

# def sanitize_input(text: str) -> str:
#     """Basic input sanitization to remove potentially harmful characters."""
#     if not text:
#         return ""
#     # Example: Remove characters that are not alphanumeric, spaces, or common punctuation.
#     # This is a very basic example and might need to be much more robust depending on use case.
#     # sanitized_text = re.sub(r'[^a-zA-Z0-9\s\.,;:!?\'"-]', '', text)
#     # return sanitized_text
#     return text # Placeholder, actual sanitization is complex

# def format_currency_ngn(amount: float) -> str:
#     """Formats a float amount as NGN currency string."""
#     try:
#         return f"₦{amount:,.2f}"
#     except (ValueError, TypeError):
#         return "₦0.00" # Or handle error appropriately

# def parse_date_string(date_str: str, fmt: str = "%Y-%m-%d") -> datetime.date:
#     """Parses a date string into a datetime.date object."""
#     try:
#         return datetime.strptime(date_str, fmt).date()
#     except (ValueError, TypeError):
#         return None # Or raise error

# Example usage:
if __name__ == "__main__":
    unique_task_id = generate_unique_id(prefix="task_")
    print(f"Generated Unique ID: {unique_task_id}")

    current_time = get_current_utc_timestamp()
    print(f"Current UTC Timestamp: {current_time}")

    # raw_text = "<script>alert('XSS')</script> Some valid text."
    # sanitized = sanitize_input(raw_text)
    # print(f"Sanitized Text: '{sanitized}' (Note: current sanitize is a placeholder)")

    # amount = 1234567.89
    # formatted_amount = format_currency_ngn(amount)
    # print(f"Formatted NGN Amount: {formatted_amount}")

    # date_obj = parse_date_string("2023-10-27")
    # if date_obj:
    #     print(f"Parsed Date: {date_obj}, Type: {type(date_obj)}")
    # else:
    #     print("Failed to parse date string.")
    print("Core utils.py placeholder with common utility functions.")

print("Core utils.py placeholder.")
