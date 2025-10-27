from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    # Django 3.2 had a count of ~260,000 by default, which was upped to 870,000 for Django 5.1.
    iterations = 260000
