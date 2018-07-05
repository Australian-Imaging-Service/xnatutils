class XnatUtilsException(Exception):
    pass


class XnatUtilsError(XnatUtilsException):
    pass


class XnatUtilsDigestCheckError(XnatUtilsError):
    pass


class XnatUtilsDigestCheckFailedError(XnatUtilsDigestCheckError):
    pass


class XnatUtilsNoMatchingSessionsException(XnatUtilsException):
    pass


class XnatUtilsSkippedAllSessionsException(
        XnatUtilsNoMatchingSessionsException):
    pass


class XnatUtilsMissingResourceException(XnatUtilsException):

    def __init__(self, resource_name, sess_label, scan_label):
        self.resource_name = resource_name
        self.sess_label = sess_label
        self.scan_label = scan_label


class XnatUtilsUsageError(XnatUtilsError):
    pass


class XnatUtilsKeyError(XnatUtilsUsageError):

    def __init__(self, key, msg):
        super(XnatUtilsKeyError, self).__init__(msg)
        self.key = key


class XnatUtilsLookupError(XnatUtilsUsageError):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return ("Could not find asset corresponding to '{}' (please make sure"
                " you have access to it if it exists)".format(self.path))
