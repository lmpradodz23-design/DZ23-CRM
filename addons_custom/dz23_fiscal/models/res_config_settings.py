from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dz23_nfe_provider = fields.Selection(
        selection=[
            ("focusnfe", "Focus NFe"),
            ("nfeio", "NFe.io"),
            ("nuvemfiscal", "Nuvem Fiscal"),
        ],
        string="Provedor de NF-e",
        config_parameter="dz23.nfe_provider",
    )
    dz23_nfe_token = fields.Char("Token do provedor de NF-e", config_parameter="dz23.nfe_token")
    dz23_nfe_base = fields.Char("Base URL (sandbox/prod)", config_parameter="dz23.nfe_base")
