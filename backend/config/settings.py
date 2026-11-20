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
    controller_api_url: str = Field(default="http://127.0.0.1:8080")
    controller_api_token: str = Field(default="")
    # Comma-separated management API URLs of standby controllers, tried in order.
    controller_backup_api_urls: str = Field(default="")
    # Management API of the Mininet network agent; empty means "no live network"
    # (model-only demo mode where new links stay unconfirmed and unroutable).
    network_agent_url: str = Field(default="")
    network_agent_token: str = Field(default="")
    controller_monitor_enabled: bool = Field(default=True)
    controller_heartbeat_interval_sec: float = Field(default=2.0, gt=0)
    controller_heartbeat_timeout_sec: float = Field(default=1.5, gt=0)
    controller_failure_threshold: int = Field(default=3, ge=1)
    controller_recovery_threshold: int = Field(default=2, ge=1)

    @property
    def controller_endpoints(self) -> List[str]:
        """Primary management URL followed by any configured standbys."""
        backups = [u.strip() for u in self.controller_backup_api_urls.split(",") if u.strip()]
        return [self.controller_api_url, *backups]

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
    controller_rest_port=int(os.getenv("CONTROLLER_REST_PORT", 8080)),
    controller_api_url=os.getenv("CONTROLLER_API_URL", "http://127.0.0.1:8080"),
    controller_api_token=os.getenv("CONTROLLER_API_TOKEN", ""),
    controller_backup_api_urls=os.getenv("CONTROLLER_BACKUP_API_URLS", ""),
    network_agent_url=os.getenv("NETWORK_AGENT_URL", ""),
    network_agent_token=os.getenv("NETWORK_AGENT_TOKEN", "") or os.getenv("CONTROLLER_API_TOKEN", ""),
    controller_monitor_enabled=os.getenv("CONTROLLER_MONITOR_ENABLED", "true").lower() != "false",
    controller_heartbeat_interval_sec=float(os.getenv("CONTROLLER_HEARTBEAT_INTERVAL_SEC", 2.0)),
    controller_heartbeat_timeout_sec=float(os.getenv("CONTROLLER_HEARTBEAT_TIMEOUT_SEC", 1.5)),
    controller_failure_threshold=int(os.getenv("CONTROLLER_FAILURE_THRESHOLD", 3)),
    controller_recovery_threshold=int(os.getenv("CONTROLLER_RECOVERY_THRESHOLD", 2)),
)
