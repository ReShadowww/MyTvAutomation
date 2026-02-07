-- Table to store authentication tokens and secrets
CREATE TABLE tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    client_id VARCHAR(64) NOT NULL,
    client_secret VARCHAR(64) NOT NULL,
    refresh_token VARCHAR(64) NOT NULL,
    access_token VARCHAR(64) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    auth_code VARCHAR(16) NOT NULL
);

-- Insert example data
INSERT INTO tokens (
    client_id,
    client_secret,
    refresh_token,
    access_token,
    device_id,
    auth_code
) VALUES (
    '00000000-0000-0000-0000-000000000000',    -- client_id
    '00000000-0000-0000-0000-000000000000',    -- client_secret
    '00000000-0000-0000-0000-000000000000',    -- refresh_token
    '00000000-0000-0000-0000-000000000000',    -- access_token
    '00000000-0000-0000-0000-000000000000',    -- device_id
    '000000'                                   -- auth_code
);