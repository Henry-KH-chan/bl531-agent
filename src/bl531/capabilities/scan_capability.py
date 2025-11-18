"""
Scan Plan Capability for BL531 Beamline.

Executes a scan plan to read detectors while scanning a motor.
"""

from typing import Dict, Any, Optional
import textwrap

from osprey.base.decorators import capability_node
from osprey.base.capability import BaseCapability
from osprey.base.errors import ErrorClassification, ErrorSeverity
from osprey.base.examples import (
    OrchestratorGuide, OrchestratorExample, PlannedStep,
    ClassifierActions, ClassifierExample, TaskClassifierGuide
)
from osprey.state import AgentState, StateManager
from osprey.registry import get_registry
from osprey.utils.logger import get_logger
from osprey.utils.streaming import get_streamer

from bl531.context_classes import ScanPlanContext
from bl531.BL531API import bl531

logger = get_logger("scan_capability")
registry = get_registry()


class ScanCapabilityError(Exception):
    """Base exception for scan capability."""
    pass


class InvalidMotorError(ScanCapabilityError):
    """Raised when invalid motor is specified."""
    pass


class PlanExecutionError(ScanCapabilityError):
    """Raised when plan execution fails."""
    pass


@capability_node
class ScanCapability(BaseCapability):
    """Execute a scan plan on the BL531 beamline.
    
    Scans a motor while reading detectors and returns the run_uid for data analysis.
    """
    
    name = "bl531_scan"
    description = "Execute a scan plan on BL531 beamline - scan motor while reading detectors"
    provides = ["SCAN_PLAN_CONTEXT"]
    # Orchestrator must provide these inputs
    requires = ["MOTOR_NAME", "START_POSITION", "STOP_POSITION", "NUM_POINTS", "DETECTORS"]
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute scan plan using inputs from orchestrator."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("scan_capability", state)
        
        try:
            # The orchestrator provides inputs as a list of dicts, so we merge them.
            inputs_list = step.get('inputs', [])
            logger.info(inputs_list)
            combined_inputs = {}
            if isinstance(inputs_list, list):
                for item in inputs_list:
                    if isinstance(item, dict):
                        combined_inputs.update(item)
            else:
                combined_inputs = inputs_list if isinstance(inputs_list, dict) else {}
            
            # Extract required parameters
            motor = combined_inputs.get("MOTOR_NAME")
            start = combined_inputs.get("START_POSITION")
            stop = combined_inputs.get("STOP_POSITION")
            num = combined_inputs.get("NUM_POINTS")
            detectors = combined_inputs.get("DETECTORS", ["det"])
            
            # Validate we have all required inputs
            if not motor or start is None or stop is None or num is None:
                raise ValueError(
                    f"Missing required scan inputs. Got: motor={motor}, start={start}, "
                    f"stop={stop}, num={num}"
                )
            
            # Convert to proper types
            start = float(start)
            stop = float(stop)
            num = int(num)
            
            # Parse detectors - orchestrator might send as string representation
            if isinstance(detectors, str):
                # Handle cases like "['det']" or "det" or '["det"]'
                import ast
                try:
                    # Try to parse as Python literal (e.g., "['det']" → ['det'])
                    detectors = ast.literal_eval(detectors)
                except (ValueError, SyntaxError):
                    # If that fails, treat as single detector name
                    detectors = [detectors]
            
            # Ensure detectors is a list
            if not isinstance(detectors, list):
                detectors = [detectors]
            
            context_key = step.get("context_key", "scan_result")
            
            logger.info(f"🔄 Executing scan: motor={motor}, start={start}, stop={stop}, num={num}, detectors={detectors}")
            streamer.status(f"Scanning {motor} from {start} to {stop} with {num} points...")
            
            # Call API to submit plan
            result = bl531.scan(
                detectors=detectors,
                motor=motor,
                start=start,
                stop=stop,
                num=num
            )
            
            logger.info(f"✅ Scan completed. run_uid: {result.run_uid}")
            streamer.status(f"Scan completed with run_uid: {result.run_uid}")
            
            # Create output context
            context = ScanPlanContext(
                run_uid=result.run_uid,
                motor=motor,
                start=start,
                stop=stop,
                num_points=num,
                detectors=detectors,
                timestamp=result.timestamp,
                status="completed"
            )
            
            # Store context and return
            context_updates = StateManager.store_context(
                state,
                registry.context_types.SCAN_PLAN_CONTEXT,
                context_key,
                context
            )
            
            return context_updates
            
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify scan errors for intelligent retry coordination."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid scan parameters: {str(exc)}",
                metadata={"type": "invalid_parameter"}
            )
        elif isinstance(exc, InvalidMotorError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid motor specified: {str(exc)}",
                metadata={"type": "invalid_motor"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Scan execution error: {str(exc)}",
                metadata={"type": "execution_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="gisaxs_scan",
                capability="bl531_scan",
                task_objective="Scan grazing incidence angle from 0.1 to 0.2 in 5 steps, taking images at each point.",
                expected_output=registry.context_types.SCAN_PLAN_CONTEXT,
                success_criteria="Scan completes successfully and returns run_uid for data analysis.",
                inputs={
                    "MOTOR_NAME": "gi_angle",
                    "START_POSITION": 0.1,
                    "STOP_POSITION": 0.2,
                    "NUM_POINTS": 5,
                    "DETECTORS": ["det"]
                }
            ),
            scenario_description="User asks to take images at multiple grazing incidence angles.",
            notes="The planner must extract motor name, start/stop positions, number of points, and which detectors to use from the user's query."
        )

        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="height_scan_image",
                capability="bl531_scan",
                task_objective="Scan height 0.1 to 0.2 in 5 steps, taking images at each point.",
                expected_output=registry.context_types.SCAN_PLAN_CONTEXT,
                success_criteria="Scan completes successfully and returns run_uid for data analysis.",
                inputs={
                    "MOTOR_NAME": "hexapod_motor_Tz",
                    "START_POSITION": 0.1,
                    "STOP_POSITION": 0.2,
                    "NUM_POINTS": 5,
                    "DETECTORS": ["det"]
                }
            ),
            scenario_description="User asks to take images at multiple specimen height.",
            notes="The planner must extract motor name, start/stop positions, number of points, and which detectors to use from the user's query."
        )

        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="incidence_angle_scan_diode",
                capability="bl531_scan",
                task_objective="Scan angle 0.1 to 0.2 in 5 steps, taking diode value at each point.",
                expected_output=registry.context_types.SCAN_PLAN_CONTEXT,
                success_criteria="Scan completes successfully and returns run_uid for data analysis.",
                inputs={
                    "MOTOR_NAME": "gi_angle",
                    "START_POSITION": 0.1,
                    "STOP_POSITION": 0.2,
                    "NUM_POINTS": 5,
                    "DETECTORS": ["diode"]
                }
            ),
            scenario_description="User asks to take diode value at multiple grazing incidence angles.",
            notes="The planner must extract motor name, start/stop positions, number of points, and which detectors to use from the user's query."
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **When to plan "bl531_scan" steps:**
                - User asks to scan a motor through a range of positions
                - User requests measurements at multiple angles or positions
                - User wants GISAXS or grazing incidence measurements at different angles
                
                **Inputs:**
                You MUST populate the `inputs` field with these keys:
                - `MOTOR_NAME`: Motor to scan. Choose from:
                  * "gi_angle" for grazing angle, incidence angle, tilt, rotation
                  * "hexapod_motor_Ty" for lateral position, horizontal movement
                  * "hexapod_motor_Tz" for vertical position, height
                - `START_POSITION`: Numerical starting value for the scan
                - `STOP_POSITION`: Numerical ending value for the scan
                - `NUM_POINTS`: Number of measurement points (integer)
                - `DETECTORS`: List of detectors. Options:
                  * ["det"] for images/camera
                  * ["diode"] for beam intensity
                  * ["diode", "det"] for both
                
                **Translation Examples:**
                "GISAXS from 0.1 to 0.2 in 5 steps"
                → MOTOR_NAME: "gi_angle", START: 0.1, STOP: 0.2, NUM: 5, DETECTORS: ["det"]
                
                "Scan Ty from 0 to 0.3, 10 points"
                → MOTOR_NAME: "hexapod_motor_Ty", START: 0.0, STOP: 0.3, NUM: 10, DETECTORS: ["det"]
                
                "Images at angles 0.12, 0.15, 0.18"
                → MOTOR_NAME: "gi_angle", START: 0.12, STOP: 0.18, NUM: 3, DETECTORS: ["det"]
                
                **Output:**
                Produces a SCAN_PLAN_CONTEXT object containing run_uid for data retrieval.
                """),
            examples=[example1, example2, example3],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Determine if the user wants to SCAN a motor through a range of positions while taking measurements.",
            examples=[
                ClassifierExample(
                    query="Take images at grazing incidence angles from 0.1 to 0.2 in 5 steps",
                    result=True,
                    reason="Request to scan through multiple angles while taking images."
                ),
                ClassifierExample(
                    query="GISAXS at 0.12, 0.15, 0.18 degrees",
                    result=True,
                    reason="Multiple measurement points - requires scanning from 0.12 to 0.18."
                ),
                ClassifierExample(
                    query="Scan Ty from 0 to 0.3 in 10 steps",
                    result=True,
                    reason="Explicit scan command with range and number of points."
                ),
                ClassifierExample(
                    query="Move Ry to 0.15",
                    result=False,
                    reason="Single position movement, not a scan."
                ),
                ClassifierExample(
                    query="What is the current motor position?",
                    result=False,
                    reason="Request to READ data, not scan."
                ),
                ClassifierExample(
                    query="Take one image",
                    result=False,
                    reason="Single measurement, use count plan instead."
                ),
            ],
            actions_if_true=ClassifierActions()
        )