from core.response_handler import ResponseHandler


class FakeClassifier:
    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.labels = [
            "greeting",
            "goodbye",
            "check_in",
            "check_out",
            "room_inquiry",
            "facilities",
            "wifi",
            "directions",
            "complaint",
            "concierge",
            "confirm_yes",
            "confirm_no",
            "identity",
            "thanks",
            "unknown",
        ]

    def predict(self, text):
        intent = self._outputs.pop(0)
        return {"intent": intent, "confidence": 0.99}


class FakeFuture:
    def __init__(self, result):
        self._result = result

    def wait(self, timeout=5.0):
        return self._result


class FakeDBWorker:
    def __init__(self):
        self.created = []

    def create_booking(self, **kwargs):
        self.created.append(kwargs)
        return FakeFuture(42)

    def list_bookings(self):
        return FakeFuture(
            [
                {
                    "booking_id": 7,
                    "guest_name": "Alice",
                    "room_number": "101",
                    "check_in_date": "2026-05-20",
                    "check_out_date": "2026-05-22",
                }
            ]
        )

    def cancel_booking(self, booking_id):
        return FakeFuture(0)

    def list_rooms(self):
        return FakeFuture(
            [
                {"room_id": 1, "room_number": "101", "room_type": "standard", "description": "A"},
                {"room_id": 2, "room_number": "201", "room_type": "deluxe", "description": "B"},
            ]
        )

    def check_availability(self, check_in, check_out):
        return FakeFuture([1])


def test_random_response_avoids_immediate_repeat():
    handler = ResponseHandler(classifier=FakeClassifier(["thanks", "thanks"]))
    first = handler.process("thanks")
    second = handler.process("thanks again")

    assert first != second


def test_check_in_flow_creates_booking():
    db_worker = FakeDBWorker()
    handler = ResponseHandler(
        classifier=FakeClassifier(["check_in", "confirm_yes", "confirm_yes"]),
        db_worker=db_worker,
    )

    reply = handler.process("I want to check in")
    assert reply == "Welcome! May I have your name, please?"

    reply = handler.process("My name is Alice")
    assert reply == "Thank you Alice. What are your check-in and check-out dates?"

    reply = handler.process("May 20 to 22")
    assert "42" in reply
    assert db_worker.created == [
        {
            "guest_name": "Alice",
            "email": "",
            "check_in": "2026-05-20",
            "check_out": "2026-05-22",
            "guests": 1,
            "room_id": 1,
        }
    ]


def test_identity_lookup_uses_booking_list():
    handler = ResponseHandler(classifier=FakeClassifier(["identity"]), db_worker=FakeDBWorker())

    reply = handler.process("my name is Alice")

    assert "Room 101" in reply
    assert "2026-05-20" in reply


def test_room_inquiry_summarises_available_rooms():
    handler = ResponseHandler(classifier=FakeClassifier(["room_inquiry"]), db_worker=FakeDBWorker())

    reply = handler.process("May 20 to 22")

    assert "1 room(s) available" in reply
    assert "201" in reply
