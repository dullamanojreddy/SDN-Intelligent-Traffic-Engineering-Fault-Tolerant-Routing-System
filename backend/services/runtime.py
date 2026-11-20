"""Process-wide service singletons shared by routes and the app lifespan."""
from backend.config.settings import settings
from backend.services.controller_monitor import ControllerMonitor
from backend.services.network_agent import NetworkAgentClient
from backend.services.orchestrator import NetworkOrchestrator
from backend.services.routing_service import RoutingService
from backend.services.topology_service import topology_service

routing_service = RoutingService(topology_service)
routing_service.refresh("Initial topology")  # baseline paths; produces no decisions

controller_monitor = ControllerMonitor(
    endpoints=settings.controller_endpoints,
    token_provider=lambda: settings.controller_api_token,
    snapshot_provider=topology_service.snapshot,
    interval=settings.controller_heartbeat_interval_sec,
    timeout=settings.controller_heartbeat_timeout_sec,
    failure_threshold=settings.controller_failure_threshold,
    recovery_threshold=settings.controller_recovery_threshold,
)
network_agent = NetworkAgentClient(settings.network_agent_url, settings.network_agent_token)
orchestrator = NetworkOrchestrator(topology_service, controller_monitor, routing_service, network_agent)
controller_monitor.on_event = orchestrator.on_controller_event
controller_monitor.on_state = orchestrator.on_live_state
controller_monitor.on_version_conflict = topology_service.ensure_version_above
