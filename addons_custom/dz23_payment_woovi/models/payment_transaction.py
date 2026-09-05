from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


def _to_cents(amount):
    return int(float_round(amount * 100, precision_digits=0))


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Cria a cobrança PIX na Woovi e devolve QR Code + copia-e-cola."""
        if self.provider_code != "woovi":
            return super()._get_specific_rendering_values(processing_values)

        payload = {
            "correlationID": self.reference,
            "value": _to_cents(self.amount),  # Woovi usa centavos (int)
            "comment": self.reference,
        }
        try:
            response = self._send_api_request("POST", "/charge", json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        charge = (response or {}).get("charge", {})
        return {
            "woovi_br_code": charge.get("brCode", ""),
            "woovi_qr_code_image": charge.get("qrCodeImage", ""),
            "woovi_status": charge.get("status", ""),
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        if provider_code != "woovi":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("charge", {}).get("correlationID")

    def _apply_updates(self, payment_data):
        if self.provider_code != "woovi":
            return super()._apply_updates(payment_data)

        charge = payment_data.get("charge", {})
        self.provider_reference = charge.get("correlationID") or self.reference
        status = (charge.get("status") or "").upper()
        if status in ("ACTIVE", "PENDING"):
            self._set_pending()
        elif status in ("COMPLETED", "PAID", "CONFIRMED"):
            # Defesa extra: confere o valor pago contra o esperado (em centavos).
            paid = charge.get("value")
            expected = _to_cents(self.amount)
            if paid is not None and int(paid) != expected:
                self._set_error(
                    _("Valor divergente na confirmação Woovi (esperado %s, recebido %s).")
                    % (expected, paid)
                )
            else:
                self._set_done()
        elif status in ("EXPIRED",):
            self._set_canceled()
        else:
            self._set_error(_("Status Woovi não suportado: %s") % status)
