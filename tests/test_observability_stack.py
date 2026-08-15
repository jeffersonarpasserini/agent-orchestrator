from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ObservabilityStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = (ROOT / "compose.yaml").read_text()
        cls.collector = (ROOT / "observability/otel-collector.yaml").read_text()

    def test_images_ports_limits_and_volume_are_explicit(self):
        self.assertIn("openobserve:v0.92.1@sha256:", self.compose)
        self.assertIn("opentelemetry-collector-contrib:0.158.0@sha256:", self.compose)
        for binding in ("127.0.0.1:5080:5080", "127.0.0.1:4318:4318"):
            self.assertIn(binding, self.compose)
        self.assertIn("openobserve-data:/data", self.compose)
        self.assertIn('ZO_COMPACT_DATA_RETENTION_DAYS: "7"', self.compose)
        self.assertIn("ZO_HTTP_ADDR: 0.0.0.0", self.compose)
        self.assertIn("mem_limit: 1g", self.compose)
        self.assertIn("mem_limit: 256m", self.compose)

    def test_producer_targets_only_collector(self):
        self.assertIn(
            "OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4318/v1/traces",
            self.compose,
        )

    def test_collector_redacts_then_fans_out(self):
        self.assertIn("transform/redact:", self.collector)
        self.assertIn("error_mode: propagate", self.collector)
        self.assertGreaterEqual(self.collector.count("keep_keys(attributes"), 3)
        self.assertIn("exporters: [otlp_http/phoenix, otlp_http/openobserve]", self.collector)
        self.assertIn("set(body, \"[redacted]\")", self.collector)
        self.assertIn("logs:\n      receivers: [otlp]", self.collector)
        self.assertIn("metrics:\n      receivers: [otlp]", self.collector)
        for forbidden in ("prompt", "authorization", "api_key", "dsn"):
            self.assertNotIn(f'"{forbidden}"', self.collector.lower())

    def test_openobserve_is_loopback_only_and_failure_does_not_gate_api(self):
        self.assertIn('"127.0.0.1:5080:5080"', self.compose)
        openobserve_block = self.compose.split("  openobserve:", 1)[1].split(
            "\n  otel-collector:", 1
        )[0]
        self.assertIn("networks:\n      - observability-edge", openobserve_block)
        api_block = self.compose.split("  api:", 1)[1].split("\n  phoenix:", 1)[0]
        self.assertNotIn("openobserve", api_block.lower())
