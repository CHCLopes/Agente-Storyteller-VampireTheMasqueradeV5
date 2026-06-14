from pydantic_settings import BaseSettings, SettingsConfigDict
import warnings

class Settings(BaseSettings):
    LMSTUDIO_HOST: str = "localhost"
    LMSTUDIO_PORT: int = 1234
    LMSTUDIO_MODEL: str = "nome-do-modelo"
    LMSTUDIO_TIMEOUT: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def model_post_init(self, __context: object) -> None:
        if self.LMSTUDIO_MODEL == "nome-do-modelo":
            warnings.warn(
                "[CONFIGURAÇÃO] LMSTUDIO_MODEL está com o valor placeholder 'nome-do-modelo'. "
                "Atualize o arquivo .env com o nome real do modelo carregado no LM Studio.",
                stacklevel=2
            )

    @property
    def lm_studio_base_url(self) -> str:
        return f"http://{self.LMSTUDIO_HOST}:{self.LMSTUDIO_PORT}/v1"
