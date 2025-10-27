from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    # Set your desired lower iteration count here.
    # For example, using Django 3.2's 260,000 count.
    iterations = 260000
