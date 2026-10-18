from scripts.evaluate_scene_resolution_offline import evaluate


def test_authored_scene_resolution_offline_corpus_passes_all_gates() -> None:
    report = evaluate()

    assert report["case_count"] == 4
    assert report["passed_count"] == 4
    assert report["failed_count"] == 0
    assert report["all_gates_passed"] is True
    assert report["provider_calls"] == 0
    assert report["runtime_default_eligible"] is False
    assert {case["actual"] for case in report["cases"]} == {
        "admitted",
        "rejected",
    }
