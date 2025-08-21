# backend/app/main.py
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from app.core.config import settings
from app.core.database import create_tables
from app.core.logging import setup_logging, logger
from app.middleware.auth import AuthenticationMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.tenant import TenantMiddleware

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Global storage for latest sensor data (Dashboard integration)
# In production, this should be replaced with proper database queries
latest_sensor_data: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting PdM Platform API")
    
    # Initialize database
    await create_tables()
    
    # Startup health checks
    from app.core.database import check_db_connection
    from app.core.redis import check_redis_connection
    
    if not await check_db_connection():
        raise RuntimeError("Database connection failed")
    
    if not await check_redis_connection():
        raise RuntimeError("Redis connection failed")
    
    logger.info("All systems ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PdM Platform API")


def create_application() -> FastAPI:
    """Create FastAPI application with all configurations."""
    
    app = FastAPI(
        title="PdM Platform API",
        description="Production-grade Predictive Maintenance Platform",
        version="1.0.0",
        contact={
            "name": "PdM Platform Team",
            "email": "support@pdmplatform.com"
        },
        license_info={
            "name": "Proprietary",
        },
        lifespan=lifespan,
        docs_url=None,  # Custom docs below
        redoc_url=None,
    )
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="PdM Platform API",
            version="1.0.0",
            description="Production-grade Predictive Maintenance Platform API",
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app


# Create app instance
app = create_application()

# Setup logging
setup_logging()

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(AuthenticationMiddleware)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for all requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Add timing header
    response.headers["X-Process-Time"] = str(duration)
    
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"path": request.url.path, "method": request.method}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time(),
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(
        f"Internal server error: {str(exc)}",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": time.time(),
            "path": request.url.path
        }
    )


def store_latest_sensor_data(data: Dict[str, Any]) -> None:
    """Store latest sensor data for dashboard access."""
    global latest_sensor_data
    
    machine_id = data.get("machine_id")
    if machine_id:
        latest_sensor_data[machine_id] = {
            **data,
            "received_at": datetime.utcnow().isoformat()
        }
        
        # Log for debugging
        logger.debug(f"Stored sensor data for machine {machine_id}")


# =============================================================================
# DASHBOARD API ENDPOINTS
# =============================================================================

@app.get("/api/v1/health", tags=["Health"], summary="API Health Check")
async def api_health_check():
    """Enhanced health check endpoint for dashboard connection."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PdM Platform API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": time.time()
    }


@app.get("/api/v1/clients", tags=["Dashboard"], summary="Get Client Configurations")
async def get_clients():
    """Get all client configurations for dashboard."""
    clients = {
        "acme-corp": {
            "name": "ACME Corporation",
            "description": "Leading manufacturer of industrial equipment",
            "icon": "🏢",
            "industry": "Manufacturing",
            "machines": ["acme-pump-01", "acme-motor-02", "acme-comp-03", "acme-fan-04", "acme-mill-05"]
        },
        "tech-solutions": {
            "name": "Tech Solutions Inc.",
            "description": "Advanced industrial automation solutions",
            "icon": "⚙️",
            "industry": "Industrial Automation",
            "machines": ["tech-robot-01", "tech-servo-02", "tech-cnc-03", "tech-laser-04", "tech-press-05"]
        },
        "global-motors": {
            "name": "Global Motors Ltd.",
            "description": "Automotive manufacturing and assembly",
            "icon": "🚗",
            "industry": "Automotive",
            "machines": ["gm-engine-01", "gm-weld-02", "gm-paint-03", "gm-press-04", "gm-assembly-05"]
        },
        "petro-industries": {
            "name": "Petro Industries",
            "description": "Oil refining and petrochemical processing",
            "icon": "🛢️",
            "industry": "Oil & Gas",
            "machines": ["petro-pump-01", "petro-turbine-02", "petro-comp-03", "petro-reactor-04", "petro-distill-05"]
        },
        "food-processing": {
            "name": "Food Processing Co.",
            "description": "Food manufacturing and packaging",
            "icon": "🍎",
            "industry": "Food & Beverage",
            "machines": ["food-mixer-01", "food-oven-02", "food-pack-03", "food-cool-04", "food-belt-05"]
        }
    }
    
    logger.info("Client configurations requested")
    return clients


@app.get("/api/v1/data/latest", tags=["Dashboard"], summary="Get Latest Sensor Data")
async def get_latest_data(
    client_id: Optional[str] = None,
    machine_id: Optional[str] = None,
    limit: int = 100
):
    """Get latest sensor data for dashboard with optional filtering."""
    global latest_sensor_data
    
    # Filter data based on parameters
    filtered_data = []
    
    for machine, data in latest_sensor_data.items():
        # Check if data matches filters
        if client_id and data.get("client_id") != client_id:
            continue
        if machine_id and data.get("machine_id") != machine_id:
            continue
            
        # Only return recent data (last 5 minutes)
        try:
            received_time = datetime.fromisoformat(data.get("received_at", ""))
            if datetime.utcnow() - received_time > timedelta(minutes=5):
                continue
        except (ValueError, TypeError):
            continue
            
        filtered_data.append(data)
    
    # Sort by timestamp and limit results
    filtered_data.sort(
        key=lambda x: x.get("timestamp", ""), 
        reverse=True
    )
    
    result = filtered_data[:limit]
    
    logger.info(
        f"Latest data requested: {len(result)} records returned "
        f"(client_id={client_id}, machine_id={machine_id})"
    )
    
    return result


@app.get("/api/v1/clients/{client_id}/summary", tags=["Dashboard"], summary="Get Client Summary")
async def get_client_summary(client_id: str):
    """Get summary statistics for a specific client."""
    global latest_sensor_data
    
    # Filter data for this client
    client_machines = {
        k: v for k, v in latest_sensor_data.items() 
        if v.get("client_id") == client_id
    }
    
    if not client_machines:
        logger.warning(f"No data found for client {client_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Client '{client_id}' not found or no recent data"
        )
    
    # Calculate summary statistics
    total_machines = len(client_machines)
    online_machines = len([
        m for m in client_machines.values() 
        if m.get("metadata", {}).get("status") == "online"
    ])
    
    temperatures = [
        m.get("sensor_data", {}).get("temperature_c", 0) 
        for m in client_machines.values()
    ]
    avg_temperature = sum(temperatures) / len(temperatures) if temperatures else 0
    
    power_values = [
        m.get("sensor_data", {}).get("power_w", 0) 
        for m in client_machines.values()
    ]
    total_power = sum(power_values)
    
    health_scores = [
        m.get("metadata", {}).get("health_score", 100) 
        for m in client_machines.values()
    ]
    avg_health = sum(health_scores) / len(health_scores) if health_scores else 100
    
    # Count alerts (machines with health < 80 or temp > 80)
    alerts = len([
        m for m in client_machines.values() 
        if (m.get("metadata", {}).get("health_score", 100) < 80 or 
            m.get("sensor_data", {}).get("temperature_c", 0) > 80)
    ])
    
    summary = {
        "client_id": client_id,
        "total_machines": total_machines,
        "online_machines": online_machines,
        "offline_machines": total_machines - online_machines,
        "avg_temperature": round(avg_temperature, 1),
        "total_power": round(total_power, 1),
        "avg_health_score": round(avg_health, 1),
        "active_alerts": alerts,
        "last_updated": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Summary generated for client {client_id}: {summary}")
    return summary


@app.get("/api/v1/machines/{machine_id}/data", tags=["Dashboard"], summary="Get Machine Data")
async def get_machine_data(machine_id: str, hours: int = 1):
    """Get recent data for a specific machine."""
    global latest_sensor_data
    
    machine_data = latest_sensor_data.get(machine_id)
    if not machine_data:
        logger.warning(f"No data found for machine {machine_id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Machine '{machine_id}' not found or no recent data"
        )
    
    # In a real implementation, you'd query historical data from database
    # For now, return the latest data point
    logger.info(f"Data requested for machine {machine_id}")
    return machine_data


@app.post("/api/v1/ingest", tags=["Data Ingestion"], summary="Ingest Sensor Data")
async def ingest_sensor_data(data: Dict[str, Any]):
    """
    Enhanced ingest endpoint that stores data for dashboard access.
    
    This endpoint receives sensor data from IoT devices and stores it
    for both processing and dashboard visualization.
    """
    # Store data for dashboard
    store_latest_sensor_data(data)
    
    # Extract key information for logging
    device_id = data.get("device_id", "unknown")
    machine_id = data.get("machine_id", "unknown")
    client_id = data.get("client_id", "unknown")
    sensor_data = data.get("sensor_data", {})
    metadata = data.get("metadata", {})
    
    # Enhanced logging
    logger.info(
        f"📊 Received data from device {device_id} for machine {machine_id} (client: {client_id})"
    )
    
    if "temperature_c" in sensor_data:
        logger.info(f"   🌡️  Temperature: {sensor_data['temperature_c']}°C")
    
    if "current_a" in sensor_data and "power_w" in sensor_data:
        logger.info(
            f"   ⚡ Current: {sensor_data['current_a']}A, "
            f"Power: {sensor_data['power_w']}W"
        )
    
    if "vibration_x_g" in sensor_data:
        logger.info(f"   📳 Vibration: X={sensor_data['vibration_x_g']}g")
    
    # Here you would add your existing data processing logic
    # For example:
    # - Store to database
    # - Send to ML pipeline
    # - Trigger alerts
    # - etc.
    
    return {
        "status": "success",
        "message": "Data ingested successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "machine_id": machine_id,
        "device_id": device_id
    }


# =============================================================================
# ORIGINAL ENDPOINTS (MAINTAINED)
# =============================================================================

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with branding."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Interactive API Documentation",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "showExtensions": True,
        }
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "PdM Platform API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "dashboard_endpoints": {
            "clients": "/api/v1/clients",
            "latest_data": "/api/v1/data/latest",
            "client_summary": "/api/v1/clients/{client_id}/summary"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
