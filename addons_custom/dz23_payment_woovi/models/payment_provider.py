from odoo import fields, models

# Woovi/OpenPix — endpoint único; o AppID (teste ou produção) diferencia o ambiente.
WOOVI_API_BASE = "https://api.woovi.com/api/v1"


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("woovi", "Woovi (PIX)")],
        ondelete={"woovi": "set default"},
    )
    woovi_app_id = fields.Char(
        string="Woovi AppID",
        help="Token AppID da Woovi (Authorization). Fica no servidor, não no código.",
        required_if_provider="woovi",
        groups="base.group_system",
    )

    def _get_default_payment_method_codes(self):
        """Códigos de método de pagamento padrão do Woovi."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != "woovi":
            return default_codes
        return ["woovi"]

    def _build_request_url(self, endpoint, *, is_proxy_request=False, **kwargs):
        if self.code != "woovi":
            return super()._build_request_url(endpoint, is_proxy_request=is_proxy_request, **kwargs)
        return f"{WOOVI_API_BASE}{endpoint}"

    def _build_request_headers(self, *args, **kwargs):
        if self.code != "woovi":
            return super()._build_request_headers(*args, **kwargs)
        return {
            "Authorization": self.woovi_app_id or "",
            "Content-Type": "application/json",
        }
