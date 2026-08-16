from app.banana_v3.batch_inference import predict_batch


class Service:
    def predict(self, value):
        return value


def test_batch_preserves_order_and_isolates_items():
    assert predict_batch(Service(), [b"a", b"b", b"c"], batch_size=2) == [b"a", b"b", b"c"]
