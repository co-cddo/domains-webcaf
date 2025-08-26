import os
import secrets

os.environ["SECRET_KEY"] = secrets.token_hex(20)
os.environ["SSO_MODE"] = "local"
from webcaf.settings import *  # noqa
