from prompts._legacy_messages import *
from prompts.relevance_prompts import *
from prompts.router_prompts import *
from prompts.scan_prompts import *
from prompts.signpost_prompts import *
from prompts.update_prompts import *

__all__ = [name for name in globals() if name.isupper()]
