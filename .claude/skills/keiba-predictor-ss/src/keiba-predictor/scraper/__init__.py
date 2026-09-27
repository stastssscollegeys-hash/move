"""keiba-predictor スクレイパーパッケージ"""

try:
    from .smartrc_api import SmartRCAPI
except ImportError:
    SmartRCAPI = None

try:
    from .smartrc import SmartRCScraper
except ImportError:
    SmartRCScraper = None

try:
    from .jra_bias import JRABiasScraper
except ImportError:
    JRABiasScraper = None

try:
    from .results import ResultsScraper
except ImportError:
    ResultsScraper = None

__all__ = ["SmartRCAPI", "SmartRCScraper", "JRABiasScraper", "ResultsScraper"]
