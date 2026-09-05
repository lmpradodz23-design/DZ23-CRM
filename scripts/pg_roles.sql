-- DZ23 CRM — separação de roles PostgreSQL (HIGH-03 da reauditoria).
-- Objetivo: o processo Odoo em produção NÃO deve conectar como SUPERUSER/
-- BYPASSRLS. Três roles: owner (dono dos objetos, NOLOGIN), migrator (só para
-- install/upgrade de módulos) e runtime (tráfego normal, apenas DML).
--
-- COMO APLICAR (uma vez, com um superusuário do cluster):
--   psql -h <host> -U postgres -f scripts/pg_roles.sql
-- Depois, migrar ownership e trocar o usuário do Odoo runtime (ver
-- docs/runbooks/postgres_roles.md). Fazer BACKUP antes (migração de ownership
-- é delicada). Definir senhas reais fora do Git (.env / vault).

-- 1) Roles (senhas são PLACEHOLDERS; troque via ALTER ROLE com valor do .env).
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dz23_owner') THEN
    CREATE ROLE dz23_owner NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dz23_migrator') THEN
    CREATE ROLE dz23_migrator LOGIN PASSWORD 'CHANGE_ME_MIGRATOR'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dz23_runtime') THEN
    CREATE ROLE dz23_runtime LOGIN PASSWORD 'CHANGE_ME_RUNTIME'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
END
$$;

-- 2) migrator pode assumir o owner (para DDL de install/upgrade).
GRANT dz23_owner TO dz23_migrator;

-- 3) runtime: conectar + DML no schema public (sem DDL, sem BYPASSRLS).
GRANT CONNECT ON DATABASE dz23crm TO dz23_runtime;
GRANT USAGE ON SCHEMA public TO dz23_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dz23_runtime;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO dz23_runtime;

-- 4) Objetos criados no futuro pelo owner ficam acessíveis ao runtime.
ALTER DEFAULT PRIVILEGES FOR ROLE dz23_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dz23_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE dz23_owner IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO dz23_runtime;

-- 5) Ownership do banco -> owner. Rodar conectado ao dz23crm, com cuidado:
--   ALTER DATABASE dz23crm OWNER TO dz23_owner;
--   REASSIGN OWNED BY odoo TO dz23_owner;   -- migra objetos existentes
-- (mantidas comentadas: exigem janela de manutenção + backup validado.)
