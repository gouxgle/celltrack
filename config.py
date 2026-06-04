import os

class Config:
    SECRET_KEY       = os.getenv('SECRET_KEY', 'celltrack_dev_secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER    = 'uploads'

    _https = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
    SESSION_COOKIE_SECURE   = _https
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE  = _https

    MYSQL_HOST     = os.getenv('MYSQL_HOST', '192.168.0.7')
    MYSQL_USER     = os.getenv('MYSQL_USER', 'celltrack')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Celulares580')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'gcel')
    MYSQL_PORT     = int(os.getenv('MYSQL_PORT', 3306))

    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'ssl_disabled': True},
        'pool_pre_ping': True,      # verifica conexión antes de usarla
        'pool_recycle': 280,        # recicla antes del wait_timeout de MySQL (300s)
        'pool_size': 5,
        'max_overflow': 10,
    }

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )
