class GPRSError(Exception):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSATCheckError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSGPRSCheckError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSGetProviderError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSSetProviderError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSEnableWirelessError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSGetIpError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSSMSError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSTCPError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class GPRSHTTPError(GPRSError):
    """Exception raised for errors in the GPRS Module.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
