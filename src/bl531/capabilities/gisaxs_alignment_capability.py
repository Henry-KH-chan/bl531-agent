"""
GISAXS Alignment Capability for BL531 Beamline.

Executes automatic GISAXS alignment to find the reference zero angle.
This is a prerequisite for accurate grazing incidence measurements.
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

from bl531.context_classes import AlignmentContext
from bl531.BL531API import bl531

logger = get_logger("gisaxs_alignment_capability")
registry = get_registry()


class AlignmentCapabilityError(Exception):
    """Base exception for alignment capability."""
    pass


class AlignmentExecutionError(AlignmentCapabilityError):
    """Raised when alignment execution fails."""
    pass


@capability_node
class GISAXSAlignmentCapability(BaseCapability):
    """Execute automatic GISAXS alignment on the BL531 beamline.
    
    Finds the reference zero angle (critical angle) for grazing incidence measurements.
    This should typically be run before GISAXS scans to ensure accurate angle positioning.
    """
    
    name = "bl531_gisaxs_alignment"
    description = "Execute automatic GISAXS alignment to find reference zero angle"
    provides = ["ALIGNMENT_CONTEXT"]
    requires = []  # No inputs needed - fully automatic
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute automatic GISAXS alignment."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("gisaxs_alignment_capability", state)
        
        try:
            context_key = step.get("context_key", "alignment_result")
            
            logger.info("🎯 Starting automatic GISAXS alignment")
            streamer.status("Executing automatic GISAXS alignment procedure...")
            
            # Call API to submit alignment plan
            result = bl531.automatic_gisaxs_alignment()
            
            logger.info(f"✅ Alignment completed. run_uid: {result.run_uid}")
            streamer.status(f"Alignment completed with run_uid: {result.run_uid}")
            
            # Create and store output context
            context = AlignmentContext(
                run_uid=result.run_uid,
                alignment_type="automatic_gisaxs",
                timestamp=result.timestamp,
                status="completed"
            )
            
            return StateManager.store_context(
                state,
                registry.context_types.ALIGNMENT_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Alignment execution error: {e}")
            raise AlignmentExecutionError(f"GISAXS alignment failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify alignment errors for intelligent retry coordination."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout during alignment, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, AlignmentExecutionError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Alignment failed: {str(exc)}",
                metadata={"type": "alignment_failed"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Alignment error: {str(exc)}",
                metadata={"type": "unknown_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        # Example 1: Direct alignment request
        alignment_example = OrchestratorExample(
            step=PlannedStep(
                context_key="alignment_result",
                capability="bl531_gisaxs_alignment",
                task_objective="Execute automatic GISAXS alignment to find reference zero angle.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Alignment completes successfully and returns run_uid.",
                inputs={}  # No inputs required
            ),
            scenario_description="User: 'Align the beamline' or 'Find reference zero angle'",
            notes="No inputs needed - alignment is fully automatic."
        )
        
        # Example 2: Pre-GISAXS alignment
        pre_gisaxs_example = OrchestratorExample(
            step=PlannedStep(
                context_key="pre_scan_alignment",
                capability="bl531_gisaxs_alignment",
                task_objective="Perform alignment before GISAXS scan to ensure accurate angle positioning.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Alignment completes successfully.",
                inputs={}
            ),
            scenario_description="Alignment before GISAXS measurements",
            notes="Best practice: align before GISAXS scans for accurate results."
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **USE bl531_gisaxs_alignment FOR:**
                - Finding reference zero angle (critical angle)
                - Aligning the beamline before GISAXS measurements
                - Calibrating grazing incidence angle positioning
                
                **NO INPUTS REQUIRED:**
                This capability is fully automatic - no parameters needed.
                Just create a step with empty inputs: `inputs={}`
                
                **WHEN TO USE:**
                - User explicitly asks to "align" or "find reference angle"
                - Before GISAXS scans for best accuracy (optional but recommended)
                - After major beamline changes or sample mounting
                
                **IMPORTANT:**
                - Alignment must complete BEFORE any GISAXS scans
                - If user wants both alignment + scan, create TWO steps:
                  1. bl531_gisaxs_alignment (find reference)
                  2. bl531_scan (perform GISAXS)
                
                **EXAMPLE WORKFLOW:**
                User: "Align and then do GISAXS from 0.1 to 0.2"
                → Step 1: bl531_gisaxs_alignment (inputs={})
                → Step 2: bl531_scan (with GISAXS parameters)
                
                **OUTPUT:**
                Returns ALIGNMENT_CONTEXT with run_uid for the alignment procedure.
                """),
            examples=[alignment_example, pre_gisaxs_example],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Check if user wants to perform GISAXS alignment or find reference zero angle.",
            examples=[
                ClassifierExample(
                    query="Align the beamline",
                    result=True,
                    reason="Direct alignment request - use bl531_gisaxs_alignment"
                ),
                ClassifierExample(
                    query="Find reference zero angle",
                    result=True,
                    reason="Finding reference angle is alignment - use bl531_gisaxs_alignment"
                ),
                ClassifierExample(
                    query="Do GISAXS alignment",
                    result=True,
                    reason="Explicit GISAXS alignment request"
                ),
                ClassifierExample(
                    query="Calibrate grazing incidence angle",
                    result=True,
                    reason="Calibration requires alignment procedure"
                ),
                ClassifierExample(
                    query="Align and then scan from 0.1 to 0.2",
                    result=True,
                    reason="Includes alignment (will need scan step too)"
                ),
                ClassifierExample(
                    query="GISAXS from 0.1 to 0.2",
                    result=False,
                    reason="Just scanning, no alignment requested - use bl531_scan only"
                ),
                ClassifierExample(
                    query="What is the current angle?",
                    result=False,
                    reason="Question, not alignment command"
                ),
                ClassifierExample(
                    query="Take an image",
                    result=False,
                    reason="Image capture - use bl531_count"
                ),
            ],
            actions_if_true=ClassifierActions()
        )