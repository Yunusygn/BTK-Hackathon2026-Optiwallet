-- ============================================================
-- OptiWallet Database Initialization
-- ============================================================
-- PostgreSQL ilk açıldığında çalışır
-- ============================================================

-- Ana OptiWallet database zaten oluşturuldu (POSTGRES_DB ile)
-- Mock Bank için ayrı database
CREATE DATABASE mock_bank;

-- UUID extension'ını aktif et
\c optiwallet;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

\c mock_bank;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Başarı mesajı
\echo 'OptiWallet databases initialized successfully.'