def validate_phone(phone: str) -> bool:
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    return phone.isdigit() and 10 <= len(phone) <= 15