"""MR-NEW-06: only genuine pre-handler validation is certified as no-side-effect."""
from fastapi.testclient import TestClient
from scripts.rehearse_client import build_rehearsal

AT="2026-11-12T20:00:00+03:00"

def test_fastapi_pre_handler_422_has_certified_marker_no_effects_and_followup_succeeds():
    w=build_rehearsal()
    with TestClient(w,raise_server_exceptions=False) as api:
        s=api.post("/api/v1/sessions",headers={"Authorization":"Bearer offline-team"},
                   json={"source":"dev","stay_id":"stay_test"})
        assert s.status_code==201
        h={"Authorization":"Bearer "+s.json()["session_token"]}
        baseline=api.get("/api/v1/state",headers=h).json()
        n=w.state.rehearsal_simulator.actions
        rejected=api.post("/api/v1/messages",headers={**h,"Idempotency-Key":"mrnew06-rejected-0001"},
                          json={"at":AT,"text":""})
        assert rejected.status_code==422 and "detail" in rejected.json()
        assert rejected.headers["X-Sain-Rejection-Class"]=="prehandler"
        assert w.state.rehearsal_simulator.actions==n
        state=api.get("/api/v1/state",headers=h).json()
        assert state==baseline
        session=api.get("/api/v1/session",headers=h).json()
        assert session["pending_action"] is None and session["reconciliation_required"] is False
        assert session["history"]==[]
        accepted=api.post("/api/v1/messages",headers={**h,"Idempotency-Key":"mrnew06-corrected-0002"},
                          json={"at":AT,"text":"Сделай попрохладнее"})
        assert accepted.status_code==200,accepted.text
        assert accepted.json()["reply"]["response_class"]=="done"
        assert w.state.rehearsal_simulator.actions==n+1
        assert len(api.get("/api/v1/session",headers=h).json()["history"])==1

def test_prehandler_manual_and_proven_safe_domain_refusal_headers():
    w=build_rehearsal()
    with TestClient(w,raise_server_exceptions=False) as api:
        s=api.post("/api/v1/sessions",headers={"Authorization":"Bearer offline-team"},
                   json={"source":"dev","stay_id":"stay_test"})
        h={"Authorization":"Bearer "+s.json()["session_token"]}
        before=w.state.rehearsal_simulator.actions
        for device in ["light","climate"]:
            response=api.post("/api/v1/devices",
               headers={**h,"Idempotency-Key":"mrnew06-manual-invalid-"+device},
               json={"device_id":device,"values":{},"at":AT})
            assert response.status_code==422
            assert response.headers["X-Sain-Rejection-Class"]=="prehandler"
        invalid=api.post("/api/v1/devices",
            headers={**h,"Idempotency-Key":"mrnew06-domain-invalid-0001"},
            json={"device_id":"light","values":{"brightness":999},"at":AT})
        assert invalid.status_code==422,invalid.text
        assert invalid.json()["code"]=="INVALID_VALUE"
        assert invalid.headers["X-Sain-Rejection-Class"]=="domain"
        assert w.state.rehearsal_simulator.actions==before
        info=api.get("/api/v1/session",headers=h).json()
        assert not info["reconciliation_required"]
        good=api.post("/api/v1/devices",
          headers={**h,"Idempotency-Key":"mrnew06-valid-manual-0002"},
          json={"device_id":"light","values":{"brightness":30},"at":AT})
        assert good.status_code==200,good.text
        assert w.state.rehearsal_simulator.actions==before+1

def test_unknown_uncertainty_and_old_clock_still_have_no_certified_header():
    w=build_rehearsal()
    with TestClient(w,raise_server_exceptions=False) as api:
        s=api.post("/api/v1/sessions",headers={"Authorization":"Bearer offline-team"},
                   json={"source":"dev","stay_id":"stay_test"})
        h={"Authorization":"Bearer "+s.json()["session_token"]}
        first=api.post("/api/v1/messages",headers={**h,"Idempotency-Key":"mrnew06-partial-0001"},
             json={"at":"2026-11-12T20:45:00+03:00","text":"Проверка частичного выполнения"})
        assert first.status_code==409
        assert first.headers.get("X-Sain-Rejection-Class") is None
        assert first.json()["code"]=="ACTION_PARTIAL"
        info=api.get("/api/v1/session",headers=h).json()
        assert info["reconciliation_required"] is True
        bad=api.post("/api/v1/messages",headers={**h,"Idempotency-Key":"mrnew06-pending-0002"},
                     json={"at":AT,"text":"Сделай попрохладнее"})
        assert bad.status_code==409
        assert bad.headers.get("X-Sain-Rejection-Class") is None
        assert bad.json()["code"]=="RECOVERY_REQUIRED"
