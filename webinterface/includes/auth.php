<?php
declare(strict_types=1);

const AUSZEIT_AUTH_SESSION_KEY = 'auszeit_admin_authenticated';
const AUSZEIT_CSRF_SESSION_KEY = 'auszeit_csrf_token';
const AUSZEIT_LOGIN_ATTEMPTS_FILE = __DIR__ . '/../data/auth/login-attempts.json';
const AUSZEIT_DEFAULT_MAX_LOGIN_ATTEMPTS = 10;
const AUSZEIT_DEFAULT_LOGIN_LOCK_SECONDS = 900;

function auszeit_load_config(): array
{
    $configFile = dirname(__DIR__) . '/config/local.php';
    if (!is_file($configFile)) {
        throw new RuntimeException(
            'Die lokale Webinterface-Konfiguration fehlt. Bitte config/local.php anlegen.'
        );
    }

    $config = require $configFile;
    if (!is_array($config)) {
        throw new RuntimeException('Die lokale Webinterface-Konfiguration ist ungültig.');
    }

    $passwordHash = (string)($config['admin_password_hash'] ?? '');
    if ($passwordHash === '' || password_get_info($passwordHash)['algo'] === null) {
        throw new RuntimeException('In config/local.php fehlt ein gültiger admin_password_hash.');
    }

    return $config;
}

function auszeit_is_authenticated(): bool
{
    return ($_SESSION[AUSZEIT_AUTH_SESSION_KEY] ?? false) === true;
}

function auszeit_login(string $password, array $config): bool
{
    $clientKey = auszeit_login_client_key();
    $status = auszeit_login_status($clientKey, $config);
    if ($status['locked']) {
        return false;
    }

    if (!password_verify($password, (string)$config['admin_password_hash'])) {
        auszeit_record_failed_login($clientKey, $config);
        return false;
    }

    auszeit_clear_failed_logins($clientKey);
    session_regenerate_id(true);
    $_SESSION[AUSZEIT_AUTH_SESSION_KEY] = true;
    unset($_SESSION[AUSZEIT_CSRF_SESSION_KEY]);
    return true;
}

function auszeit_login_client_key(): string
{
    $address = (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown');
    return hash('sha256', $address);
}

function auszeit_login_limits(array $config): array
{
    $maximum = max(1, (int)($config['max_login_attempts'] ?? AUSZEIT_DEFAULT_MAX_LOGIN_ATTEMPTS));
    $lockSeconds = max(60, (int)($config['login_lock_seconds'] ?? AUSZEIT_DEFAULT_LOGIN_LOCK_SECONDS));
    return [$maximum, $lockSeconds];
}

function auszeit_update_login_attempts(callable $callback): mixed
{
    $directory = dirname(AUSZEIT_LOGIN_ATTEMPTS_FILE);
    if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
        throw new RuntimeException('Der Ordner für die Anmeldesperre konnte nicht erstellt werden.');
    }

    $handle = fopen(AUSZEIT_LOGIN_ATTEMPTS_FILE, 'c+');
    if ($handle === false) {
        throw new RuntimeException('Die Anmeldesperre konnte nicht geöffnet werden.');
    }

    try {
        if (!flock($handle, LOCK_EX)) {
            throw new RuntimeException('Die Anmeldesperre konnte nicht gesperrt werden.');
        }
        rewind($handle);
        $contents = stream_get_contents($handle);
        $entries = $contents === false || trim($contents) === '' ? [] : json_decode($contents, true);
        if (!is_array($entries)) {
            $entries = [];
        }

        $result = $callback($entries);
        $encoded = json_encode($entries, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
        if ($encoded === false) {
            throw new RuntimeException('Die Anmeldesperre konnte nicht serialisiert werden.');
        }
        rewind($handle);
        if (!ftruncate($handle, 0) || fwrite($handle, $encoded . PHP_EOL) === false || !fflush($handle)) {
            throw new RuntimeException('Die Anmeldesperre konnte nicht gespeichert werden.');
        }
        flock($handle, LOCK_UN);
        return $result;
    } finally {
        fclose($handle);
    }
}

function auszeit_login_status(string $clientKey, array $config): array
{
    [$maximum, $lockSeconds] = auszeit_login_limits($config);
    return auszeit_update_login_attempts(static function (array &$entries) use ($clientKey, $maximum, $lockSeconds): array {
        $now = time();
        foreach ($entries as $key => $entry) {
            $lastFailure = (int)($entry['last_failure'] ?? 0);
            if ($lastFailure === 0 || $lastFailure + $lockSeconds <= $now) {
                unset($entries[$key]);
            }
        }
        $entry = (array)($entries[$clientKey] ?? []);
        $failures = (int)($entry['failures'] ?? 0);
        $lockedUntil = $failures >= $maximum ? (int)($entry['last_failure'] ?? 0) + $lockSeconds : 0;
        return [
            'locked' => $lockedUntil > $now,
            'remaining_attempts' => max(0, $maximum - $failures),
            'locked_until' => $lockedUntil,
        ];
    });
}

function auszeit_record_failed_login(string $clientKey, array $config): void
{
    [$maximum] = auszeit_login_limits($config);
    auszeit_update_login_attempts(static function (array &$entries) use ($clientKey, $maximum) {
        $entry = (array)($entries[$clientKey] ?? []);
        $entries[$clientKey] = [
            'failures' => min($maximum, (int)($entry['failures'] ?? 0) + 1),
            'last_failure' => time(),
        ];
        return null;
    });
}

function auszeit_clear_failed_logins(string $clientKey): void
{
    auszeit_update_login_attempts(static function (array &$entries) use ($clientKey) {
        unset($entries[$clientKey]);
        return null;
    });
}

function auszeit_csrf_token(): string
{
    $token = (string)($_SESSION[AUSZEIT_CSRF_SESSION_KEY] ?? '');
    if ($token === '') {
        $token = bin2hex(random_bytes(32));
        $_SESSION[AUSZEIT_CSRF_SESSION_KEY] = $token;
    }
    return $token;
}

function auszeit_csrf_input(): string
{
    return '<input type="hidden" name="csrf_token" value="'
        . htmlspecialchars(auszeit_csrf_token(), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')
        . '">';
}

function auszeit_verify_csrf(): void
{
    $expected = (string)($_SESSION[AUSZEIT_CSRF_SESSION_KEY] ?? '');
    $submitted = (string)($_POST['csrf_token'] ?? '');
    if ($expected === '' || $submitted === '' || !hash_equals($expected, $submitted)) {
        throw new RuntimeException('Sicherheitsprüfung fehlgeschlagen. Bitte Seite neu laden.');
    }
}

function auszeit_logout(): void
{
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(
            session_name(),
            '',
            time() - 42000,
            $params['path'],
            $params['domain'],
            $params['secure'],
            $params['httponly']
        );
    }
    session_destroy();
}
