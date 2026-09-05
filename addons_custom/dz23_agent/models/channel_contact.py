# Adiciona o vínculo com crm.lead à identidade de canal (dz23.channel.contact).
# Fica aqui (dz23_agent depende de crm) e não no dz23_whatsapp base.
from odoo import fields, models


class DZ23ChannelContact(models.Model):
    _inherit = "dz23.channel.contact"

    lead_id = fields.Many2one("crm.lead", check_company=True, index=True)
