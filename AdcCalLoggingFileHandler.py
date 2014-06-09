# Based on http://stackoverflow.com/questions/9405890/dynamic-filepath-filename-for-filehandler-in-logger-config-file-in-python
import logging
import logging.config
import logging.handlers
timestamp = ''

class AdcCalLoggingFileHandler(logging.handlers.RotatingFileHandler):
    logfilename = ""
    timestamp = ""
    def __init__(self, fileName, mode, mxByte, bkupN):
        global logfilename
        fn = fileName + timestamp + '.log'
        logfilename = fn
        super(AdcCalLoggingFileHandler,self).__init__(fn, mode, mxByte, bkupN)
