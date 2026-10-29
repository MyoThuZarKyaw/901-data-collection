Latency Query:

sum(rate(otel_http_server_requests_milliseconds_sum{application="inventory_service"}[1m])) / sum(rate(otel_http_server_requests_milliseconds_count{application="inventory_service"}[1m]))