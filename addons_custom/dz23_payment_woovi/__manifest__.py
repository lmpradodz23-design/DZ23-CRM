# -*- coding: utf-8 -*-
# DZ23 CRM — Provedor de pagamento Woovi (PIX).
# Fluxo: cria cobrança PIX via API Woovi, exibe QR Code/copia-e-cola e confirma
# via webhook. Credenciais (AppID) ficam no registro do provider (servidor).
# NOTA: o fluxo PIX ao vivo requer conta/sandbox Woovi + webhook público.
{
    "name": "DZ23 CRM — Pagamento Woovi (PIX)",
    "version": "19.0.1.0.0",
    "summary": "Provedor de pagamento PIX via Woovi.",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Accounting/Payment Providers",
    "depends": ["payment"],
    "data": [
        "views/payment_woovi_templates.xml",
        "data/payment_provider_data.xml",
        "views/payment_provider_views.xml",
    ],
    "installable": True,
    "application": False,
}
