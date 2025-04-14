from aidial_sdk import DIALApp
from aidial_sdk.telemetry.types import TelemetryConfig

from aidial_bing_grounding.bing_grounding import BingGroundingApplication
from aidial_bing_grounding.utils.log_config import configure_loggers

app = DIALApp(
    description="DIAL application implementing agent with Bing grounding",
    telemetry_config=TelemetryConfig(),
    add_healthcheck=True,
)

# NOTE: configuring logger after the DIAL telemetry is initialized,
# because it may have configured the root logger on its own via
# logging=True configuration.
configure_loggers()

app.add_chat_completion("{model_id}", BingGroundingApplication())
