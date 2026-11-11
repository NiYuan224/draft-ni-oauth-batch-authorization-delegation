"""Core checks using the real local services."""
import time
import unittest
from contextlib import ExitStack
from leader_agent import Leader, self_test
from view import decode

class DemoTests(unittest.TestCase):
    def setUp(self):
        self.cleanup = ExitStack()
        self.addCleanup(self.cleanup.close)
        self.lab = Leader(self.cleanup)

    def test_consent_permissions_and_rs_rejection(self):
        self_test(self.lab)

    def test_token_times_and_interview_inputs(self):
        self.lab.set_task("candidate@example.test", "2030-06-07T14:00:00+08:00")
        before = int(time.time())
        self.lab.approve(["calendar-agent", "email-agent"])
        batch = decode(self.lab.batch["body"]["access_token"], 1)
        self.assertTrue(before <= batch["iat"] <= int(time.time()))
        self.assertEqual(batch["exp"] - batch["iat"], 300)
        for result in self.lab.work.values():
            child = decode(result["exchange"]["body"]["access_token"], 1)
            self.assertLessEqual(child["exp"], batch["exp"])
            self.assertLessEqual(child["exp"] - child["iat"], 120)
        event = self.lab.work["calendar-agent"]["resource"]["body"]
        self.assertEqual(event["start"], self.lab.start)
        self.assertEqual(event["attendee"], self.lab.email)

    def test_invalid_input(self):
        for email, start in [("bad", "2030-06-07T14:00:00+08:00"),
                             ("candidate@example.test", "invalid")]:
            with self.assertRaises(ValueError):
                self.lab.set_task(email, start)

if __name__ == "__main__":
    unittest.main()
