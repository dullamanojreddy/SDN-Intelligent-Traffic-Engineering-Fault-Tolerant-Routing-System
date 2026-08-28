"""
Backend Settings & Environment Variables
"""
from pydantic import BaseModel, Field
from typing import List
import os

class Settings(BaseModel):
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    environment: str = Field(default="development")
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
    
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="sdn_traffic_engineering")
    
    controller_host: str = Field(default="127.0.0.1")
    controller_of_port: int = Field(default=6653)
    controller_rest_port: int = Field(default=8080)

    @property
    def cors_list(self) -> List[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings(
    backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
    backend_port=int(os.getenv("BACKEND_PORT", 8000)),
    environment=os.getenv("ENVIRONMENT", "development"),
    cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"),
    mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
    mongodb_database=os.getenv("MONGODB_DATABASE", "sdn_traffic_engineering"),
    controller_host=os.getenv("CONTROLLER_HOST", "127.0.0.1"),
    controller_of_port=int(os.getenv("CONTROLLER_OF_PORT", 6653)),
    controller_rest_port=int(os.getenv("CONTROLLER_REST_PORT", 8080))
)
