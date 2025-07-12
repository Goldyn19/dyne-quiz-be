from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ValidationError) and response is not None:
        errors = []

        # Handle non-field errors
        non_field_errors = exc.detail.get('non_field_errors')
        if non_field_errors:
            for message in non_field_errors:
                errors.append({
                    'field': 'general',
                    'message': str(message)
                })

        # Handle field-specific errors
        for field, messages in exc.detail.items():
            if field == 'non_field_errors':
                continue  # already handled above

            if isinstance(messages, list):
                for message in messages:
                    errors.append({
                        'field': field,
                        'message': str(message)
                    })
            else:
                errors.append({
                    'field': field,
                    'message': str(messages)
                })

        response.data = {
            'errors': errors
        }
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    return response
