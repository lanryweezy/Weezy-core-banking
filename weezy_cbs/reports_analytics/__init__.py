# reports_analytics module

# This module might focus more on services for data aggregation and
# presenting data, rather than storing new primary data.
# However, it could store definitions of custom reports or saved queries.

from . import models # For report definitions, saved queries, dashboard configs
from . import schemas # For report request/response structures
from . import services # For generating reports/analytics from other modules' data
from . import api # For requesting reports or viewing dashboards

# __all__ = ['models', 'schemas', 'services', 'api']
