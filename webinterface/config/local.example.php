<?php
declare(strict_types=1);

return [
    // Erzeugen mit: php -r "echo password_hash('NEUES-PASSWORT', PASSWORD_DEFAULT), PHP_EOL;"
    'admin_password_hash' => '$2y$12$HIER_DEN_ERZEUGTEN_PASSWORT_HASH_EINTRAGEN',
    'max_login_attempts' => 10,
    'login_lock_seconds' => 900,
];
