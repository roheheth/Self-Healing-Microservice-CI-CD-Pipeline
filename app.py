import time
import json
import random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Self-Healing API",
    description="SRE Portfolio REST API with built-in health probes and monitoring integration.",
    version="1.0.0"
)

# Track application start time for readiness delay simulation
START_TIME = time.time()
INITIALIZATION_DELAY_SECONDS = 10

# Track global health state for liveness probe failure simulation
is_healthy = True

# Mock market data for tickers
TICKERS = {
    "AMAZ": {"name": "Amazon Inc", "price": 9500.0, "currency": "USD"},
    "AAPL": {"name": "Apple Inc.", "price": 180.50, "currency": "USD"},
    "MSFT": {"name": "Microsoft Corporation", "price": 420.20, "currency": "USD"},
    "GOOGL": {"name": "Alphabet Inc.", "price": 175.80, "currency": "USD"},
}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Asynchronous HTTP middleware for structured logging of request latencies."""
    start_time = time.time()
    response = await call_next(request)
    
    # Exclude health and ready endpoints from logging to prevent spam
    if request.url.path in ["/health", "/ready"]:
        return response

    latency_ms = (time.time() - start_time) * 1000
    
    log_data = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "latency_ms": round(latency_ms, 2),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    # Print structured JSON log to stdout
    print(json.dumps(log_data), flush=True)
    return response

@app.get("/health")
def health():
    """Liveness probe endpoint."""
    global is_healthy
    if is_healthy:
        return {
            "status": "healthy",
            "uptime_seconds": int(time.time() - START_TIME)
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "reason": "Simulated application failure"}
        )

@app.get("/ready")
def ready():
    """Readiness probe endpoint simulating an initial startup workload."""
    uptime = time.time() - START_TIME
    if uptime < INITIALIZATION_DELAY_SECONDS:
        return JSONResponse(
            status_code=503,
            content={
                "status": "initializing",
                "uptime_seconds": int(uptime),
                "delay_required": INITIALIZATION_DELAY_SECONDS
            }
        )
    return {
        "status": "ready",
        "uptime_seconds": int(uptime)
    }

@app.get("/data")
def get_data():
    """Returns mock stock market ticker prices."""
    # Simulate price fluctuations
    data = {}
    for symbol, info in TICKERS.items():
        fluctuation = random.uniform(-0.02, 0.02)  # Max 2% change
        current_price = round(info["price"] * (1 + fluctuation), 2)
        data[symbol] = {
            "name": info["name"],
            "ticker": symbol,
            "price": current_price,
            "currency": info["currency"],
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    return {
        "status": "success",
        "data": data
    }

@app.api_route("/simulate-unhealthy", methods=["GET", "POST"])
def simulate_unhealthy():
    """Simulates an internal application failure by breaking the health check endpoint."""
    global is_healthy
    is_healthy = False
    log_data = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "level": "ERROR",
        "message": "Manual trigger: Application entering unhealthy state (liveness failure simulated)"
    }
    print(json.dumps(log_data), flush=True)
    return {"message": "Liveness status changed to unhealthy. /health will now return 500."}

@app.api_route("/simulate-healthy", methods=["GET", "POST"])
def simulate_healthy():
    """Resets the health check endpoint back to healthy."""
    global is_healthy
    is_healthy = True
    return {"message": "Liveness status changed back to healthy."}
