# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .brasil_api import only_digits


class ResPartner(models.Model):
    _inherit = "res.partner"

    # --- Enriquecimento via CNPJ (BrasilAPI) ---
    dz23_cnpj_situacao = fields.Char("Situação cadastral", readonly=True)
    dz23_cnpj_porte = fields.Char("Porte", readonly=True)
    dz23_cnpj_cnae = fields.Char("CNAE principal", readonly=True)
    dz23_cnpj_natureza = fields.Char("Natureza jurídica", readonly=True)
    dz23_simples_nacional = fields.Boolean("Optante Simples", readonly=True)
    dz23_mei = fields.Boolean("MEI", readonly=True)
    dz23_last_enrich = fields.Datetime("Último enriquecimento", readonly=True)

    # --- WhatsApp (wa.me) ---
    dz23_whatsapp_link = fields.Char(
        "Link WhatsApp", compute="_compute_dz23_whatsapp_link", store=False
    )

    @api.depends("mobile", "phone")
    def _compute_dz23_whatsapp_link(self):
        for p in self:
            raw = only_digits(p.mobile or p.phone or "")
            link = False
            if raw:
                # normaliza para E.164 BR (adiciona 55 quando faltar)
                if not raw.startswith("55") and len(raw) in (10, 11):
                    raw = "55" + raw
                if 12 <= len(raw) <= 13:
                    link = "https://wa.me/%s" % raw
            p.dz23_whatsapp_link = link

    # --- helpers ---
    def _dz23_state_from_uf(self, uf):
        if not uf:
            return False
        br = self.env.ref("base.br", raise_if_not_found=False)
        domain = [("code", "=", uf)]
        if br:
            domain.append(("country_id", "=", br.id))
        return self.env["res.country.state"].search(domain, limit=1)

    def _dz23_fill_address(self, d, overwrite=False):
        br = self.env.ref("base.br", raise_if_not_found=False)
        if br:
            self.country_id = br
        street = d.get("street_name") or ""
        if d.get("number"):
            street = (street + ", " + d["number"]).strip(", ")
        if street and (overwrite or not self.street):
            self.street = street
        if d.get("district") and (overwrite or not self.street2):
            self.street2 = d["district"]
        if d.get("city"):
            self.city = d["city"]
        if d.get("zip"):
            self.zip = d["zip"]
        st = self._dz23_state_from_uf(d.get("state_code"))
        if st:
            self.state_id = st

    def _dz23_fill_from_cnpj(self, d):
        self.company_type = "company"
        if not self.name and (d.get("trade_name") or d.get("legal_name")):
            self.name = d.get("trade_name") or d.get("legal_name")
        self._dz23_fill_address(d, overwrite=False)
        if d.get("phone") and not self.phone:
            self.phone = d["phone"]
        if d.get("email") and not self.email:
            self.email = d["email"]
        self.dz23_cnpj_situacao = d.get("situacao")
        self.dz23_cnpj_porte = d.get("porte")
        self.dz23_cnpj_cnae = d.get("cnae")
        self.dz23_cnpj_natureza = d.get("natureza")
        self.dz23_simples_nacional = d.get("simples")
        self.dz23_mei = d.get("mei")
        self.dz23_last_enrich = fields.Datetime.now()

    # --- onchange: autofill automático ao digitar ---
    @api.onchange("zip")
    def _dz23_onchange_zip(self):
        if not self.zip or len(only_digits(self.zip)) != 8:
            return
        try:
            d = self.env["dz23.brasil.api"].fetch_cep(self.zip)
        except UserError as e:
            return {"warning": {"title": _("CEP"), "message": str(e)}}
        if d:
            self._dz23_fill_address(d, overwrite=False)

    @api.onchange("vat")
    def _dz23_onchange_vat(self):
        if len(only_digits(self.vat)) != 14:
            return
        try:
            d = self.env["dz23.brasil.api"].fetch_cnpj(self.vat)
        except UserError as e:
            return {"warning": {"title": _("CNPJ"), "message": str(e)}}
        if d:
            self._dz23_fill_from_cnpj(d)

    # --- botões (busca manual explícita) ---
    def action_dz23_buscar_cep(self):
        for p in self:
            if p.zip and len(only_digits(p.zip)) == 8:
                d = p.env["dz23.brasil.api"].fetch_cep(p.zip)
                if d:
                    p._dz23_fill_address(d, overwrite=True)
                else:
                    raise UserError(_("CEP não encontrado."))
        return True

    def action_dz23_enriquecer_cnpj(self):
        for p in self:
            if len(only_digits(p.vat)) != 14:
                raise UserError(_("Informe um CNPJ válido (14 dígitos) no campo NIF/CNPJ."))
            d = p.env["dz23.brasil.api"].fetch_cnpj(p.vat)
            if d:
                p._dz23_fill_from_cnpj(d)
            else:
                raise UserError(_("CNPJ não encontrado."))
        return True
