from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination


# ?page=2              -> page 2
# ?page=2&page_size=20 -> page 2 with 20 items
class SmallPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 50


# ?limit=10&offset=20 -> skip 20, take 10
class SmallLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 5
    max_limit = 50


# Response looks like:
# {
#     "count": 23,
#     "next": "http://.../?page=3",
#     "previous": "http://.../?page=1",
#     "results": [ ... ]
# }
#
# GLOBAL pagination (all list APIs) -> in settings.py:
# REST_FRAMEWORK = {
#     "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
#     "PAGE_SIZE": 10,
# }
