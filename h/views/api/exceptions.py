# -*- coding: utf-8 -*-

"""
API exception views.

Views rendered by the web application in response to exceptions thrown within
API views.
"""

from __future__ import unicode_literals

from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config

from h.i18n import TranslationString as _  # noqa: N813
from h.exceptions import APIError
from h.schemas import ValidationError
from h.util.view import handle_exception, json_view
from h.views.api.config import cors_policy

# All exception views below need to apply the `cors_policy` decorator for the
# responses to be readable by web applications other than those on the same
# origin as h itself.


# Within the API, render a JSON 403/404 message.
@forbidden_view_config(path_info='/api/', renderer='json', decorator=cors_policy)
@notfound_view_config(path_info='/api/', renderer='json', decorator=cors_policy)
def api_notfound(request):
    """Handle a request for an unknown/forbidden resource within the API."""
    request.response.status_code = 404
    message = _("Either the resource you requested doesn't exist, or you are "
                "not currently authorized to see it.")
    return {'status': 'failure', 'reason': message}


@json_view(context=APIError, decorator=cors_policy)
def api_error(context, request):
    """Handle an expected/deliberately thrown API exception."""
    request.response.status_code = context.status_code
    return {'status': 'failure', 'reason': str(context)}


@json_view(context=ValidationError, path_info='/api/', decorator=cors_policy)
def api_validation_error(context, request):
    request.response.status_code = 400
    return {'status': 'failure', 'reason': str(context)}


@json_view(context=Exception, path_info='/api/', decorator=cors_policy)
def json_error(context, request):
    """Handle an unexpected exception in an API view."""
    handle_exception(request, exception=context)
    message = _("Hypothesis had a problem while handling this request. "
                "Our team has been notified. Please contact support@hypothes.is"
                " if the problem persists.")
    return {'status': 'failure', 'reason': message}
