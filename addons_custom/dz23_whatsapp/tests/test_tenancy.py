# -*- coding: utf-8 -*-
# Provas adversariais de isolamento multi-tenant do dz23.channel:
# um usuário comum da empresa A não enxerga nem lê canais da empresa B.
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "dz23")
class TestChannelTenancy(TransactionCase):
    def setUp(self):
        super().setUp()
        Company = self.env["res.company"]
        self.cA = Company.create({"name": "Tenant A DZ23"})
        self.cB = Company.create({"name": "Tenant B DZ23"})
        Ch = self.env["dz23.channel"]
        self.chA = Ch.create({"name": "Canal A", "company_id": self.cA.id, "provider": "evolution"})
        self.chB = Ch.create({"name": "Canal B", "company_id": self.cB.id, "provider": "evolution"})
        self.userA = self.env["res.users"].create({
            "name": "Usuário A", "login": "ua_dz23_test",
            "company_id": self.cA.id, "company_ids": [(6, 0, [self.cA.id])],
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

    def test_search_hides_other_company(self):
        visiveis = self.env["dz23.channel"].with_user(self.userA).search([])
        self.assertIn(self.chA, visiveis)
        self.assertNotIn(self.chB, visiveis, "usuário de A não pode listar canal de B")

    def test_read_other_company_denied(self):
        with self.assertRaises(AccessError):
            self.chB.with_user(self.userA).read(["name"])

    def test_token_uniqueness(self):
        # tokens são gerados distintos por canal
        self.assertNotEqual(self.chA.webhook_token, self.chB.webhook_token)
