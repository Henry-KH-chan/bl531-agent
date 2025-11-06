"""
BL531 Beamline Context Classes.

These define the data structures that capabilities exchange and store in agent state.
Each context class represents a distinct data type returned by beamline operations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT CLASSES FOR BL531:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CountPlanContext
   - Returned by: count() plan submission
   - Contains: run_uid, detector info, status
   - Use: For accessing measurement data after execution

2. ScanPlanContext
   - Returned by: scan() plan submission
   - Contains: run_uid, motor info, range, num points, status
   - Use: For analyzing scan data after execution

3. GisaxsAlignmentContext
   - Returned by: automatic_gisaxs_alignment() plan submission
   - Contains: run_uid, status, timestamp
   - Use: For processing alignment results after execution

All contexts return run_uid which can be used to retrieve and analyze actual data.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, ClassVar
from pydantic import Field
from osprey.context.base import CapabilityContext

class ScanParametersContext(CapabilityContext):
    """Parameters for executing a scan plan.
    
    The LLM orchestrator extracts these from the user query and creates
    this context, which the scan capability then consumes.
    """
    
    CONTEXT_TYPE: ClassVar[str] = "SCAN_PARAMETERS"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    motor: str = Field(
        description="Motor to scan: 'hexapod_motor_Ry', 'hexapod_motor_Ty', or 'hexapod_motor_Tz'"
    )
    
    start: float = Field(
        description="Starting position for the scan"
    )
    
    stop: float = Field(
        description="Ending position for the scan"
    )
    
    num_points: int = Field(
        description="Number of measurement points in the scan"
    )
    
    detectors: List[str] = Field(
        default_factory=lambda: ["det"],
        description="List of detectors to read: ['diode'], ['det'], or ['diode', 'det']"
    )
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.SCAN_PARAMETERS.{key_ref}",
            "available_fields": ["motor", "start", "stop", "num_points", "detectors"],
            "example_usage": f"""# Access scan parameters
motor = context.SCAN_PARAMETERS.{key_ref}.motor
start = context.SCAN_PARAMETERS.{key_ref}.start
stop = context.SCAN_PARAMETERS.{key_ref}.stop
num_points = context.SCAN_PARAMETERS.{key_ref}.num_points
detectors = context.SCAN_PARAMETERS.{key_ref}.detectors""",
            "data_structure": "Single parameter set for one scan operation"
        }
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate human-readable summary."""
        return {
            "type": "Scan Parameters",
            "motor": self.motor,
            "scan_range": f"{self.start} to {self.stop}",
            "num_points": self.num_points,
            "detectors": ", ".join(self.detectors)
        }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COUNT PLAN CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CountPlanContext(CapabilityContext):
    """Context for count plan execution on BL531 beamline.
    
    A count plan reads detectors n times without moving any motors.
    This context stores the run_uid and execution details.
    
    Use case: Get beam intensity measurements, detector readings, etc.
    
    Example:
        result = context.COUNT_PLAN_CONTEXT.diode_reading
        print(f"Run UID: {result.run_uid}")
        print(f"Detectors: {result.detectors}")
        print(f"Readings: {result.num_readings}")
    """
    
    CONTEXT_TYPE: ClassVar[str] = "COUNT_PLAN_CONTEXT"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    # ────────────────────────────────────────────────────────────────────────
    # Data Fields
    # ────────────────────────────────────────────────────────────────────────
    
    run_uid: str = Field(
        description="Unique identifier for this measurement run. Use this to retrieve actual measurement data."
    )
    
    detectors: List[str] = Field(
        description="List of detectors that were read (e.g., ['diode', 'det'])"
    )
    
    num_readings: int = Field(
        description="Number of readings taken for each detector"
    )
    
    timestamp: datetime = Field(
        description="When this count plan was submitted (ISO format)"
    )
    
    status: str = Field(
        default="completed",
        description="Execution status: 'submitted', 'completed', or 'failed'"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is 'failed', None otherwise"
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # Access Details for LLM
    # ────────────────────────────────────────────────────────────────────────
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM code generation."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.COUNT_PLAN_CONTEXT.{key_ref}",
            
            "available_fields": [
                "run_uid",
                "detectors", 
                "num_readings",
                "timestamp",
                "status",
                "error_message"
            ],
            
            "example_usage": f"""# Get the run UID for data analysis
run_uid = context.COUNT_PLAN_CONTEXT.{key_ref}.run_uid

# Check which detectors were used
detectors = context.COUNT_PLAN_CONTEXT.{key_ref}.detectors

# Get execution timestamp
timestamp = context.COUNT_PLAN_CONTEXT.{key_ref}.timestamp

# Verify successful execution
if context.COUNT_PLAN_CONTEXT.{key_ref}.status == "completed":
    print(f"Measurement successful with run_uid: {{run_uid}}")
else:
    print(f"Error: {{context.COUNT_PLAN_CONTEXT.{key_ref}.error_message}}")""",
            
            "data_structure": (
                "Single measurement record. "
                "Use run_uid to retrieve actual detector readings from data storage."
            ),
            
            "important_notes": [
                "run_uid is the key to accessing actual measurement data",
                "timestamp is when the plan was submitted, not when readings were taken",
                "status is always 'completed' if no error_message",
                "detectors list shows which instruments were read"
            ]
        }
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate human-readable summary."""
        return {
            "type": "Count Plan Measurement",
            "run_uid": self.run_uid,
            "detectors": ", ".join(self.detectors),
            "readings_per_detector": self.num_readings,
            "submission_time": self.timestamp.isoformat(),
            "status": self.status,
            "error": self.error_message or "None"
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCAN PLAN CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ScanPlanContext(CapabilityContext):
    """Context for scan plan execution on BL531 beamline.
    
    A scan plan moves a motor through a range while reading detectors.
    This context stores the run_uid and scan parameters.
    
    Use case: Map detector response vs motor position, alignment scans, etc.
    
    Example:
        result = context.SCAN_PLAN_CONTEXT.my_scan
        print(f"Scanned motor: {result.motor}")
        print(f"Range: {result.start} to {result.stop}")
        print(f"Points: {result.num_points}")
    """
    
    CONTEXT_TYPE: ClassVar[str] = "SCAN_PLAN_CONTEXT"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    # ────────────────────────────────────────────────────────────────────────
    # Data Fields
    # ────────────────────────────────────────────────────────────────────────
    
    run_uid: str = Field(
        description="Unique identifier for this scan run. Use this to retrieve scan data and motor positions."
    )
    
    motor: str = Field(
        description="Motor that was scanned (e.g., 'hexapod_motor_Ty')"
    )
    
    start: float = Field(
        description="Starting position of the scan"
    )
    
    stop: float = Field(
        description="Ending position of the scan"
    )
    
    num_points: int = Field(
        description="Number of measurement points in the scan"
    )
    
    detectors: List[str] = Field(
        description="List of detectors read at each scan point (e.g., ['diode', 'det'])"
    )
    
    timestamp: datetime = Field(
        description="When this scan plan was submitted (ISO format)"
    )
    
    status: str = Field(
        default="completed",
        description="Execution status: 'submitted', 'completed', or 'failed'"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is 'failed', None otherwise"
    )
    
    # ────────────────────────────────────────────────────────────────────────
    # Access Details for LLM
    # ────────────────────────────────────────────────────────────────────────
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM code generation."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.SCAN_PLAN_CONTEXT.{key_ref}",
            
            "available_fields": [
                "run_uid",
                "motor",
                "start",
                "stop", 
                "num_points",
                "detectors",
                "timestamp",
                "status",
                "error_message"
            ],
            
            "example_usage": f"""# Get scan identification
run_uid = context.SCAN_PLAN_CONTEXT.{key_ref}.run_uid
motor = context.SCAN_PLAN_CONTEXT.{key_ref}.motor

# Get scan parameters
start = context.SCAN_PLAN_CONTEXT.{key_ref}.start
stop = context.SCAN_PLAN_CONTEXT.{key_ref}.stop
num_points = context.SCAN_PLAN_CONTEXT.{key_ref}.num_points

# Get detector information
detectors = context.SCAN_PLAN_CONTEXT.{key_ref}.detectors

# Create scan description
print(f"{{motor}} scan: {{start}} to {{stop}} in {{num_points}} steps")
print(f"Detectors: {{', '.join(detectors)}}")
print(f"Run UID: {{run_uid}}")""",
            
            "data_structure": (
                "Single scan record with motor parameters and detector list. "
                "Use run_uid to retrieve motor positions and detector readings."
            ),
            
            "important_notes": [
                "run_uid is required to access actual scan data",
                "Motor moves from start to stop in num_points steps",
                "Each step reads all detectors in the list",
                "Position range is: start <= position <= stop"
            ]
        }
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate human-readable summary."""
        return {
            "type": "Scan Plan Measurement",
            "run_uid": self.run_uid,
            "motor_scanned": self.motor,
            "scan_range": f"{self.start} to {self.stop}",
            "measurement_points": self.num_points,
            "detectors": ", ".join(self.detectors),
            "submission_time": self.timestamp.isoformat(),
            "status": self.status,
            "error": self.error_message or "None"
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GISAXS ALIGNMENT CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# class GisaxsAlignmentContext(CapabilityContext):
#     """Context for automatic GISAXS alignment on BL531 beamline.
    
#     An alignment plan automatically finds the reference zero angle of the Ry motor.
#     This context stores the run_uid for accessing alignment results.
    
#     Use case: Prepare beamline for GISAXS measurements, set reference angle.
    
#     Example:
#         result = context.GISAXS_ALIGNMENT_CONTEXT.alignment
#         print(f"Alignment run: {result.run_uid}")
#         print(f"Status: {result.status}")
#     """
    
#     CONTEXT_TYPE: ClassVar[str] = "GISAXS_ALIGNMENT_CONTEXT"
#     CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
#     # ────────────────────────────────────────────────────────────────────────
#     # Data Fields
#     # ────────────────────────────────────────────────────────────────────────
    
#     run_uid: str = Field(
#         description="Unique identifier for this alignment run. Use to retrieve alignment results and reference angle."
#     )
    
#     timestamp: datetime = Field(
#         description="When this alignment plan was submitted (ISO format)"
#     )
    
#     status: str = Field(
#         default="completed",
#         description="Execution status: 'submitted', 'completed', or 'failed'"
#     )
    
#     error_message: Optional[str] = Field(
#         default=None,
#         description="Error details if status is 'failed', None otherwise"
#     )
    
#     # ────────────────────────────────────────────────────────────────────────
#     # Access Details for LLM
#     # ────────────────────────────────────────────────────────────────────────
    
#     def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
#         """Provide access information for LLM code generation."""
#         key_ref = key_name if key_name else "key_name"
        
#         return {
#             "access_pattern": f"context.GISAXS_ALIGNMENT_CONTEXT.{key_ref}",
            
#             "available_fields": [
#                 "run_uid",
#                 "timestamp",
#                 "status",
#                 "error_message"
#             ],
            
#             "example_usage": f"""# Get alignment identification
# run_uid = context.GISAXS_ALIGNMENT_CONTEXT.{key_ref}.run_uid
# status = context.GISAXS_ALIGNMENT_CONTEXT.{key_ref}.status

# # Check if alignment was successful
# if status == "completed":
#     print(f"Alignment successful with run_uid: {{run_uid}}")
#     # Use run_uid to retrieve reference angle from data
# else:
#     error = context.GISAXS_ALIGNMENT_CONTEXT.{key_ref}.error_message
#     print(f"Alignment failed: {{error}}")""",
            
#             "data_structure": (
#                 "Simple alignment record. "
#                 "Use run_uid to retrieve reference angle and alignment data."
#             ),
            
#             "important_notes": [
#                 "run_uid is required to access alignment results",
#                 "Reference angle will be extracted from the run data",
#                 "Motor adjusted is: hexapod_motor_Ry",
#                 "status confirms successful alignment"
#             ]
#         }
    
#     def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
#         """Generate human-readable summary."""
#         return {
#             "type": "GISAXS Alignment",
#             "run_uid": self.run_uid,
#             "alignment_time": self.timestamp.isoformat(),
#             "status": self.status,
#             "motor_aligned": "hexapod_motor_Ry",
#             "error": self.error_message or "None"
#         }