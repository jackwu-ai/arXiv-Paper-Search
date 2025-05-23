from flask_caching import Cache
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

cache = Cache()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    auto_check=True, 
    enabled=True 
) 