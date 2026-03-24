-- db9 Global Lead Generation Schema
-- Apply via: mysql -h HOST -P 4000 -u USER -p DATABASE < schema.sql

CREATE TABLE IF NOT EXISTS leads (
    id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    website         VARCHAR(500),
    country         VARCHAR(100) NOT NULL,
    global_region   VARCHAR(50),
    sub_region      VARCHAR(100),
    geo             VARCHAR(50),
    industry        VARCHAR(100),
    company_size    VARCHAR(50),
    description     TEXT,
    db9_pain        TEXT,
    db9_use_case    TEXT,
    fit_score       INT CHECK (fit_score BETWEEN 1 AND 10),
    source_url      VARCHAR(500),
    status          VARCHAR(50) DEFAULT 'new',
    embedding       TEXT,
    created_at      DATETIME DEFAULT NOW(),
    updated_at      DATETIME DEFAULT NOW(),
    UNIQUE KEY leads_company_country_unique (company_name, country)
);

CREATE TABLE IF NOT EXISTS contacts (
    id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    lead_id         INT NOT NULL,
    role            VARCHAR(200),
    name            VARCHAR(200),
    linkedin_url    VARCHAR(500),
    email           VARCHAR(200),
    created_at      DATETIME DEFAULT NOW(),
    CONSTRAINT fk_contacts_lead FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_leads_country        ON leads(country);
CREATE INDEX IF NOT EXISTS idx_leads_global_region  ON leads(global_region);
CREATE INDEX IF NOT EXISTS idx_leads_sub_region     ON leads(sub_region);
CREATE INDEX IF NOT EXISTS idx_leads_geo            ON leads(geo);
CREATE INDEX IF NOT EXISTS idx_leads_fit_score      ON leads(fit_score);
CREATE INDEX IF NOT EXISTS idx_leads_status         ON leads(status);
CREATE INDEX IF NOT EXISTS idx_contacts_lead        ON contacts(lead_id);

-- ============================================================
-- Migration: TiDB does not support ADD COLUMN IF NOT EXISTS.
-- Run ALTER TABLE statements manually if upgrading an existing database.
--
-- ALTER TABLE leads ADD COLUMN global_region VARCHAR(50)  AFTER country;
-- ALTER TABLE leads ADD COLUMN sub_region    VARCHAR(100) AFTER global_region;
-- ALTER TABLE leads ADD COLUMN geo           VARCHAR(50)  AFTER sub_region;
-- ALTER TABLE leads ADD COLUMN company_size  VARCHAR(50)  AFTER industry;
-- ALTER TABLE leads ADD COLUMN embedding              TEXT         AFTER status;
-- ALTER TABLE leads ADD COLUMN outreach_recommendation TEXT         AFTER embedding;
--
-- UPDATE leads SET global_region = 'EMEA' WHERE global_region IS NULL;
--
-- UPDATE leads SET geo = CASE
--     WHEN global_region = 'North America' THEN 'NAMERICA'
--     WHEN global_region = 'APAC'          THEN 'APAC'
--     ELSE 'EMEA'
-- END WHERE geo IS NULL;
--
-- UPDATE leads SET sub_region = CASE
--     WHEN country IN ('United Kingdom', 'Ireland')                        THEN 'British Isles'
--     WHEN country IN ('Germany', 'Austria', 'Switzerland')                THEN 'DACH'
--     WHEN country IN ('Sweden', 'Norway', 'Denmark', 'Finland', 'Iceland') THEN 'Nordics'
--     WHEN country IN ('Netherlands', 'Belgium', 'Luxembourg')             THEN 'Benelux'
--     WHEN country IN ('Estonia', 'Latvia', 'Lithuania')                   THEN 'Baltics'
--     WHEN country IN ('France', 'Spain', 'Portugal', 'Italy', 'Greece', 'Malta', 'Cyprus') THEN 'Southern Europe'
--     WHEN country IN ('Poland', 'Czech Republic', 'Hungary', 'Romania',
--                      'Slovakia', 'Bulgaria', 'Croatia', 'Slovenia')      THEN 'Eastern Europe'
--     WHEN country IN ('Israel', 'United Arab Emirates', 'Saudi Arabia', 'Qatar',
--                      'Bahrain', 'Kuwait', 'Jordan', 'Lebanon')           THEN 'Middle East'
--     WHEN country IN ('South Africa', 'Nigeria', 'Kenya', 'Ghana',
--                      'Egypt', 'Morocco', 'Tunisia')                      THEN 'Africa'
--     WHEN country IN ('United States', 'Canada')                          THEN 'North America'
--     WHEN country IN ('Mexico', 'Brazil', 'Colombia', 'Argentina', 'Chile') THEN 'Latin America'
--     WHEN country IN ('Japan', 'South Korea', 'Taiwan', 'Hong Kong')      THEN 'East Asia'
--     WHEN country IN ('Singapore', 'Vietnam', 'Thailand', 'Indonesia', 'Malaysia', 'Philippines') THEN 'Southeast Asia'
--     WHEN country IN ('India', 'Sri Lanka')                               THEN 'South Asia'
--     WHEN country IN ('Australia', 'New Zealand')                         THEN 'Oceania'
--     ELSE 'Unknown'
-- END WHERE sub_region IS NULL;
-- ============================================================
