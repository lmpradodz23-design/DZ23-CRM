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
        self.channel = self.env["dz23.channel"].create(
            {
                "name": "Canal Teste",
                "company_id": self.env.company.id,
                "provider": "evolution",
                "evo_base": "http://evo.local:8080",
                "evo_instance": "inst_teste",
                "evo_apikey": "TESTKEY-123",
            }
        )
        self.secret = self.channel.callback_secret
        self.url = "/dz23/whatsapp/evolution/webhook/%s" % self.channel.webhook_token
        self.body = json.dumps({"instance": "inst_teste", "data": {}}).encode()

    def _post(self, headers, body=None):
        return self.url_open(self.url, data=body or self.body, headers=headers, timeout=30)

    def test_unknown_token_404(self):
        r = self.url_open(
            "/dz23/whatsapp/evolution/webhook/naoexiste",
            data=self.body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        self.assertEqual(r.status_code, 404)

    def test_missing_header_401(self):
        r = self._post({"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 401)

    def test_wrong_secret_401(self):
        r = self._post({"Content-Type": "application/json", "X-DZ23-Callback": "WRONG"})
        self.assertEqual(r.status_code, 401)

    def test_admin_key_is_not_callback_secret_401(self):
        # a chave administrativa NÃO serve como segredo de callback
        r = self._post({"Content-Type": "application/json", "X-DZ23-Callback": "TESTKEY-123"})
        self.assertEqual(r.status_code, 401)

    def test_correct_secret_200(self):
        r = self._post({"Content-Type": "application/json", "X-DZ23-Callback": self.secret})
        self.assertEqual(r.status_code, 200)

    def test_invalid_json_400(self):
        r = self._post(
            {"Content-Type": "application/json", "X-DZ23-Callback": self.secret}, body=b"{ nope"
        )
        self.assertEqual(r.status_code, 400)

    def test_wrong_instance_409(self):
        body = json.dumps({"instance": "outra_instancia", "data": {}}).encode()
        r = self._post(
            {"Content-Type": "application/json", "X-DZ23-Callback": self.secret}, body=body
        )
        self.assertEqual(r.status_code, 409)

    def test_meta_no_app_secret_503(self):
        # Canal Meta sem App Secret => canal desabilitado (503), reachable pois
        # meta_app_secret não é obrigatório (callback_secret do Evolution é).
        meta = self.env["dz23.channel"].create(
            {
                "name": "Meta sem secret",
                "company_id": self.env.company.id,
                "provider": "meta_cloud",
            }
        )
        r = self.url_open(
            "/dz23/whatsapp/meta/webhook/%s" % meta.webhook_token,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        self.assertEqual(r.status_code, 503)

    def test_cross_channel_secret_isolation(self):
        # segredo de outro canal não autentica neste token
        other = self.env["dz23.channel"].create(
            {
                "name": "Outro",
                "company_id": self.env.company.id,
                "provider": "evolution",
                "evo_base": "http://evo.local:8080",
                "evo_instance": "inst_outra",
                "evo_apikey": "OTHERKEY-999",
            }
        )
        r = self._post(
            {"Content-Type": "application/json", "X-DZ23-Callback": other.callback_secret}
        )
        self.assertEqual(r.status_code, 401)
