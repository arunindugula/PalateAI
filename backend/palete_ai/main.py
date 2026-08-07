from fastapi import FastAPI

from orders.api import router as orders_router
from chat.api import router as chat_router

app = FastAPI(title="Palete AI")
app.include_router(orders_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
