from .settings import ZTASKD_LOG_LEVEL, ZTASKD_LOG_PATH
import logging

def _get_logger(logfile=ZTASKD_LOG_PATH, loglevel=ZTASKD_LOG_LEVEL):
    LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    logger = logging.getLogger('ztaskd')
    logger.setLevel(LEVELS[loglevel.lower()])
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

logger = _get_logger()