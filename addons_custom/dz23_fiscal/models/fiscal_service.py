# Serviço de emissão de NF-e.
# ROTA 1 (ADR-002): DESATIVADO até existir um adapter homologado por provedor.
# Não há endpoint genérico nem payload "faz-de-conta": qualquer tentativa de
# emissão falha de forma clara (fail-closed). Quando um adapter real (OCA
# l10n-brazil ou provedor homologado, com schema/ambiente/idempotência/testes
# em homologação) for implementado, is_enabled() passa a refletir a config.
import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class DZ23Fiscal(models.AbstractModel):
    _name = "dz23.fiscal"
    _description = "DZ23 — Serviço de emissão de NF-e (desativado até homologação)"

    @api.model
    def is_enabled(self):
        """Emissão de NF-e disponível? Falso até existir adapter homologado.

        Ponto único de verdade: enquanto retornar False, o botão de emissão não
        aparece e emit() recusa. Um adapter real só deve ligar isto após passar
        em homologação SEFAZ com testes de contrato.
        """
        return False

    @api.model
    def emit(self, invoice):
        """Fail-closed: emissão indisponível até adapter homologado (ADR-002)."""
        raise UserError(
            _(
                "Emissão de NF-e não está disponível. O recurso fiscal está "
                "desativado até existir um adapter homologado por provedor "
                "(certificado e-CNPJ A1 + conta do provedor + homologação SEFAZ + "
                "validação contábil). Ver docs/adr/ADR-002-odoo-version-brazil.md."
            )
        )
