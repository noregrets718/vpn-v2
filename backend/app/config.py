from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # PostgreSQL настройки
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    #jwt
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SS_BINARY_PATH: str = "/usr/bin/ss-server"
    SS_CONFIG_DIR: str = "/etc/shadowsocks-libev/users"
    SS_METHOD: str = "chacha20-ietf-poly1305"
    PORT_RANGE_START: int = 10001
    PORT_RANGE_END: int = 60000

    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    LOCAL_SERVER_NAME: str
    LOCAL_SERVER_COUNTRY: str

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def async_database_url(self) -> str:
        """Формирует URL для asyncpg"""

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()