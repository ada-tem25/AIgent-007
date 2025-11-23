from fastapi import FastAPI, Request
import uvicorn
app = FastAPI()

@app.post("/on_metering")
async def recv(req: Request):
    body = await req.json()
    print("Received on_receiver:", body)
    return {"ack": {"status": "ACK"}}

if __name__ == "__main__":
    uvicorn.run("sim_receiver:app", host="127.0.0.1", port=9000)