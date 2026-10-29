-- ============================================================
-- Cybersecurity Incident Management System — Schema
-- ============================================================
USE cyber_incident_db;

-- -----------------------------------------------------------
-- People & Reference Data
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    username      VARCHAR(80)  NOT NULL UNIQUE,
    email         VARCHAR(150) UNIQUE,
    role          ENUM('Employee','Analyst','Manager','Administrator')
                  NOT NULL DEFAULT 'Employee',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysts (
    analyst_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL UNIQUE,
    specialization  VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attack_types (
    attack_type_id  INT AUTO_INCREMENT PRIMARY KEY,
    attack_name     VARCHAR(100) NOT NULL UNIQUE,
    category        VARCHAR(100),
    description     TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS incident_status (
    status_id    INT AUTO_INCREMENT PRIMARY KEY,
    status_name  VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- Core Records
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS assets (
    asset_id     INT AUTO_INCREMENT PRIMARY KEY,
    asset_name   VARCHAR(150) NOT NULL,
    asset_type   VARCHAR(60)  NOT NULL,
    ip_address   VARCHAR(45),
    owner_name   VARCHAR(100),
    criticality  ENUM('Low','Medium','High','Critical')
                 NOT NULL DEFAULT 'Medium',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vulnerabilities (
    vulnerability_id    INT AUTO_INCREMENT PRIMARY KEY,
    vulnerability_name  VARCHAR(150) NOT NULL,
    description         TEXT,
    cve_id              VARCHAR(30),
    cvss_score          DECIMAL(3,1),
    severity            ENUM('Low','Medium','High','Critical')
                        NOT NULL DEFAULT 'Medium',
    remediation         TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS incidents (
    incident_id       INT AUTO_INCREMENT PRIMARY KEY,
    incident_code     VARCHAR(20)  NOT NULL UNIQUE,
    title             VARCHAR(200) NOT NULL,
    description       TEXT,
    reported_by       INT NOT NULL,
    assigned_analyst  INT NULL,
    attack_type_id    INT NULL,
    status_id         INT NOT NULL,
    severity          ENUM('Low','Medium','High','Critical')
                      NOT NULL DEFAULT 'Medium',
    reported_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at       DATETIME  NULL,
    FOREIGN KEY (reported_by)      REFERENCES users(user_id),
    FOREIGN KEY (assigned_analyst) REFERENCES analysts(analyst_id),
    FOREIGN KEY (attack_type_id)   REFERENCES attack_types(attack_type_id),
    FOREIGN KEY (status_id)        REFERENCES incident_status(status_id),
    INDEX idx_status   (status_id),
    INDEX idx_severity (severity),
    INDEX idx_reported (reported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- Relationship Tables
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS incident_assets (
    incident_id         INT NOT NULL,
    asset_id            INT NOT NULL,
    impact_description  TEXT,
    PRIMARY KEY (incident_id, asset_id),
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id)    REFERENCES assets(asset_id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS incident_vulnerabilities (
    incident_id       INT NOT NULL,
    vulnerability_id  INT NOT NULL,
    PRIMARY KEY (incident_id, vulnerability_id),
    FOREIGN KEY (incident_id)      REFERENCES incidents(incident_id)       ON DELETE CASCADE,
    FOREIGN KEY (vulnerability_id) REFERENCES vulnerabilities(vulnerability_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- Investigation
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id    INT AUTO_INCREMENT PRIMARY KEY,
    incident_id    INT NOT NULL,
    evidence_type  VARCHAR(60)  NOT NULL,
    file_name      VARCHAR(255),
    file_hash      CHAR(64),
    description    TEXT,
    collected_by   INT NOT NULL,
    collected_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id)  REFERENCES incidents(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (collected_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mitigation_actions (
    action_id           INT AUTO_INCREMENT PRIMARY KEY,
    incident_id         INT NOT NULL,
    action_description  TEXT NOT NULL,
    performed_by        INT NOT NULL,
    action_status       ENUM('Pending','In Progress','Completed')
                        NOT NULL DEFAULT 'Pending',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME NULL,
    FOREIGN KEY (incident_id)  REFERENCES incidents(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS incident_status_history (
    history_id     INT AUTO_INCREMENT PRIMARY KEY,
    incident_id    INT NOT NULL,
    old_status_id  INT NULL,
    new_status_id  INT NOT NULL,
    changed_by     INT NOT NULL,
    change_note    TEXT,
    changed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id)   REFERENCES incidents(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (old_status_id) REFERENCES incident_status(status_id),
    FOREIGN KEY (new_status_id) REFERENCES incident_status(status_id),
    FOREIGN KEY (changed_by)    REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS incident_comments (
    comment_id    INT AUTO_INCREMENT PRIMARY KEY,
    incident_id   INT NOT NULL,
    user_id       INT NOT NULL,
    comment_text  TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- Reports
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS reports (
    report_id     INT AUTO_INCREMENT PRIMARY KEY,
    incident_id   INT NULL,
    report_title  VARCHAR(200) NOT NULL,
    generated_by  INT NOT NULL,
    generated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_notes  TEXT,
    FOREIGN KEY (incident_id)  REFERENCES incidents(incident_id),
    FOREIGN KEY (generated_by) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------
-- Reference Data
-- -----------------------------------------------------------

INSERT IGNORE INTO incident_status (status_name) VALUES
    ('Open'),
    ('Assigned'),
    ('Investigating'),
    ('Contained'),
    ('Resolved'),
    ('Closed');

INSERT IGNORE INTO attack_types (attack_name, category, description) VALUES
    ('Phishing',            'Social Engineering', 'Deceptive emails or messages to steal credentials or deploy malware.'),
    ('Malware',             'Malware',            'Malicious software including ransomware, trojans, and spyware.'),
    ('Brute Force',         'Credential Attack',  'Automated password guessing against authentication systems.'),
    ('SQL Injection',       'Web Attack',         'Injecting SQL code via web inputs to manipulate the database.'),
    ('DDoS',                'Network Attack',     'Distributed denial-of-service flooding the target with traffic.'),
    ('Unauthorized Access', 'Access Control',     'Accessing systems or data without proper authorisation.'),
    ('Insider Threat',      'Insider',            'Malicious or negligent actions by an employee or trusted party.'),
    ('Zero-Day Exploit',    'Vulnerability',      'Exploiting a previously unknown vulnerability before a patch exists.'),
    ('Man-in-the-Middle',   'Network Attack',     'Intercepting communications between two parties.'),
    ('Ransomware',          'Malware',            'Encrypts victim files and demands payment for decryption key.');
