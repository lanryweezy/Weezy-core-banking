# digital_channels_modules container module

# This module itself might not have direct models/services/api
# but will contain sub-modules for each digital channel.

# Example sub-modules (can be created as actual directories later):
# from . import internet_banking
# from . import mobile_banking
# from . import ussd_banking
# from . import agent_dashboard_channel
# from . import chatbot_integration

# For now, basic files for the main container if it were to have shared utilities.
from . import models # Shared models if any (e.g. user session, notification preferences)
from . import schemas # Shared schemas
from . import services # Shared services (e.g. multi-channel notification service)
from . import api # A root API for digital channels if needed, or just sub-routers included in main app

# __all__ = [...]
