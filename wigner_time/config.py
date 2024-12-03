import logging

###############################################################################
#                   Constants                                                 #
###############################################################################
LABEL__ANCHOR = "ANCHOR"
TIME_RESOLUTION = 1.0e-6

###############################################################################
#                   Logging                                                 #
###############################################################################
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
wtlog = logging.getLogger("wtlog")
wtlog.setLevel(logging.DEBUG)
