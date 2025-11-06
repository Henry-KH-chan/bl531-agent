"""
BL531 Beamline Control API.

Provides interface to submit plans to the BL531 beamline's Bluesky Queue Server.
Does NOT handle data retrieval - that's left to separate data analysis tools.
"""
import requests
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

try:  
    from configs.logger import get_logger
except ImportError: 
    from logging import getLogger as get_logger



logger = get_logger("bl531_api")

# ============================================================================
# Configuration
# ============================================================================

BL531_MOTORS = {
    "hexapod_motor_Ry",
    "hexapod_motor_Ty",
    "hexapod_motor_Tz",
}

BL531_DETECTORS = {
    "diode",
    "det",
}

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class PlanResult:
    """Result from executing a plan."""
    run_uid: str
    plan_name: str
    timestamp: datetime


# ============================================================================
# Main API Class
# ============================================================================

class BL531API:
    """
    A control client for the BL531 beamline's Bluesky Queue Server.
    
    This API ONLY handles plan submission and execution.
    Data retrieval and analysis should be handled separately.
    """
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the BL531API control client.
        
        Args:
            base_url: URL of the Bluesky Queue Server
            api_key: API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Apikey {self.api_key}",
        }
        
        logger.info(f"Initializing BL531API with base_url={base_url}")

    def count(self, detectors: List[str], num: int = 1, metadata: Optional[Dict[str, Any]] = None) -> PlanResult:
        """
        Submit a 'count' plan to read detectors n times.

        Args:
            detectors: List of detector names
            num: Number of readings to take
            metadata: Optional metadata dict

        Returns:
            PlanResult with run_uid
            
        Raises:
            ValueError: If detectors are invalid
        """
        logger.info(f"📊 Submitting count plan: detectors={detectors}, num={num}")
        
        self._validate_detectors(detectors)
        
        plan_dict = {
            "item": {
                "name": "count",
                "kwargs": {
                    "detectors": detectors,
                    "num": num,
                    "md": metadata or {}
                },
                "item_type": "plan",
            },
            "pos": "back"
        }
        
        item_uid = self._submit_plan(plan_dict)
        run_uid = self._wait_for_completion(item_uid)
        
        logger.info(f"✅ Count plan completed. run_uid: {run_uid}")
        
        return PlanResult(
            run_uid=run_uid,
            plan_name="count",
            timestamp=datetime.now()
        )

    def scan(
        self,
        detectors: List[str],
        motor: str,
        start: float,
        stop: float,
        num: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PlanResult:
        """
        Submit a 'scan' plan.

        Args:
            detectors: List of detector names
            motor: Motor name to scan
            start: Starting position
            stop: Ending position
            num: Number of points
            metadata: Optional metadata dict

        Returns:
            PlanResult with run_uid
            
        Raises:
            ValueError: If detectors or motor are invalid
        """
        logger.info(f"🔄 Submitting scan plan: motor={motor}, range=[{start}, {stop}], num={num}")
        
        self._validate_detectors(detectors)
        self._validate_motor(motor)
        
        plan_dict = {
            "item": {
                "name": "scan",
                "kwargs": {
                    "detectors": detectors,
                    "motor": motor,
                    "start": start,
                    "stop": stop,
                    "num": num,
                    "md": metadata or {}
                },
                "item_type": "plan",
            },
            "pos": "back"
        }
        
        item_uid = self._submit_plan(plan_dict)
        run_uid = self._wait_for_completion(item_uid)
        
        logger.info(f"✅ Scan completed. run_uid: {run_uid}")
        
        return PlanResult(
            run_uid=run_uid,
            plan_name="scan",
            timestamp=datetime.now()
        )

    def automatic_gisaxs_alignment(self, metadata: Optional[Dict[str, Any]] = None) -> PlanResult:
        """
        Submit an automatic GISAXS alignment plan.

        Args:
            metadata: Optional metadata dict

        Returns:
            PlanResult with run_uid
        """
        logger.info("🎯 Submitting automatic GISAXS alignment plan")
        
        plan_dict = {
            "item": {
                "name": "automatic_gisaxs_alignment",
                "kwargs": {
                    "md": metadata or {}
                },
                "item_type": "plan",
            },
            "pos": "back"
        }
        
        item_uid = self._submit_plan(plan_dict)
        run_uid = self._wait_for_completion(item_uid)
        
        logger.info(f"✅ Alignment completed. run_uid: {run_uid}")
        
        return PlanResult(
            run_uid=run_uid,
            plan_name="automatic_gisaxs_alignment",
            timestamp=datetime.now()
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _validate_detectors(self, detectors: List[str]):
        """Validate that all requested detectors are available."""
        invalid = set(detectors) - BL531_DETECTORS
        if invalid:
            raise ValueError(
                f"Invalid detectors: {invalid}. Available detectors: {BL531_DETECTORS}"
            )
        logger.info(f"   ✅ Detectors validated: {detectors}")

    def _validate_motor(self, motor: str):
        """Validate that the motor is available."""
        if motor not in BL531_MOTORS:
            raise ValueError(
                f"Invalid motor: {motor}. Available motors: {BL531_MOTORS}"
            )
        logger.info(f"   ✅ Motor validated: {motor}")

    def _submit_plan(self, plan_dict: Dict[str, Any]) -> str:
        """Submit a plan to the queue and return the item_uid."""
        plan_name = plan_dict['item']['name']
        logger.info(f"📤 Submitting: {plan_name}")
        
        response = requests.post(
            f"{self.base_url}/api/queue/item/add",
            headers=self.headers,
            json=plan_dict
        )
        response.raise_for_status()
        
        item_uid = response.json()["item"]["item_uid"]
        logger.info(f"   item_uid: {item_uid}")
        
        # Start the queue
        requests.post(f"{self.base_url}/api/queue/start", headers=self.headers).raise_for_status()
        logger.info(f"   ▶️  Queue started")
        
        return item_uid

    def _wait_for_completion(self, item_uid: str, timeout: int = 300) -> str:
        """Wait for a plan to complete and return the run_uid."""
        logger.info(f"⏳ Waiting for completion...")
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Plan did not complete within {timeout}s")
            
            response = requests.get(f"{self.base_url}/api/history/get", headers=self.headers)
            response.raise_for_status()
            history = response.json()
            
            for entry in history.get("items", []):
                if entry.get("item_uid") == item_uid:
                    result = entry.get("result", {})
                    exit_status = result.get("exit_status")
                    run_uids = result.get("run_uids", [])
                    
                    if run_uids and exit_status == "completed":
                        return run_uids[0]
                    elif exit_status in ["failed", "aborted"]:
                        raise RuntimeError(f"Plan failed: {exit_status}")
            
            time.sleep(1)

# ============================================================================
# Module-level instance
# ============================================================================


bl531 = BL531API(
    base_url="http://localhost:60610",
    api_key="test"
)
