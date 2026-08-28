"""
Quality of Service (QoS) Policy Engine
"""
from typing import Dict, Any
from controller.config.settings import settings
from controller.routing.cost_function import CostCalculator

class QoSEngine:
    def __init__(self):
        self.profiles = settings.qos_profiles
        
    def get_cost_calculator_for_traffic(self, traffic_class: str = "DEFAULT") -> CostCalculator:
        """Returns a customized CostCalculator weighted according to the traffic QoS priority."""
        cls = traffic_class.upper()
        if cls in self.profiles:
            cfg = self.profiles[cls]
            return CostCalculator(
                alpha=cfg["latency"],
                beta=cfg["utilization"],
                gamma=cfg["loss"]
            )
        # Default global policy
        return CostCalculator(
            alpha=settings.latency_weight,
            beta=settings.utilization_weight,
            gamma=settings.loss_weight
        )
        
    def classify_packet(self, ip_proto: int, src_port: int, dst_port: int, dscp: int = 0) -> str:
        """Classifies incoming packet into QoS service tier."""
        # RTP / SIP Voice ports
        if ip_proto == 17 and (dst_port in [5060, 5061] or (16384 <= dst_port <= 32767)):
            return "VOICE"
        # Video streaming / RTSP / RTMP / HLS
        if dst_port in [554, 1935, 8088] or (ip_proto == 6 and dst_port in [8000, 8080]):
            return "VIDEO"
        # Web browsing (HTTP/HTTPS)
        if dst_port in [80, 443]:
            return "WEB"
        # Background Bulk transfers
        return "BACKGROUND"
