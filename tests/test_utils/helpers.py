import json
from pathlib import Path


def create_org_systems_and_user(num_systems=1):
    """Create an Organisation, the requested number of Systems, a test User and UserProfile.

    Returns (org, [systems], user)
    """
    from django.contrib.auth.models import User

    from webcaf.webcaf.models import Organisation, System, UserProfile

    org = Organisation.objects.create(name="Test Organisation")
    systems = []
    for i in range(1, num_systems + 1):
        name = "Test System" if i == 1 else f"Test System {i}"
        systems.append(System.objects.create(name=name, organisation=org))

    user = User.objects.create_user(username="test@test.gov.uk", email="test@test.gov.uk")
    UserProfile.objects.create(user=user, organisation=org, role="cyber_advisor")

    return org, systems, user


def load_fixture_json(filename: str):
    """Load a fixture from tests/fixtures by filename and return the parsed JSON."""
    FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
    with open(FIXTURE_DIR / filename, "r") as f:
        return json.load(f)
