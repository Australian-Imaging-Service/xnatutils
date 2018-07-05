"""
XNAT-Utils

Copyright (c) 2012-2017 Thomas G. Close, Monash Biomedical Imaging,
Monash University, Melbourne, Australia

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from .version_ import __version__
from .base import connect, print_usage_error, print_response_error, print_info_message
from .get import get, varget
from .put import put, varput
from .ls import ls
from .misc import rename

