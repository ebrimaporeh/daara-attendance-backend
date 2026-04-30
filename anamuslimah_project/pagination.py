# utils/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict

class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class with configurable page size
    Default: 20 items per page
    Max: 100 items per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Override to add more useful pagination metadata
        """
        return Response(OrderedDict([
            ('status', 'success'),
            ('message', 'Data retrieved successfully'),
            ('data', data),
            ('pagination', OrderedDict([
                ('current_page', self.page.number),
                ('total_pages', self.page.paginator.num_pages),
                ('total_items', self.page.paginator.count),
                ('has_next', self.page.has_next()),
                ('has_previous', self.page.has_previous()),
                ('page_size', self.get_page_size(self.request)),
            ]))
        ]))
    
    def get_paginated_response_schema(self, view):
        """
        Override to provide better OpenAPI schema documentation
        """
        return {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'success'},
                'message': {'type': 'string', 'example': 'Data retrieved successfully'},
                'data': {
                    'type': 'array',
                    'items': view.get_serializer().get_fields()
                },
                'pagination': {
                    'type': 'object',
                    'properties': {
                        'current_page': {'type': 'integer', 'example': 1},
                        'total_pages': {'type': 'integer', 'example': 10},
                        'total_items': {'type': 'integer', 'example': 195},
                        'has_next': {'type': 'boolean', 'example': True},
                        'has_previous': {'type': 'boolean', 'example': False},
                        'page_size': {'type': 'integer', 'example': 20}
                    }
                }
            }
        }


class LargeResultsSetPagination(CustomPageNumberPagination):
    """
    Pagination class for endpoints that may return large datasets
    Default: 50 items per page
    Max: 200 items per page
    """
    page_size = 50
    max_page_size = 200


class SmallResultsSetPagination(CustomPageNumberPagination):
    """
    Pagination class for endpoints that return small datasets
    Default: 10 items per page
    Max: 50 items per page
    """
    page_size = 10
    max_page_size = 50