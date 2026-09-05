# -*- coding: utf-8 -*-
# Testes FAIL-CLOSED + multi-tenant dos webhooks de WhatsApp.
# Provam: token desconhecido -> 404; header apikey ausente/errado -> 401;
# canal sem apikey -> 503; JSON inválido -> 400; instância divergente -> 409;
# correto -> 200. E isolamento: token de um canal não serve para outro.
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "dz23")
class TestEvolutionWebhookAuth(HttpCase):
    def setUp(self):
        super().setUp()
        self.channel = self.env["dz23.channel"].create({
            "name": "Canal Teste",
            "company_id": self.env.company.id,
            "provider": "evolution",
            "evo_base": "http://evo.local:8080",
            "evo_instance": "inst_teste",
            "evo_apikey": "TESTKEY-123",
        })
        self.url = "/dz23/whatsapp/evolution/webhook/%s" % self.channel.webhook_token
        self.body = json.dumps({"instance": "inst_teste", "data": {}}).encode()

    def _post(self, headers, body=None):
        return self.url_open(self.url, data=body or self.body, headers=headers, timeout=30)

    def test_unknown_token_404(self):
        r = self.url_open("/dz23/whatsapp/evolution/webhook/naoexiste",
                          data=self.body, headers={"Content-Type": "application/json"}, timeout=30)
        self.assertEqual(r.status_code, 404)

    def test_missing_header_401(self):
        r = self._post({"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 401)

    def test_wrong_key_401(self):
        r = self._post({"Content-Type": "application/json", "apikey": "WRONG"})
        self.assertEqual(r.status_code, 401)

    def test_correct_key_200(self):
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"})
        self.assertEqual(r.status_code, 200)

    def test_invalid_json_400(self):
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"}, body=b"{ nope")
        self.assertEqual(r.status_code, 400)

    def test_wrong_instance_409(self):
        body = json.dumps({"instance": "outra_instancia", "data": {}}).encode()
        r = self._post({"Content-Type": "application/json", "apikey": "TESTKEY-123"}, body=body)
        self.assertEqual(r.status_code, 409)

    def test_no_apikey_configured_503(self):
        self.channel.evo_apikey = False
        r = self._post({"Content-Type": "application/json", "apikey": "x"})
        self.assertEqual(r.status_code, 503)

    def test_cross_channel_token_isolation(self):
        # apikey de outro canal não autentica neste token
        other = self.env["dz23.channel"].create({
            "name": "Outro", "company_id": self.env.company.id, "provider": "evolution",
            "evo_base": "http://evo.local:8080", "evo_instance": "inst_outra",
            "evo_apikey": "OTHERKEY-999",
        })
        r = self._post({"Content-Type": "application/json", "apikey": other.evo_apikey})
        self.assertEqual(r.status_code, 401)
