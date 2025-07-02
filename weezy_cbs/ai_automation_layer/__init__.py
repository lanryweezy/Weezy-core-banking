# ai_automation_layer module

# This module will contain services and configurations for AI models,
# ML-driven fraud detection, LLM task automation, chatbots, etc.
# It might interact with many other modules to provide AI capabilities.

from . import models # For AI model configs, agent action logs, fraud rule parameters
from . import schemas # For interacting with AI services or configuring them
from . import services # Services that invoke AI models or manage AI agents
from . import api # Endpoints for triggering AI tasks, getting predictions, or admin config

# __all__ = ['models', 'schemas', 'services', 'api']
