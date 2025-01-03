import requests
import json
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import google.generativeai as genai
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlencode
import time
from difflib import SequenceMatcher
import tempfile
import os
import re
