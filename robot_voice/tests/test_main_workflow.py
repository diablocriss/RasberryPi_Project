import main


def test_pi_audio_workflow_routes_to_i2s_pipeline(monkeypatch):
    called = []

    monkeypatch.setenv("ROBOT_WORKFLOW", "pi_audio")
    monkeypatch.setattr(main, "run_i2s_pipeline", lambda: called.append("i2s"))

    main.main()

    assert called == ["i2s"]
