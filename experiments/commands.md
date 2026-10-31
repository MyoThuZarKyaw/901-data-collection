### Log view

# Command to copy order service "logs" folder to current directory
docker cp 901_app_services-order-service-1:/tmp/logs .   
docker cp 901_app_services-gateway-service-1:/tmp/logs .  

# Command to unzip the log archived file
cd logs
gzip -dk application.log.2026-10-29.0.gz 

# Sample Commands to find text from the log if needed
grep -F "Circuit Breaker '" application.log
grep -F "Tripping circuit breaker" application.log.2026-10-29.0        
grep -F "Skipping trip for circuit breaker" application.log.2026-10-29.0
grep -F "Received a circuit breaker alert:" application.log