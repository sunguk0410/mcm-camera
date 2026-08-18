import os


CAMERA_INDEX = int(os.getenv("MCM_CAMERA_INDEX", "0"))
BACKEND_BASE_URL = os.getenv("MCM_BACKEND_URL", "https://api.mcm-showcase.com")
MODEL_NAME = os.getenv("MCM_MODEL_NAME", "yolo26n-pose.pt")
PERSON_CONFIDENCE = 0.60
MIN_PERSON_AREA_RATIO = 0.02

# A person is considered to have left after being absent this long. This avoids
# ending a visit because of a few missed detection frames.
PERSON_EXIT_GRACE_SECONDS = 2.0

# Demo layout, expressed as (left, top, right, bottom) ratios of the image.
# The left half contains one square split into four zones. Adjust these values
# after mounting the camera if the floor markings do not align with the overlay.
ZONE_RATIOS = {
    "ZONE_1": (0.04, 0.18, 0.24, 0.50),
    "ZONE_2": (0.24, 0.18, 0.44, 0.50),
    "ZONE_3": (0.04, 0.50, 0.24, 0.82),
    "ZONE_4": (0.24, 0.50, 0.44, 0.82),
}

# Set real floor/category codes used by the Spring server.
ZONE_METADATA = {
    "ZONE_1": ("1F", "BAG"),
    "ZONE_2": ("1F", "WOMEN"),
    "ZONE_3": ("2F", "MEN"),
    "ZONE_4": ("2F", "ACCESSORY"),
}

AR_ZONE_RATIO = (0.62, 0.20, 0.96, 0.88)
AR_DWELL_SECONDS = 3.0
AR_SESSION_LOOKUP_RETRY_SECONDS = 1.0
