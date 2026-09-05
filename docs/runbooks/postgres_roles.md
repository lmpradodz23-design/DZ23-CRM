# Runbook — separação de roles PostgreSQL (HIGH-03)

> Objetivo: o Odoo em produção deixa de conectar como SUPERUSER/BYPASSRLS.
> Requer Docker/psql de pé e uma janela de manutenção com **backup validado**.

## Estado atual (auditado)
A role `odoo` é `SUPERUSER, CREATEDB, CREATEROLE, BYPASSRLS` e dona dos bancos.
Qualquer falha/injeção no processo Odoo herda controle do cluster e ignora RLS.

## Passos (com backup antes)
1. **Backup**: `pg_dump` do `dz23crm` + cópia do volume `dz23-db`. Validar restore.
2. **Criar roles**: `psql -U postgres -f scripts/pg_roles.sql`.
3. **Senhas reais** (fora do Git): `ALTER ROLE dz23_migrator PASSWORD '<.env>';`
   e `ALTER ROLE dz23_runtime PASSWORD '<.env>';`.
4. **Migrar ownership** (conectado ao `dz23crm`):
   - `REASSIGN OWNED BY odoo TO dz23_owner;`
   - `ALTER DATABASE dz23crm OWNER TO dz23_owner;`
5. **Trocar o usuário do Odoo**:
   - tráfego normal (runtime): compose `USER/PASSWORD` = `dz23_runtime`
     (`docker-compose.yml`, env do serviço `odoo`), com `db_user/db_password`
     do `/tmp/odoo.conf` apontando para o runtime.
   - install/upgrade de módulos (`-i`/`-u`): rodar como `dz23_migrator`
     (job exclusivo), nunca com o runtime.
6. **Provar** (gate de release):
   - `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='dz23_runtime';`
     deve retornar `f, f`.
   - Uma operação DDL como runtime deve **falhar**; DML deve funcionar.
   - Teste de RLS com o runtime (sem BYPASSRLS) provando isolamento real.

## Estado nesta entrega
- `scripts/pg_roles.sql` escrito (idempotente).
- **Aplicação = BLOCKED_EXTERNAL**: exige Docker de pé + janela + backup. Não
  executada automaticamente (migração de ownership é destrutiva se malfeita).
