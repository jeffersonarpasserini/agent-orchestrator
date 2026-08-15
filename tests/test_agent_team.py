import unittest

from orchestrator.agent_team import (
    AGENT_POLICIES,
    MATERIAL_AUTHORITIES,
    PARALLEL_IMPLEMENTATION_WORKFLOW,
    RESERVE_OWNERS,
    SPEC_REVIEW_WORKFLOW,
    can_authorize,
    get_agent_policy,
    request_report,
)


class AgentTeamPolicyTests(unittest.TestCase):
    def test_spec_panel_has_required_order_and_final_decision(self):
        self.assertEqual(
            [step.profile for step in SPEC_REVIEW_WORKFLOW],
            ["seven", "troi", "b-elanna", "spock"],
        )
        self.assertEqual(SPEC_REVIEW_WORKFLOW[-1].order, 4)

    def test_la_forge_leads_complex_parallel_work(self):
        parallel = [
            step for step in PARALLEL_IMPLEMENTATION_WORKFLOW
            if step.parallel_group == "implementation"
        ]
        self.assertEqual(
            {step.profile for step in parallel},
            {"la-forge", "b-elanna", "barclay", "data"},
        )
        la_forge = next(step for step in parallel if step.profile == "la-forge")
        self.assertIn("most complex", la_forge.responsibility)

    def test_reserve_owners_separate_material_responsibilities(self):
        self.assertEqual(RESERVE_OWNERS["grant_and_final_decision"], ("spock",))
        self.assertEqual(RESERVE_OWNERS["operations_incident_kill_switch"], ("obrien",))
        self.assertEqual(RESERVE_OWNERS["finance_ledger_reconciliation"], ("data",))
        self.assertEqual(
            RESERVE_OWNERS["specification"],
            ("spock", "b-elanna", "seven", "troi"),
        )

    def test_alfred_may_request_reports_without_material_authority(self):
        request = request_report("alfred", "tuvok", "security review status")
        self.assertTrue(request.report_only)
        self.assertEqual(request.authorities, frozenset())
        self.assertFalse(MATERIAL_AUTHORITIES & request.authorities)
        for authority in MATERIAL_AUTHORITIES:
            self.assertFalse(can_authorize("alfred", authority))

    def test_only_alfred_uses_personal_report_coordination(self):
        with self.assertRaisesRegex(PermissionError, "only Alfred"):
            request_report("spock", "tuvok", "status")

    def test_unknown_agent_and_empty_subject_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown agent"):
            get_agent_policy("token-plan-alias")
        with self.assertRaisesRegex(ValueError, "report subject"):
            request_report("alfred", "spock", "  ")

    def test_catalog_contains_all_primary_profiles(self):
        self.assertEqual(len(AGENT_POLICIES), 15)
        self.assertIn("crusher", AGENT_POLICIES)
        self.assertIn("la-forge", AGENT_POLICIES)
