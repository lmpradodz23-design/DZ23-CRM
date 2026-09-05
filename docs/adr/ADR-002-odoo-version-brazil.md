# ADR-002 — Versão do Odoo para o ERP fiscal brasileiro (18.0 vs 19.0)

- Status: **Proposto — planejar migração para 18.0** (decisão do dono do
  produto em 2026-09-05). **NÃO executar downgrade sem confirmação final e sem
  o inventário/rollback abaixo validado.**
- Contexto: o DZ23 CRM roda hoje em Odoo 19.0 Community. O objetivo inclui NF-e
  e ERP fiscal brasileiro real. O ecossistema **OCA/l10n-brazil** para 19.0 se
  declara **em transição** (branch nova, cobertura fiscal ainda incompleta),
  enquanto a linha **18.0** tem localização fiscal e módulos OCA mais maduros.

## Opções

### A) Manter 19.0
- Prós: já rodando; recursos mais novos; sem trabalho de migração agora.
- Contras: OCA/l10n-brazil 19 imaturo → risco alto para NF-e/impostos; possível
  retrabalho ao acompanhar a estabilização do 19.

### B) Migrar para 18.0 (escolhida para PLANEJAMENTO)
- Prós: fiscal/OCA brasileiro mais estável e testado; base mais segura para
  emitir NF-e via OCA e para os módulos Enterprise→OSS (ver
  `OPEN_SOURCE_PARITY_MATRIX.md`).
- Contras: exige migração de dados e revalidação de todos os módulos DZ23;
  18.0 tem APIs ligeiramente diferentes das que já corrigimos no 19
  (ex.: `group_ids`, kanban `card`, ausência de `mobile`).

## Decisão

Planejar a migração para **18.0** como base do ERP fiscal. A execução do
downgrade fica **bloqueada** até:

1. **Inventário de dados** do banco atual (empresas, parceiros, leads,
   pedidos, eventos, parâmetros, usuários) exportado e conferido.
2. **Inventário de módulos**: os 9 módulos DZ23 + OCA usados, com o diff de API
   19→18 mapeado por módulo (o que muda em cada `__manifest__`/model/view).
3. **Plano de compatibilidade**: ajustar manifests para `18.0.x.y.z`, revalidar
   XPaths/campos, e reinstalar em um banco 18 limpo.
4. **Rollback**: backup completo (dump + filestore) do ambiente 19 preservado e
   testado antes de qualquer passo; caminho de volta documentado.
5. **Confirmação explícita** do dono do produto para executar.

## Consequências imediatas (sem executar downgrade)

- O fluxo fiscal (`dz23_fiscal`) fica **desabilitado/fail-closed** ("Não
  configurado") até existir adapter homologado — independentemente da versão
  (ver P0-D). Isso evita prometer NF-e antes de 18 + homologação.
- Nenhum outro pacote depende do downgrade; seguimos endurecendo o 19 (segurança,
  tenancy, fila, agente, CI) e todo esse trabalho é portável para o 18.
