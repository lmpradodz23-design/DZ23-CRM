# -*- coding: utf-8 -*-
# Testes de autenticação FAIL-CLOSED dos webhooks de WhatsApp.
# Prova que header ausente/incorreto é rejeitado e que canal não configurado
# fica desabilitado (503) — regressão do bypass do webhook Evolution.
import hashlib
import hmac
import json

from odoo.tests import HttpCase, tagged

EVO_URL = "/dz23/whatsapp/evolution/webhook"
META_URL = "/dz23/whatsapp/webhook"


@tagged("post_install", "-at_install", "dz23")
class TestEvolutionWebhookAuth(HttpCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("dz23.whatsapp.evolution_apikey", "TESTKEY-123")

    def _post(self, headers, body=b"{}"):
        return self.url_open(EVO_URL, data=body, headers=headers, timeout=30)

    def test_missing_header_rejected(self):
        r = self._post({"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 401, "header ausente deve ser 401 (não aceitar)")

    def test_empty_header_rejected(self):
        r = self._post({"Content-Type": "application/json", "apikey": ""})
        self.assertEqual(r.status_code, 401)

    def test_wrong_key_rejected(self):
        r = self._post({"Content-Type": "application/json", "apikey": "WRONG"})
        self.assertEqual(r.status_code, 401)

    def test_correct_key_accepted(self):
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"})
        self.assertEqual(r.status_code, 200)

    def test_invalid_json_rejected(self):
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"},
                       body=b"{ not json")
        self.assertEqual(r.status_code, 400)

    def test_non_object_json_rejected(self):
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"},
                       body=b"[1,2,3]")
        self.assertEqual(r.status_code, 400)

    def test_oversized_body_rejected(self):
        big = b'{"x":"' + b"a" * (1024 * 1024 + 16) + b'"}'
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"}, body=big)
        self.assertEqual(r.status_code, 413)

    def test_not_configured_disabled(self):
        self.ICP.set_param("dz23.whatsapp.evolution_apikey", "")
        r = self._post({"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 503, "canal não configurado deve ficar desabilitado (503)")


@tagged("post_install", "-at_install", "dz23")
class TestMetaWebhookAuth(HttpCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("dz23.whatsapp.meta_app_secret", "META-SECRET-XYZ")

    def _sig(self, body, secret="META-SECRET-XYZ"):
        return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_missing_signature_rejected(self):
        r = self.url_open(META_URL, data=b"{}", headers={"Content-Type": "application/json"}, timeout=30)
        self.assertEqual(r.status_code, 401)

    def test_wrong_signature_rejected(self):
        r = self.url_open(META_URL, data=b"{}",
                          headers={"Content-Type": "application/json",
                                   "X-Hub-Signature-256": "sha256=deadbeef"}, timeout=30)
        self.assertEqual(r.status_code, 401)

    def test_valid_signature_accepted(self):
        body = json.dumps({"object": "whatsapp_business_account"}).encode()
        r = self.url_open(META_URL, data=body,
                          headers={"Content-Type": "application/json",
                                   "X-Hub-Signature-256": self._sig(body)}, timeout=30)
        self.assertEqual(r.status_code, 200)

    def test_not_configured_disabled(self):
        self.ICP.set_param("dz23.whatsapp.meta_app_secret", "")
        r = self.url_open(META_URL, data=b"{}", headers={"Content-Type": "application/json"}, timeout=30)
        self.assertEqual(r.status_code, 503)
