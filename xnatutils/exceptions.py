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

    def __init__(self, resource_name, sess_label, scan_label,
                 available=None):
        self.resource_name = resource_name
        self.sess_label = sess_label
        self.scan_label = scan_label
        self.available = available
        
        
    def __repr__(self):
        return "{}(resource='{}', sess='{}', scan='{}')".format(
            self.__class__.__name__, self.resource_name, self.sess_label,
            self.scan_label)
        
    def __str__(self):
        return "Missing '{}' in '{}:{}', found: '{}'".format(
            self.resource_name, self.sess_label, self.scan_label,
            "', '".join(self.available))


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
