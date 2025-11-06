"""
Count Plan Capability for BL531 Beamline.

Executes a count plan to read detectors n times.
Can also be used to take single images.
"""

from typing import Dict, Any, Optional
import textwrap
from datetime import datetime

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

from bl531.context_classes import CountPlanContext
from bl531.BL531API import bl531

logger = get_logger("count_capability")
registry = get_registry()


class CountCapabilityError(Exception):
    """Base exception for count capability."""
    pass


class InvalidDetectorError(CountCapabilityError):
    """Raised when invalid detector is specified."""
    pass


class PlanExecutionError(CountCapabilityError):
    """Raised when plan execution fails."""
    pass


@capability_node
class CountCapability(BaseCapability):
    """Execute a count plan on the BL531 beamline.
    
    Reads detectors n times and returns the run_uid for data analysis.
    Can also be used to take single images with the detector.
    """
    
    name = "bl531_count"
    description = "Execute a count plan to read detectors n times on BL531 beamline (can also take single images)"
    provides = ["COUNT_PLAN_CONTEXT"]
    # Orchestrator must provide these inputs
    requires = ["DETECTORS", "NUM_READINGS"]
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute count plan using inputs from orchestrator."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("count_capability", state)
        
        try:
            # Extract inputs from orchestrator (same pattern as scan)
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
            detectors = combined_inputs.get("DETECTORS")
            num = combined_inputs.get("NUM_READINGS")
            
            # Convert to proper types
            num = int(num)
            
            # Parse detectors - orchestrator might send as string representation
            if isinstance(detectors, str):
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
            
            context_key = step.get("context_key", "count_result")
            
            logger.info(f"📊 Executing count plan: detectors={detectors}, num={num}")
            streamer.status(f"Reading detectors {detectors} {num} time(s)...")
            
            # Call API to submit plan
            result = bl531.count(detectors=detectors, num=num)
            
            logger.info(f"✅ Count plan completed. run_uid: {result.run_uid}")
            streamer.status(f"Count completed with run_uid: {result.run_uid}")
            
            # Create output context
            context = CountPlanContext(
                run_uid=result.run_uid,
                detectors=detectors,
                num_readings=num,
                timestamp=result.timestamp,
                status="completed"
            )
            
            # Store context and return
            context_updates = StateManager.store_context(
                state,
                registry.context_types.COUNT_PLAN_CONTEXT,
                context_key,
                context
            )
            
            return context_updates
            
        except Exception as e:
            logger.error(f"Count execution error: {e}")
            raise
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify count errors for intelligent retry coordination."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid count parameters: {str(exc)}",
                metadata={"type": "invalid_parameter"}
            )
        elif isinstance(exc, InvalidDetectorError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid detector specified: {str(exc)}",
                metadata={"type": "invalid_detector"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Count execution error: {str(exc)}",
                metadata={"type": "execution_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="beam_intensity",
                capability="bl531_count",
                task_objective="Measure beam intensity using diode detector.",
                expected_output=registry.context_types.COUNT_PLAN_CONTEXT,
                success_criteria="Successfully reads diode value and returns run_uid.",
                inputs={
                    "DETECTORS": ["diode"],
                    "NUM_READINGS": ['1'],
                }
            ),
            scenario_description="User wants to measure beam intensity or beam current.",
            notes="IMPORTANT: Use 'diode' ONLY for intensity/current measurements, NOT for images."
        )
        
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="single_image",
                capability="bl531_count",
                task_objective="Take a single scattering image with the detector.",
                expected_output=registry.context_types.COUNT_PLAN_CONTEXT,
                success_criteria="Successfully captures one scattering image and returns run_uid.",
                inputs={
                    "DETECTORS": ["det"],
                    "NUM_READINGS": ['1'],
                }
            ),
            scenario_description="User wants to take an image or capture scattering pattern.",
            notes="IMPORTANT: Use 'det' for ALL image-related requests (scattering images, direct beam images, pictures)."
        )
        
        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="three_images",
                capability="bl531_count",
                task_objective="Take three scattering images with the detector.",
                expected_output=registry.context_types.COUNT_PLAN_CONTEXT,
                success_criteria="Successfully captures three images and returns run_uid.",
                inputs={
                    "DETECTORS": ["det"],
                    "NUM_READINGS": ['3'],
                }
            ),
            scenario_description="User wants to take multiple images at the current position.",
            notes="IMPORTANT: Use 'det' for images, NOT 'diode'. Set NUM_READINGS to the number of images requested."
        )
        
        example4 = OrchestratorExample(
            step=PlannedStep(
                context_key="multiple_readings",
                capability="bl531_count",
                task_objective="Take 5 intensity readings with diode.",
                expected_output=registry.context_types.COUNT_PLAN_CONTEXT,
                success_criteria="Successfully reads diode 5 times and returns run_uid.",
                inputs={
                    "DETECTORS": ["diode"],
                    "NUM_READINGS": ['5'],
                }
            ),
            scenario_description="User wants multiple intensity measurements.",
            notes="IMPORTANT: Use 'diode' for intensity, 'det' for images. Never mix them up."
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **When to plan "bl531_count" steps:**
                - User wants to read detector values without moving motors
                - User wants to measure beam intensity
                - User wants to take image(s) at current position
                - User asks to "count", "read", "measure", or "take image"
                
                **CRITICAL DETECTOR SELECTION RULES:**
                
                ⚠️  **DETECTOR "det" (Pilatus area detector):**
                - Use for: images, pictures, scattering patterns, scattering images, direct beam images
                - Use for: ANY request mentioning "image", "picture", "pattern", "scattering"
                - This is an AREA DETECTOR that captures 2D images
                - Examples: "take an image", "capture scattering", "take 3 images", "get a picture"
                
                ⚠️  **DETECTOR "diode" (Intensity Monitor):**
                - Use for: beam intensity, beam current, intensity measurements
                - Use for: ANY request about "intensity", "current", "flux"
                - This is a SINGLE-VALUE detector (not an image)
                - Examples: "measure intensity", "read beam current", "check intensity"
                
                **NEVER use 'diode' for images! NEVER use 'det' for intensity!**
                
                **Inputs:**
                You MUST populate the `inputs` field with these keys:
                - `DETECTORS`: List of detectors to read
                * ["det"] - For ALL image-related requests (scattering, direct beam, pictures)
                * ["diode"] - For intensity/current measurements ONLY
                * ["diode", "det"] - For both simultaneously (rare)
                - `NUM_READINGS`: Number of times to read (integer, default: 1)
                * Use 1 for single measurement or single image
                * Use N for N repeated readings/images
                
                **Translation Examples:**
                
                "Measure beam intensity"
                → DETECTORS: ["diode"], NUM_READINGS: ['1']
                
                "Take an image"
                → DETECTORS: ["det"], NUM_READINGS: ['1']
                
                "Take 3 images"
                → DETECTORS: ["det"], NUM_READINGS: ['3']
                
                "Capture scattering pattern"
                → DETECTORS: ["det"], NUM_READINGS: ['1']
                
                "Take 5 measurements with diode"
                → DETECTORS: ["diode"], NUM_READINGS: ['5']
                
                "Get direct beam image"
                → DETECTORS: ["det"], NUM_READINGS: ['1']
                
                **Common Mistakes to Avoid:**
                ❌ WRONG: "take 3 images" → ["diode"]
                ✅ RIGHT: "take 3 images" → ["det"], NUM_READINGS: ['3']
                
                ❌ WRONG: "measure intensity" → ["det"]
                ✅ RIGHT: "measure intensity" → ["diode"], NUM_READINGS: ['1']
                
                **Important:**
                - For images at CURRENT position: use bl531_count
                - For images at MULTIPLE positions: use bl531_scan
                - Count plan does NOT move motors
                
                **Output:**
                Produces a COUNT_PLAN_CONTEXT object containing run_uid for data retrieval.
                """),
            examples=[example1, example2, example3, example4],
            priority=10
        )

    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Determine if the user wants to READ detectors OR take images at the current position (without scanning motors).",
            examples=[
                ClassifierExample(
                    query="Take a measurement with the diode detector",
                    result=True,
                    reason="Single intensity reading at current position - use count with diode."
                ),
                ClassifierExample(
                    query="Read beam intensity",
                    result=True,
                    reason="Measure intensity using diode - use count."
                ),
                ClassifierExample(
                    query="Take an image",
                    result=True,
                    reason="Single image at current position - use count with det."
                ),
                ClassifierExample(
                    query="Take 3 images",
                    result=True,
                    reason="Multiple images at current position - use count with det, num=3."
                ),
                ClassifierExample(
                    query="Capture scattering pattern",
                    result=True,
                    reason="Take scattering image - use count with det."
                ),
                ClassifierExample(
                    query="Get direct beam image",
                    result=True,
                    reason="Image capture - use count with det."
                ),
                ClassifierExample(
                    query="What is the current diode reading",
                    result=True,
                    reason="Read current intensity - use count with diode."
                ),
                ClassifierExample(
                    query="Scan motor from 0.1 to 0.2 taking images",
                    result=False,
                    reason="Images at multiple positions - use bl531_scan instead."
                ),
                ClassifierExample(
                    query="Take images at different angles",
                    result=False,
                    reason="Multiple positions - use bl531_scan instead."
                ),
                ClassifierExample(
                    query="Align the beamline",
                    result=False,
                    reason="Alignment procedure - use alignment capability."
                ),
            ],
            actions_if_true=ClassifierActions()
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Determine if the user wants to READ detectors at the current position (without scanning).",
            examples=[
                ClassifierExample(
                    query="Take a measurement with the diode detector",
                    result=True,
                    reason="Single reading of diode at current position."
                ),
                ClassifierExample(
                    query="Read beam intensity",
                    result=True,
                    reason="Measure intensity using diode - no motor movement."
                ),
                ClassifierExample(
                    query="Take an image",
                    result=True,
                    reason="Single image capture at current position using det."
                ),
                ClassifierExample(
                    query="Take 5 measurements of both detectors",
                    result=True,
                    reason="Multiple readings at current position - use count."
                ),
                ClassifierExample(
                    query="What is the current diode reading",
                    result=True,
                    reason="Read current value - use count plan."
                ),
                ClassifierExample(
                    query="Scan the motor from 0.1 to 0.2",
                    result=False,
                    reason="Motor scanning - use bl531_scan instead."
                ),
                ClassifierExample(
                    query="Take images at different angles",
                    result=False,
                    reason="Multiple positions - use bl531_scan instead."
                ),
                ClassifierExample(
                    query="Align the beamline",
                    result=False,
                    reason="Alignment procedure - use alignment capability."
                ),
            ],
            actions_if_true=ClassifierActions()
        )