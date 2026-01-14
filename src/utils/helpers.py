import secrets
import string

def generate_secure_password(length=12):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for i in range(length))

import csv

def get_csv_reader(f):
    """
    Returns a csv.DictReader with automatically detected delimiter.
    Falls back to comma if detection fails.
    """
    try:
        sample = f.read(1024)
        f.seek(0)
        # Only sniff for common delimiters
        dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
        delimiter = dialect.delimiter
    except csv.Error:
        f.seek(0)
        delimiter = ','
    
    return csv.DictReader(f, delimiter=delimiter)
