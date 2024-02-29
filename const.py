# KNOWN ATTRIBUTE NAMES
XES_TIME = "time:timestamp"
XES_NAME = "concept:name"
XES_LIFECYCLE = "lifecycle:transition"
XES_RESOURCE = "org:resource"
XES_GROUP = "org:group"
XES_ROLE = "org:role"
XES_CASE = "case:" + XES_NAME
# SEMANTIC ATTRIBUTES
OBJECT = "object:name"
ACTION = "action:name"
# STUFF THAT HAS TO BE THERE ON THE EVENT LEVEL
XES_BASIC = [XES_NAME, XES_TIME]
# CUSTOM ATTRIBUTES RELATED TO TIME
SINCE_START = "time:since:start"
SINCE_LAST = "time:since:last"
WEEKDAY = "time:weekday"
DAY = "time:day"
# THE POSITION OF AN EVENT WITHIN A TRACE (CUSTOM ATTRIBUTE)
POS = "position"
# ATTRIBUTES RELATED TO TIME
TIME_ATTRIBUTES = [SINCE_LAST, SINCE_START, WEEKDAY, XES_TIME]

# MODES FOR CANDIDATE COMPUTATION (DEPENDS ON THE TYPE OF GUARANTEES,
# I.E. WHETHER THEY ARE MONOTONIC, ANTI-MONOTONIC OR NON-MONOTONIC)
ANTI_MONO = "anti-monotonic"
MONO = "monotonic"
NON_MONO = "non-monotonic"

GROUPING = "grouping"
CLASS_BASED = "classbased"
INSTANCE_BASED = "instancebased"

"""
Constraints are of shape (attribute | bound | aggregation function | target value)
"""
# NUMBER OF GROUPS, CAN BE USED TO PROVIDE A GUARANTEE ON THE ENTIRE GROUPING
NUM_GROUPS = "k"

# CANNOT-LINK, FOR THIS CONSTRAINT THE SECOND PARAMETER IS
# A COLLECTION OF PAIRS INDICATING WHICH CLASSES CANNOT BE GROUPED
CL = "cannotlink"

# MUST-LINK, FOR THIS CONSTRAINT THE SECOND PARAMETER IS
# A COLLECTION OF PAIRS INDICATING WHICH CLASSES MUST BE GROUPED
ML = "mustlink"

# BOUNDS
MAX = "max"
MIN = "min"
EXACTLY = "exactly"
INTERVAL = "interval"

# AGGREGATION FUNCTIONS
SUM = "sum"
AVG = "avg"
NUM = "num"
VAR = "var"
SPAN = "span"
GAP = "gap"

# DISTANCE NOTION
# event classes over all traces where they occur together
INTER_GROUP_INTERLEAVING = "inter-group interleaving"

# IF ATTRIBUTE VALUES ARE CHECKED THE FOLLOWING WILL BE SIMPLY IGNORED
TERMS_FOR_MISSING = ['undefined', 'missing', 'none', 'nan', 'empty', 'empties', 'unknown', 'other', 'others', 'na',
                     'nil', 'null', '', "", ' ', '<unknown>']

# storage location for custom objects
DEFAULT_SER_PATH = "resources/saved/"
DEFAULT_LOG_SER_PATH = DEFAULT_SER_PATH + "logs/"
DEFAULT_GROUP_SER_PATH = DEFAULT_SER_PATH + "groups/"
DEFAULT_EVAL_SER_PATH = DEFAULT_SER_PATH + "eval/"
DEFAULT_ABSTRACTED_PATH = DEFAULT_SER_PATH + "abstracted/"
# The raw log files
LOG_PATH = "resources/raw/"
SYNTHETIC_LOGS_DIR = LOG_PATH + "synthetic/"
REAL_LOGS_DIR = LOG_PATH + "real/"

RESULTS_DIR = "resources/output/"
LPM_GROUPS_PATH = "resources/baseline/lpm/"

# the output directory
OUT_PATH = "resources/output/"
# the input directory
IN_PATH = "resources/input/"

log_to_case_id = {"bpic161.csv": "CustomerID", "bpic162.csv": "SessionID"}
log_to_label = {"bpic161.csv": "PAGE_NAME", "bpic162.csv": "PAGE_NAME"}
log_to_timestamp = {"bpic161.csv": "TIMESTAMP", "bpic162.csv": "TIMESTAMP"}


START_TOK = '▶'
END_TOK = '■'

# CONSTANTS FOR SEQUENCE TAGGING (NOT USED)
EMPTY_TOK = '[EMP]'
PADDING_TOK = '[PAD]'
UNKNOWN_TOK = '[UNK]'

CASE_PREFIX = "case_"
STANDARD_TARGET_KEY = "sub_process"

GP_BASELINE = "graphpartitioningsim"
GQ_BASELINE = "graphquerying"
PLACEHOLDER = "placeholder"

time_out = 18000
