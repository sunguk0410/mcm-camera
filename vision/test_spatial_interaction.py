import unittest
from unittest.mock import patch
import sys
from types import SimpleNamespace

# State-machine tests do not need real drawing or image arrays.
sys.modules.setdefault("cv2", SimpleNamespace(
    FONT_HERSHEY_SIMPLEX=0,
    rectangle=lambda *args, **kwargs: None,
    putText=lambda *args, **kwargs: None,
    circle=lambda *args, **kwargs: None,
))
sys.modules.setdefault("numpy", SimpleNamespace(ndarray=object))

from spatial_interaction import SpatialInteractionTracker


class FakeBackend:
    def __init__(self):
        self.created = 0
        self.ended = []
        self.interactions = []
        self.mappings = []
        self.ar_session_ids = [99]
        self.ar_lookups = 0

    def create_customer_session(self):
        self.created += 1
        return {"customerSessionId": 42}

    def end_customer_session(self, session_id):
        self.ended.append(session_id)

    def add_zone_interaction(self, *args):
        self.interactions.append(args)

    def map_ar_session(self, *args):
        self.mappings.append(args)

    def get_latest_active_ar_session_id(self):
        self.ar_lookups += 1
        return self.ar_session_ids.pop(0)


class FakeBoxes:
    def __init__(self, boxes):
        self.xyxy = FakeTensor(boxes)

    def __len__(self):
        return len(self.xyxy.value)


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


class FakeResult:
    def __init__(self, boxes):
        self.boxes = FakeBoxes(boxes) if boxes else None


class FakeFrame:
    shape = (1000, 1000, 3)

    def copy(self):
        return self


class SpatialInteractionTest(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.tracker = SpatialInteractionTracker(self.backend)
        self.frame = FakeFrame()

    def update(self, foot_x, foot_y):
        result = FakeResult([[foot_x - 50, foot_y - 200, foot_x + 50, foot_y]])
        self.tracker.update(self.frame, self.frame.copy(), result)

    def test_creates_visit_and_sends_interaction_when_leaving_zone(self):
        self.update(100, 300)  # ZONE_1
        self.update(500, 500)  # outside all zones

        self.assertEqual(1, self.backend.created)
        self.assertEqual(1, len(self.backend.interactions))
        self.assertEqual((42, "1F", "BAG"), self.backend.interactions[0][:3])

    @patch("spatial_interaction.monotonic", side_effect=[0.0, 3.1])
    def test_maps_ar_session_after_three_seconds(self, _clock):
        self.update(800, 500)
        self.update(800, 500)

        self.assertEqual(1, self.backend.ar_lookups)
        self.assertEqual([(99, 42)], self.backend.mappings)


if __name__ == "__main__":
    unittest.main()
