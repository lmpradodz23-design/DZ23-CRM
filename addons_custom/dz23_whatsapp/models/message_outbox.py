# Outbox DURÁVEL de respostas a enviar. O agente ENFILEIRA a resposta aqui
# (o efeito de negócio já foi aplicado exatamente uma vez pelo inbox); um worker
# envia com retry exponencial + jitter e DLQ. Evita PERDER a resposta ao cliente
# quando o provedor (Evolution/Meta/Twilio) está momentaneamente fora (HIGH-01).
import logging
import random
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 6
_BATCH = 20


def _sanitize(msg):
    """Mensagem de erro curta e sem conteúdo sensível."""
    return (msg or "")[:200]


class DZ23MessageOutbox(models.Model):
    _name = "dz23.message.outbox"
    _description = "DZ23 — Outbox durável de respostas (retry + DLQ)"
    _order = "id"

    channel_id = fields.Many2one("dz23.channel", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(
        related="channel_id.company_id", store=True, index=True, readonly=True
    )
    recipient = fields.Char(required=True, help="Número E.164 do destinatário")
    body = fields.Text(required=True)
    status = fields.Selection(
        [
            ("pending", "Pendente"),
            ("sent", "Enviada"),
            ("failed", "Falha (retry)"),
            ("dead", "DLQ"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(default=0)
    max_attempts = fields.Integer(default=_MAX_ATTEMPTS)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True)
    error = fields.Char()

    # ---------- enfileirar (chamado pelo agente após aplicar o efeito) ----------
    @api.model
    def _enqueue(self, channel, recipient, body):
        """Persiste a resposta a enviar. Retorna o record (ou vazio se sem corpo)."""
        if not body or not recipient:
            return self.browse()
        return self.sudo().create(
            {
                "channel_id": channel.id,
                "recipient": recipient,
                "body": body,
                "status": "pending",
                "next_attempt_at": fields.Datetime.now(),
            }
        )

    # ---------- worker (cron) ----------
    @api.model
    def _cron_process(self):
        """Reivindica lote devido com FOR UPDATE SKIP LOCKED e envia."""
        # next_attempt_at é UTC naive; comparar com clock_timestamp() convertido
        # para UTC evita erro de fuso quando o TimeZone da sessão PG não é UTC.
        self.env.cr.execute(
            """
            SELECT id FROM dz23_message_outbox
            WHERE status IN ('pending', 'failed')
              AND next_attempt_at <= (clock_timestamp() AT TIME ZONE 'utc')
            ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED
        """,
            (_BATCH,),
        )
        ids = [r[0] for r in self.env.cr.fetchall()]
        if not ids:
            return
        for rec in self.browse(ids):
            rec._process_one()

    def _process_one(self):
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self.channel_id._processing_self().send_text(self.recipient, self.body)
                self.write({"status": "sent", "error": False})
        except Exception as e:  # noqa: BLE001
            attempts = self.attempts + 1
            if attempts >= self.max_attempts:
                self.write(
                    {
                        "status": "dead",
                        "attempts": attempts,
                        "error": _("DLQ: %s") % _sanitize(str(e)),
                    }
                )
                _logger.warning("Outbox %s -> DLQ após %s tentativas.", self.id, attempts)
            else:
                backoff = min(3600, 2**attempts)
                delay = backoff + random.randint(0, max(1, backoff // 2))
                self.write(
                    {
                        "status": "failed",
                        "attempts": attempts,
                        "error": _sanitize("%s: %s" % (type(e).__name__, e)),
                        "next_attempt_at": fields.Datetime.now() + timedelta(seconds=delay),
                    }
                )

    def action_requeue(self):
        """Reprocessa itens da DLQ (ação administrativa auditável)."""
        for rec in self:
            rec.write(
                {
                    "status": "pending",
                    "attempts": 0,
                    "next_attempt_at": fields.Datetime.now(),
                    "error": False,
                }
            )
        return True
