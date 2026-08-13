import unittest


class ControlledCiFailureDrillTest(unittest.TestCase):
    def test_controlled_failure_for_spock_monitor(self):
        self.fail("O2 controlled CI failure drill; remove this sentinel after detection")


if __name__ == "__main__":
    unittest.main()
