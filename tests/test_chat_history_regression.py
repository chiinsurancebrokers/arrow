from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.chat import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_long_previous_hal_answer_does_not_cause_422():
    response = client.post(
        "/api/chat",
        json={
            "message": "Who should I call for help with a claim?",
            "history": [
                {
                    "role": "assistant",
                    "content": "A" * 3000,
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "Crawford" in body["answer"]


def test_history_still_has_sane_upper_bound():
    response = client.post(
        "/api/chat",
        json={
            "message": "Who should I call for help with a claim?",
            "history": [{"role": "assistant", "content": "A" * 6001}],
        },
    )
    assert response.status_code == 422
