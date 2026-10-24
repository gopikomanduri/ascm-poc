from orchestrator.testing_agent.runtime import FounderProfile


def test_unknown_founder_answers_are_question_specific_and_do_not_invent_facts():
    profile = FounderProfile()

    first = profile.answer("What is the expected onboarding conversion rate?")
    second = profile.answer("Which customer has committed to a paid pilot?")

    assert first != second
    assert "not have verified information" in first
    assert "not have verified information" in second
    assert "no result is claimed yet" in first
    assert "no result is claimed yet" in second
    assert "conversion rate" in first
    assert "paid pilot" in second
