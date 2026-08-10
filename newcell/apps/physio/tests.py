import json
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from .models import SerialConfig, PhysioSample, PhysioRecord


class SerialConfigTests(TestCase):
    def test_get_defaults(self):
        resp = self.client.get(reverse("physio:settings_serial"))
        body = resp.json()
        self.assertEqual(body["enabled"], False)
        self.assertEqual(body["port_a"], "COM6")
        self.assertEqual(body["port_b"], "COM5")
        self.assertEqual(body["baudrate"], 115200)

    def test_put_disabled(self):
        resp = self.client.put(
            reverse("physio:settings_serial"),
            data=json.dumps({
                "enabled": False,
                "port_a": "/dev/ttyUSB0",
                "port_b": "/dev/ttyUSB1",
                "baudrate": 9600,
            }),
            content_type="application/json",
        )
        body = resp.json()
        self.assertEqual(body["port_a"], "/dev/ttyUSB0")
        self.assertEqual(body["baudrate"], 9600)
        cfg = SerialConfig.load()
        self.assertEqual(cfg.port_b, "/dev/ttyUSB1")

    @mock.patch("newcell.apps.physio.views.physio_engine.ensure_running", return_value=True)
    @mock.patch("newcell.apps.physio.views.physio_engine.stop_all")
    def test_put_enabled_starts_reader(self, *_):
        resp = self.client.put(
            reverse("physio:settings_serial"),
            data=json.dumps({"enabled": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.json()["enabled"], True)


class ParseLineTests(TestCase):
    def test_port_a(self):
        from newcell.engine.physio import _PortWorker
        self.assertEqual(
            _PortWorker._parse_line("a", "25.4,412.3,58.2"),
            {"temp": 25.4, "pulse": 412.3, "humidity": 58.2},
        )
        self.assertIsNone(_PortWorker._parse_line("a", "garbage"))

    def test_port_b(self):
        from newcell.engine.physio import _PortWorker
        self.assertEqual(_PortWorker._parse_line("b", "512"), {"gsr": 512.0})
        self.assertIsNone(_PortWorker._parse_line("b", "abc"))


class PhysioLatestTests(TestCase):
    def test_latest(self):
        PhysioSample.objects.create(port="a", temp=25.0, pulse=400.0, humidity=60.0)
        PhysioRecord.objects.create(temp_avg=25.0, skin_humidity_avg=60.0, hr_avg=400.0)
        resp = self.client.get(reverse("physio:physio_latest"))
        body = resp.json()
        self.assertEqual(len(body["samples"]), 1)
        self.assertEqual(body["samples"][0]["port"], "a")
        self.assertEqual(body["latest"]["temp"], 25.0)

    def test_ports_endpoint(self):
        resp = self.client.get(reverse("physio:serial_ports"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ports", resp.json())
