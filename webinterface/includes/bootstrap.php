<?php
declare(strict_types=1);

date_default_timezone_set('Europe/Vienna');

ini_set('session.use_strict_mode', '1');
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_samesite', 'Strict');

if (!empty($_SERVER['HTTPS']) && strtolower((string)$_SERVER['HTTPS']) !== 'off') {
    ini_set('session.cookie_secure', '1');
}

session_start();
