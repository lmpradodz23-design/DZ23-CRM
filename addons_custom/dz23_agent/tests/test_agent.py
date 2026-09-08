# Agente determinístico (HIGH-04): agenda não assume hora, rejeita passado,
# evita double-booking; venda distingue preço de compra, exige produto não
# ambíguo, casa com acentos. LLM não cria evento/pedido diretamente.
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "dz23")
class TestAgentDeterministic(TransactionCase):
    def setUp(self):
        super().setUp()
        self.channel = self.env["dz23.channel"].create(
            {
                "name": "Canal Agente",
                "company_id": self.env.company.id,
                "provider": "evolution",
                "evo_base": "http://x.local:8080",
                "evo_instance": "agente_inst",
                "evo_apikey": "K",
            }
        )
        P = self.env["product.template"]
        # nomes únicos (o banco compartilhado pode ter produtos de mesmo nome)
        self.corte = P.create(
            {"name": "Servico Alfa QA1", "type": "service", "list_price": 50.0, "sale_ok": True}
        )
        self.manut = P.create(
            {"name": "Manutenção Zeta QA1", "type": "service", "list_price": 90.0, "sale_ok": True}
        )
        # dois produtos para ambiguidade
        self.masc = P.create(
            {"name": "Combo Delta QA1", "type": "service", "list_price": 30.0, "sale_ok": True}
        )
        self.fem = P.create(
            {"name": "Combo Epsilon QA1", "type": "service", "list_price": 40.0, "sale_ok": True}
        )
        self.lead = self.channel._agent_find_lead("5561900000001")
        self.orders0 = self._orders_total()

    def _events(self):
        return self.env["calendar.event"].search_count([("opportunity_id", "=", self.lead.id)])

    def _orders_total(self):
        return self.env["sale.order"].search_count(
            [("origin", "=", "WhatsApp DZ23"), ("company_id", "=", self.env.company.id)]
        )

    def _orders(self):
        # DELTA desde o setUp (o banco compartilhado pode ter pedidos antigos).
        return self._orders_total() - self.orders0

    # ----- agenda -----
    def test_no_time_asks_and_no_event(self):
        r = self.channel._handle_schedule(self.lead, "quero agendar dia 15/09")
        self.assertIn("horário", r.lower())
        self.assertEqual(self._events(), 0)

    def test_no_date_asks(self):
        r = self.channel._handle_schedule(self.lead, "quero agendar")
        self.assertIn("dia", r.lower())
        self.assertEqual(self._events(), 0)

    def test_past_rejected(self):
        r = self.channel._handle_schedule(self.lead, "agendar 01/01/2020 as 10:00")
        self.assertIn("passou", r.lower())
        self.assertEqual(self._events(), 0)

    def test_invalid_date(self):
        r = self.channel._handle_schedule(self.lead, "agendar 31/02/2099 as 10:00")
        self.assertTrue("não" in r.lower() or "confirmar" in r.lower())
        self.assertEqual(self._events(), 0)

    def test_future_creates_event(self):
        r = self.channel._handle_schedule(self.lead, "agendar 31/12/2099 as 14:30")
        self.assertEqual(self._events(), 1)
        self.assertIn("31/12/2099", r)

    def test_conflict_no_double_booking(self):
        self.channel._handle_schedule(self.lead, "agendar 30/12/2099 as 09:00")
        r2 = self.channel._handle_schedule(self.lead, "agendar 30/12/2099 as 09:00")
        self.assertIn("reservado", r2.lower())
        self.assertEqual(self._events(), 1)

    def test_conflict_isolated_by_company(self):
        # Mesmo horário em OUTRA empresa NÃO deve bloquear (multi-tenant):
        # o conflito é escopado por opportunity_id.company_id.
        self.channel._handle_schedule(self.lead, "agendar 29/12/2099 as 08:00")
        company_b = self.env["res.company"].create({"name": "Empresa B QA1"})
        channel_b = self.env["dz23.channel"].create(
            {
                "name": "Canal B",
                "company_id": company_b.id,
                "provider": "evolution",
                "evo_base": "http://x.local:8080",
                "evo_instance": "agente_inst_b",
                "evo_apikey": "K",
            }
        )
        lead_b = channel_b._agent_find_lead("5561900000002")
        r = channel_b._handle_schedule(lead_b, "agendar 29/12/2099 as 08:00")
        # empresa B consegue agendar o mesmo horário (sem "reservado")
        self.assertNotIn("reservado", r.lower())
        self.assertEqual(
            self.env["calendar.event"].search_count([("opportunity_id", "=", lead_b.id)]), 1
        )

    # ----- venda -----
    def test_price_does_not_create_order(self):
        r = self.channel._handle_price(self.lead, "quanto custa o Servico Alfa QA1?")
        self.assertEqual(self._orders(), 0)
        self.assertIn("50", r)

    def test_buy_single_creates_order(self):
        r = self.channel._handle_buy(self.lead, "quero comprar Servico Alfa QA1")
        self.assertEqual(self._orders(), 1)
        self.assertIn("Servico Alfa QA1", r)

    def test_buy_ambiguous_asks_no_order(self):
        r = self.channel._handle_buy(
            self.lead, "quero comprar Combo Delta QA1 ou Combo Epsilon QA1"
        )
        self.assertEqual(self._orders(), 0)
        self.assertTrue("qual" in r.lower() or "opç" in r.lower() or "opc" in r.lower())

    def test_accent_insensitive_match(self):
        # "manutencao zeta qa1" (sem acento) casa com "Manutenção Zeta QA1"
        r = self.channel._handle_price(self.lead, "quanto custa manutencao zeta qa1")
        self.assertIn("90", r)
        self.assertEqual(self._orders(), 0)
