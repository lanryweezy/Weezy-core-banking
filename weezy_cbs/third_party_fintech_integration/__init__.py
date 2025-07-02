# third_party_fintech_integration module

# This module will contain services and configurations for integrating with
# various third-party fintech services beyond standard payment gateways.
# Examples: Credit Bureaus, NIMC (for identity), Bill Payment Aggregators (if not in payments),
# External Loan Originators, BaaS partner APIs.

from . import models # For API logs, partner configs, webhook logs specific to these integrations
from . import schemas # For request/response structures with these third parties
from . import services # Clients for each third-party service
from . import api # Endpoints for webhooks or admin config

# __all__ = ['models', 'schemas', 'services', 'api']
