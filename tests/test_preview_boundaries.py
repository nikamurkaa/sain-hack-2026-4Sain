"""Offline-only DND preview boundary contract; does not contact organizers."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal

def test_local_dnd_state_at_scheduled_event_and_neighbours():
    with TestClient(build_rehearsal()) as api:
        opened = api.post("/api/v1/sessions",headers={"Authorization":"Bearer offline-team"},
                          json={"source":"dev","stay_id":"stay_test"})
        assert opened.status_code == 201, opened.text
        auth = {"Authorization":"Bearer "+opened.json()["session_token"]}
        events = api.get("/api/v1/scenario",headers=auth).json()["steps"]
        dnd_events = [s for s in events if s["device_id"] == "dnd"]
        assert len(dnd_events) >= 2
        for step in dnd_events:
            moment = datetime.fromisoformat(step["at"])
            for offset, expected in ((-1, not step["values"]["enabled"]),
                                      (0, step["values"]["enabled"]),
                                      (1, step["values"]["enabled"]),
                                      (5, step["values"]["enabled"])):
                when = (moment + timedelta(minutes=offset)).isoformat()
                response = api.get("/api/v1/state",headers=auth,params={"at":when})
                assert response.status_code == 200, (when, response.text)
                assert response.json()["state"]["dnd"]["enabled"] is expected, when
