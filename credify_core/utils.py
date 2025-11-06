import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
logging.basicConfig(level="INFO")
logger = logging.getLogger("Credify")

def credify_exception_handler(exception , context):
    response = exception_handler(exception,context)
    request = context.get("request")


    if isinstance(exception,APIException):

        if request:
            logger.info(
                "Bad Request: %s,%s,%s,%s,%s,%s",
                exception.status_code,
                exception.detail,
                request.user,
                request.method,
                request.path,
                request.data,
            )    
        else:
            logger.info("Bad Request: %s,%s",exception.status_code,exception.detail)
    return response
        