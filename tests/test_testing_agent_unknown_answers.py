from orchestrator.testing_agent.runtime import FounderProfile


def test_unknown_founder_answers_are_question_specific_and_do_not_invent_facts():
    profile = FounderProfile()

    first = profile.answer("Which internal onboarding screen was observed during the last usability session?")
    second = profile.answer("Which exact deployment region did a prospective customer request?")

    assert first != second
    assert "not have verified information" in first
    assert "not have verified information" in second
    assert "no result is claimed yet" in first
    assert "no result is claimed yet" in second
    assert "onboarding screen" in first
    assert "deployment region" in second
