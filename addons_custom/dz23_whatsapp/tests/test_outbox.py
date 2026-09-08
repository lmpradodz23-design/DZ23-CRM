# Outbox durável: enqueue, envio (sucesso pelo corpo), retry/backoff, DLQ,
# requeue e o enfileiramento da resposta pelo agente (HIGH-01).
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase, tagged

_SEND = "odoo.addons.dz23_whatsapp.models.whatsapp_channel.DZ23Channel.send_text"


@tagged("post_install", "-at_install", "dz23")
class TestMessageOutbox(TransactionCase):
    def setUp(self):
        super().setUp()
        self.channel = self.env["dz23.channel"].create(
            {
                "name": "Canal Outbox",
                "company_id": self.env.company.id,
                "provider": "evolution",
                "evo_base": "http://nao-existe.local:8080",
                "evo_instance": "outbox_inst",
                "evo_apikey": "K",
            }
        )
        self.Outbox = self.env["dz23.message.outbox"]

    def test_enqueue_creates_pending(self):
        rec = self.Outbox._enqueue(self.channel, "5561999990000", "olá")
        self.assertTrue(rec)
        self.assertEqual(rec.status, "pending")
        self.assertEqual(rec.recipient, "5561999990000")

    def test_enqueue_empty_is_noop(self):
        self.assertFalse(self.Outbox._enqueue(self.channel, "5561999990000", ""))
        self.assertFalse(self.Outbox._enqueue(self.channel, "", "oi"))

    def test_process_success_marks_sent(self):
        rec = self.Outbox._enqueue(self.channel, "5561999990000", "oi")
        with patch(_SEND, return_value={"key": {"id": "X"}}):
            rec._process_one()
        self.assertEqual(rec.status, "sent")

    def test_process_failure_retries_then_dlq(self):
        rec = self.Outbox._enqueue(self.channel, "5561999990000", "oi")
        rec.max_attempts = 2
        with patch(_SEND, side_effect=Exception("boom")):
            rec._process_one()
            self.assertEqual(rec.status, "failed")
            self.assertEqual(rec.attempts, 1)
            self.assertGreater(rec.next_attempt_at, fields.Datetime.now())
            rec.next_attempt_at = fields.Datetime.now()
            rec._process_one()
            self.assertEqual(rec.status, "dead", "vai para DLQ após max_attempts")
            self.assertEqual(rec.attempts, 2)

    def test_requeue_from_dlq(self):
        rec = self.Outbox._enqueue(self.channel, "5561999990000", "oi")
        rec.write({"status": "dead", "attempts": 6})
        rec.action_requeue()
        self.assertEqual(rec.status, "pending")
        self.assertEqual(rec.attempts, 0)

    def test_handle_inbound_enqueues_reply(self):
        # "quero agendar" (sem data) => resposta determinística (sem rede/IA),
        # que deve ser ENFILEIRADA na outbox (não enviada síncrono).
        before = self.Outbox.search_count([("channel_id", "=", self.channel.id)])
        self.channel._processing_self().handle_inbound("5561988887777", "quero agendar")
        after = self.Outbox.search_count([("channel_id", "=", self.channel.id)])
        self.assertGreater(after, before, "handle_inbound deve enfileirar a resposta na outbox")
