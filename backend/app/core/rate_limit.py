"""
Limitation de débit sur les endpoints sensibles (authentification), pour
limiter les attaques par force brute — point 17 du cahier des charges.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
