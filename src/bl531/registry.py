"""
BL531 Application Registry.

This registry registers all BL531-specific capabilities and context classes
with the Alpha Berkeley Framework. It uses the COMPACT style which automatically
includes framework capabilities (routing, memory, Python, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BL531 COMPONENTS REGISTERED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAPABILITIES:
  - bl531_count: Execute count plan (read detectors n times)
  - bl531_scan: Execute scan plan (scan motor while reading detectors)
  - bl531_gisaxs_alignment: Execute automatic GISAXS alignment

CONTEXT CLASSES:
  - COUNT_PLAN_CONTEXT: Output from count capability
  - SCAN_PLAN_CONTEXT: Output from scan capability
  - GISAXS_ALIGNMENT_CONTEXT: Output from alignment capability

FRAMEWORK CAPABILITIES (Automatic):
  - routing: Routes tasks to appropriate capabilities
  - memory: Short and long-term memory management
  - python: Execute Python code for data analysis
  - classifier: Classify tasks to determine required capabilities
  - respond: Communicate results to user

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from osprey.registry import (
    extend_framework_registry,
    CapabilityRegistration,
    ContextClassRegistration,
    RegistryConfig,
    RegistryConfigProvider
)


class Bl531RegistryProvider(RegistryConfigProvider):
    """Registry provider for BL531 beamline application.
    
    Registers all BL531-specific capabilities and context classes.
    The framework discovers and uses this class at startup.
    """
    
    def get_registry_config(self) -> RegistryConfig:
        """Get application registry configuration.
        
        Returns:
            RegistryConfig: Complete registry with framework + BL531 components
        """
        
        return extend_framework_registry(
            
            # ┌────────────────────────────────────────────────────────────┐
            # │ CAPABILITIES: BL531 Beamline Control Plans                 │
            # └────────────────────────────────────────────────────────────┘
            
            capabilities=[
                
                # ────────────────────────────────────────────────────────
                # COUNT CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes a count plan: reads detectors n times
                # No motor movement, just detector readings or image capture
                CapabilityRegistration(
                    name="bl531_count",
                    module_path="bl531.capabilities.count_capability",
                    class_name="CountCapability",
                    description="Execute a count plan on BL531 beamline - read detectors or take images without moving motors",
                    provides=["COUNT_PLAN_CONTEXT"],
                    requires=["DETECTORS", "NUM_READINGS"]  # Orchestrator provides these inputs
                ),

                # ────────────────────────────────────────────────────────
                # SCAN CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes a scan plan: scans a motor while reading detectors
                # Returns run_uid for accessing scan data
                CapabilityRegistration(
                    name="bl531_scan",
                    module_path="bl531.capabilities.scan_capability",
                    class_name="ScanCapability",
                    description="Execute a scan plan on BL531 beamline - scan motor while reading detectors",
                    provides=["SCAN_PLAN_CONTEXT"],
                    requires=["MOTOR_NAME", "START_POSITION", "STOP_POSITION", "NUM_POINTS", "DETECTORS"]  # Orchestrator provides these inputs
                ),
                
                # ────────────────────────────────────────────────────────
                # GISAXS ALIGNMENT CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes automatic GISAXS alignment
                # Finds reference zero angle of Ry motor
                # CapabilityRegistration(
                #     name="bl531_gisaxs_alignment",
                #     module_path="bl531.capabilities.gisaxs_alignment_capability",
                #     class_name="GisaxsAlignmentCapability",
                #     description="Execute automatic GISAXS alignment on BL531 beamline - find reference zero angle",
                #     provides=["GISAXS_ALIGNMENT_CONTEXT"],
                #     requires=[]
                # ),
                
            ],
            
            # ┌────────────────────────────────────────────────────────────┐
            # │ CONTEXT CLASSES: Data structures for capability outputs    │
            # └────────────────────────────────────────────────────────────┘
            
            context_classes=[
                
                # ────────────────────────────────────────────────────────
                # COUNT PLAN CONTEXT
                # ────────────────────────────────────────────────────────
                # Output from count capability
                # Contains: run_uid, detectors, num_readings, status
                ContextClassRegistration(
                    context_type="COUNT_PLAN_CONTEXT",
                    module_path="bl531.context_classes",
                    class_name="CountPlanContext"
                ),
                
                # ────────────────────────────────────────────────────────
                # SCAN PLAN CONTEXT
                # ────────────────────────────────────────────────────────
                # Output from scan capability
                # Contains: run_uid, motor, start, stop, num_points, detectors, status
                ContextClassRegistration(
                    context_type="SCAN_PLAN_CONTEXT",
                    module_path="bl531.context_classes",
                    class_name="ScanPlanContext"
                ),
                
                # ────────────────────────────────────────────────────────
                # GISAXS ALIGNMENT CONTEXT
                # ────────────────────────────────────────────────────────
                # Output from alignment capability
                # Contains: run_uid, status, timestamp
                # ContextClassRegistration(
                #     context_type="GISAXS_ALIGNMENT_CONTEXT",
                #     module_path="bl531.context_classes",
                #     class_name="GisaxsAlignmentContext"
                # ),
                ContextClassRegistration(
                    context_type="SCAN_PARAMETERS",
                    module_path="bl531.context_classes",
                    class_name="ScanParametersContext"
                ),
            ],
            
            # No data sources needed for BL531 (pure control API)
            data_sources=[],
            
            # No custom prompt providers needed
            framework_prompt_providers=[],
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USAGE NOTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# WHAT GETS REGISTERED:
#
# Capabilities (3):
#   1. bl531_count - Read detectors (no motor movement)
#   2. bl531_scan - Scan motor while reading detectors
#   3. bl531_gisaxs_alignment - Automatic alignment procedure
#
# Context Classes (3):
#   1. CountPlanContext - Stores count plan execution details
#   2. ScanPlanContext - Stores scan plan execution details
#   3. GisaxsAlignmentContext - Stores alignment plan details
#
# Framework Capabilities (Automatic, ~6):
#   - routing: Task routing between capabilities
#   - memory: Context memory management
#   - python: Python code execution for analysis
#   - classifier: Task classification and planning
#   - respond: Communicate with user
#   - user_approval: Request user confirmation (if needed)
#
# DATA FLOW:
#
#   User Query
#       ↓
#   Classifier → Determine which capability(ies) to use
#       ↓
#   Router → Route to bl531_count / bl531_scan / bl531_gisaxs_alignment
#       ↓
#   BL531 Capability → Submit plan, get run_uid
#       ↓
#   Context Store → Save COUNT_PLAN_CONTEXT / SCAN_PLAN_CONTEXT / etc
#       ↓
#   Memory → Store run_uid for future reference
#       ↓
#   Respond → Tell user about the submitted plan
#
# ANALYSIS WORKFLOW (User's responsibility):
#   After capability returns run_uid:
#       run_uid → Data retrieval tool → Access Tiled data store
#       ↓
#       Analyze detector readings / motor positions / images
#       ↓
#       Return analysis results
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTING THE REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# To verify registry is configured correctly:
#
# >>> from osprey.registry import get_registry
# >>> registry = get_registry()
#
# # Check capabilities
# >>> caps = [c.name for c in registry.capabilities]
# >>> print(caps)
# ['routing', 'memory', 'python', 'classifier', 'respond', 
#  'bl531_count', 'bl531_scan', 'bl531_gisaxs_alignment']
#
# # Check context types
# >>> contexts = [ct for ct in dir(registry.context_types) 
# ...              if not ct.startswith('_')]
# >>> print(contexts)
# ['COUNT_PLAN_CONTEXT', 'SCAN_PLAN_CONTEXT', 'GISAXS_ALIGNMENT_CONTEXT', ...]
#
# # Run the application
# >>> framework chat
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXAMPLE CONVERSATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# User: "Take a measurement with the diode detector"
#
# System:
#   1. Classifier: Recognizes this is a count plan request
#   2. Router: Routes to bl531_count capability
#   3. Count: Submits count plan (detectors=["diode"], num=1)
#   4. Context: Stores CountPlanContext with run_uid
#   5. Memory: Saves run_uid for reference
#   6. Respond: Tells user "Measurement submitted with run_uid: abc123..."
#
# User: "Scan Ty from 0 to 0.3 in 10 points"
#
# System:
#   1. Classifier: Recognizes this is a scan plan request
#   2. Router: Routes to bl531_scan capability
#   3. Scan: Submits scan plan (motor, start, stop, num)
#   4. Context: Stores ScanPlanContext with run_uid
#   5. Memory: Saves run_uid for reference
#   6. Respond: Tells user "Scan submitted with run_uid: def456..."
#
# User: "Align the beamline"
#
# System:
#   1. Classifier: Recognizes this is an alignment request
#   2. Router: Routes to bl531_gisaxs_alignment capability
#   3. Alignment: Submits alignment plan
#   4. Context: Stores GisaxsAlignmentContext with run_uid
#   5. Memory: Saves run_uid for reference
#   6. Respond: Tells user "Alignment submitted with run_uid: ghi789..."
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━