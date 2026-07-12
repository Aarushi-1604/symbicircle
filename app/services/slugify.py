import re


def generate_username(full_name: str, user_id: str) -> str:
    """
    'Aarushi Sharma' + 'a3f2b1c4-...' → 'aarushi-sharma-a3f2'
    """
    base = full_name.strip().lower()
    base = re.sub(r'[^a-z0-9\s]', '', base)
    base = re.sub(r'\s+', '-', base).strip('-')
    short_id = user_id.replace('-', '')[:4]
    return f"{base}-{short_id}"