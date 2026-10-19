from app.delivery import classify
def test_retryable_and_terminal_classification():
    assert classify(503,None).retry
    assert not classify(400,None).retry
    assert classify(204,None).success
