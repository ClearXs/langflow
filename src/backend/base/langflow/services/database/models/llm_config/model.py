"""LLMConfig model for Holo knowledge system."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Text
from sqlmodel import JSON, DateTime, Field, SQLModel, func


def utc_now():
    return datetime.now(timezone.utc)


class LiteLLMProvider(str, Enum):
    """LiteLLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    AWS = "aws"
    OLLAMA = "ollama"
    LOCAL = "local"
    BEDROCK = "bedrock"
    VERTEX_AI = "vertex_ai"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    OPENROUTER = "openrouter"
    TOGETHER_AI = "together_ai"
    FIREWORKS_AI = "fireworks_ai"
    REPLICATE = "replicate"
    PERPLEXITY = "perplexity"
    ALIBABA_QWEN = "alibaba_qwen"
    MOONSHOT = "moonshot"
    ZHIPU = "zhipu"
    ANYSCALE = "anyscale"
    DEEPINFRA = "deepinfra"
    CEREBRAS = "cerebras"
    SAMBANOVA = "sambanova"
    AI21 = "ai21"
    CLOUDFLARE = "cloudflare"
    DATABRICKS = "databricks"
    COMETAPI = "cometapi"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class LLMConfigBase(SQLModel):
    """Base model for LLM config."""

    name: str = Field(max_length=255, nullable=False)
    provider: str = Field(max_length=50, nullable=False)
    model_name: str = Field(max_length=255, nullable=False)
    api_base: str | None = Field(default=None, max_length=500, nullable=True)
    api_key: str | None = Field(default=None, max_length=500, nullable=True)
    config: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))
    custom_provider: str | None = Field(default=None, max_length=100, description="Custom provider name for non-standard LLMs")
    system_instructions: str | None = Field(default=None, sa_column=Column(Text, nullable=True), description="Custom system instructions")
    use_default_system_instructions: bool = Field(default=True, nullable=False, description="Whether to use default system instructions")
    citations_enabled: bool = Field(default=True, nullable=False, description="Enable citation formatting in responses")
    litellm_params: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"), description="Additional litellm parameters")


class LLMConfig(LLMConfigBase, table=True):  # type: ignore[call-arg]
    """LLMConfig model for LLM configurations."""

    __tablename__ = "llm_configs"

    id: int = Field(default=None, primary_key=True)
    search_space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )


class LLMConfigCreate(SQLModel):
    """Model for creating an LLM config."""

    search_space_id: int
    name: str
    provider: str
    model_name: str
    api_base: str | None = None
    api_key: str | None = None
    config: dict | None = None
    custom_provider: str | None = None
    system_instructions: str | None = None
    use_default_system_instructions: bool | None = True
    citations_enabled: bool | None = True
    litellm_params: dict | None = None


class LLMConfigUpdate(SQLModel):
    """Model for updating an LLM config."""

    name: str | None = None
    provider: str | None = None
    model_name: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    config: dict | None = None
    custom_provider: str | None = None
    system_instructions: str | None = None
    use_default_system_instructions: bool | None = None
    citations_enabled: bool | None = None
    litellm_params: dict | None = None


class LLMConfigRead(SQLModel):
    """Model for reading an LLM config."""

    id: int
    search_space_id: int
    name: str
    provider: str
    model_name: str
    api_base: str | None
    api_key: str | None
    config: dict
    custom_provider: str | None
    system_instructions: str | None
    use_default_system_instructions: bool
    citations_enabled: bool
    litellm_params: dict
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
