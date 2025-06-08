import unittest
import os
from webcaf.webcaf.router import FrameworkRouter

# We test for the validity of the CAF YAML elsewhere, so not testing the ability of
# FrameworkRouter to cope with bad YAML here.

class TestFrameworkRouter(unittest.TestCase):
    
    def setUp(self):
        self.fixture_path = os.path.join(
            os.path.dirname(__file__), 
            'fixtures',
            'caf-v3.2-dummy.yaml'
        )
        
    def test_router_flattens_hierarchy(self):
        descriptions = [
            'Capabilities exist to ensure security defences remain effective.',
            'The organisation monitors the security status of systems.',
            'Monitoring data sources allow for timely identification of security events.',
            'The organisation detects malicious activity even when it evades standard solutions.',
            'Abnormality detection is used to identify malicious activity.',
            'Sophisticated attack detection through behavior monitoring.',
            'Capabilities exist to minimize adverse impacts of security incidents.',
            'Well-defined incident management processes are in place.',
            'Incident response plan is based on risk assessment.',
            'Capability exists to execute the response plan effectively.',
            'Response plans are regularly tested with realistic scenarios.',
            'Incident root causes are analyzed to prevent recurrence.',
            'Root cause analysis ensures appropriate remediation.'
                ]
        router = FrameworkRouter(self.fixture_path)
        for i, item in enumerate(router.all):
            self.assertEqual(item['description'], descriptions[i])


if __name__ == '__main__':
    unittest.main()
