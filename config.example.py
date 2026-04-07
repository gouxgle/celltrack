import os

class Config:
    SECRET_KEY       = os.getenv('SECRET_KEY', 'CAMBIA_ESTO')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER    = 'uploads'

    MYSQL_HOST     = os.getenv('MYSQL_HOST', 'TU_HOST_MYSQL')
    MYSQL_USER     = os.getenv('MYSQL_USER', 'celltrack')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'TU_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'gcel')
    MYSQL_PORT     = int(os.getenv('MYSQL_PORT', 3306))

    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'ssl_disabled': True}
    }

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )
