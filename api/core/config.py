"""
Módulo de Configuração Central do Backend do Agente Storyteller V5.
Utiliza Pydantic Settings para carregamento automatizado de variáveis do arquivo .env ou do ambiente do Railway.
"""
from typing import List, Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Classe de Gerenciamento de Configurações Globais do Aplicativo.
    Lê chaves de variáveis de ambiente do .env local ou de variáveis injetadas na nuvem (Railway).
    """

    # --- Configurações do Servidor ---
    environment: str = Field(
        default="development",
        description="Define o ambiente de execução da aplicação (development ou production)."
    )
    host: str = Field(
        default="127.0.0.1",
        description="IP ou interface de rede na qual o servidor FastAPI escutará."
    )
    port: int = Field(
        default=8000,
        description="Porta de rede para exposição da API HTTP/WebSocket."
    )
    log_level: str = Field(
        default="INFO",
        description="Nível mínimo de severidade dos logs gravados pela aplicação."
    )
    debug: bool = Field(
        default=True,
        description="Habilita reload automático do servidor ASGI e detalhamento de erros."
    )

    # --- Banco de Dados ---
    database_url: str = Field(
        default="sqlite:///./campaign.db",
        description="URL de conexão com o banco de dados (SQLite local ou PostgreSQL)."
    )
    database_pool_size: int = Field(
        default=5,
        description="Número máximo de conexões mantidas no pool do ORM SQLAlchemy."
    )

    # --- Configurações do Google Gemini API ---
    gemini_api_key: Optional[SecretStr] = Field(
        default=None,
        description="[SECRET] Chave privada de acesso à API do Google Gemini."
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Nome do modelo da Gemini API a ser invocado."
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        description="URL base do endpoint compatível OpenAI fornecido pelo Gemini."
    )
    gemini_timeout: int = Field(
        default=30,
        description="Tempo limite em segundos para o retorno de chamadas de LLM."
    )

    # --- CORS & Segurança ---
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Origem HTTP do frontend React autorizada a fazer requisições CORS."
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Lista de nomes de domínio permitidos no cabeçalho Host das requisições."
    )
    jwt_secret: SecretStr = Field(
        default=SecretStr("super_secret_default_key_change_in_production"),
        description="[SECRET] Chave de encriptação simétrica usada para assinar sessões."
    )

    # --- Rate Limiting & Cotas ---
    gemini_max_rpm: int = Field(
        default=60,
        description="Limite máximo de requisições por minuto toleradas sob a cota do Gemini."
    )
    gemini_max_monthly_tokens: int = Field(
        default=1000000,
        description="Cota limite de consumo de tokens por mês."
    )
    queue_max_size: int = Field(
        default=10,
        description="Tamanho limite da fila interna para enfileiramento de turnos assíncronos."
    )

    # Configuração do leitor do arquivo de variáveis de ambiente
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- Métodos de Conveniência ---

    def llm_headers(self) -> dict[str, str]:
        """
        Retorna o dicionário de cabeçalhos HTTP necessários para fazer a inferência no Gemini API.
        Injeta dinamicamente a chave privada de autenticação como token Bearer se configurada.
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.gemini_api_key:
            # Desembrulha o SecretStr para obter a string crua para requisição
            headers["Authorization"] = f"Bearer {self.gemini_api_key.get_secret_value()}"
        return headers

    def llm_endpoint(self) -> str:
        """
        Calcula e retorna a URL completa do endpoint da API do Gemini para inferência de chat completions.
        """
        return f"{self.gemini_base_url}/chat/completions"

    def db_connection_string(self) -> str:
        """
        Retorna a string de conexão tratada e higienizada do banco de dados SQLAlchemy.
        """
        return self.database_url

    def cors_origins(self) -> list[str]:
        """
        Retorna a lista tratada de domínios permitidos nas requisições do CORS (incluindo frontend_url).
        """
        return [self.frontend_url] + self.allowed_hosts

# Instanciação do Singleton Global de Configurações
settings = Settings()
