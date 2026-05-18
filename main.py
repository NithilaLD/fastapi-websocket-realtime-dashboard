
import asyncio
import aiomysql  # Async MySQL library
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ValidationError

app = FastAPI()

# -------------------------
# Async MySQL connection pool
# -------------------------
DB_CONFIG = {
    "host": "your_database_host",       # e.g., "localhost" or "sql.yourhosting.com"
    "user": "your_database_username",   # e.g., "admin" or "db_user_123"
    "password": "your_secure_password", # Keep this hidden!
    "db": "your_database_name",         # The specific database schema name
    "port": 3306                        # 3306 is standard for MySQL/MariaDB
}

pool = None  # will hold aiomysql pool

async def get_db_pool():
    global pool
    if pool is None:
        pool = await aiomysql.create_pool(**DB_CONFIG, autocommit=True)
    return pool

# -------------------------
# Pydantic model for messages (example)
# -------------------------
class ClientMessage(BaseModel):
    action: str  # example field, can be extended

# -------------------------
# HTML Frontend
# -------------------------
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Real-Time Database Dashboard</title>
</head>
<body>
    <h1>Live Student Records</h1>
    <div id="records"></div>

    <script>
        // Replace with wss:// in production
        const ws = new WebSocket("ws://localhost:8000/ws?token=MY_SECURE_TOKEN");

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            let html = "<ul>";
            for (let row of data) {
                html += `<li>${row.SID} - ${row.Name} (${row.Age})</li>`;
            }
            html += "</ul>";
            document.getElementById("records").innerHTML = html;
        };

        ws.onclose = () => {
            console.log("WebSocket closed");
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

# -------------------------
# WebSocket endpoint with security and efficiency
# -------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    token: Example JWT token or API key passed in query params.
    In production, validate this token.
    """
    # --- Step 1: Authenticate ---
    if token != "MY_SECURE_TOKEN":  # replace with real JWT validation
        await websocket.close(code=1008)  # Policy violation
        return

    await websocket.accept()

    try:
        db_pool = await get_db_pool()

        while True:
            # --- Step 2: Fetch data asynchronously ---
            async with db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT * FROM sample")
                    rows = await cursor.fetchall()

            # --- Step 3: Send data to client ---
            await websocket.send_json(rows)

            # --- Step 4: Wait before next update ---
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Error:", e)
        await websocket.close(code=1011)  # Internal server error

# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)