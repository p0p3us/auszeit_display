<?php
declare(strict_types=1);
ini_set('display_errors', '0');
// Standalone endpoint. No dependency on or changes to the existing menu admin.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function finish(int $code, bool $ok): never {
    http_response_code($code);
    echo json_encode(['ok' => $ok]);
    exit;
}

if (($_SERVER['HTTPS'] ?? '') !== 'on' && ($_SERVER['HTTPS'] ?? '') !== '1') {
    finish(403, false);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    finish(405, false);
}
if (!str_starts_with(strtolower($_SERVER['CONTENT_TYPE'] ?? ''), 'application/json')) {
    finish(415, false);
}
$raw = file_get_contents('php://input', false, null, 0, 16385);
if ($raw === false || strlen($raw) > 16384) {
    finish(413, false);
}
try {
    $payload = json_decode($raw, true, 32, JSON_THROW_ON_ERROR);
} catch (JsonException $error) {
    finish(400, false);
}
if (!is_array($payload)) {
    finish(400, false);
}
$id = $payload['device_id'] ?? null;
if (!is_string($id) || !preg_match('/\A[A-Za-z0-9_-]{1,100}\z/', $id)
    || ($payload['schema_version'] ?? null) !== 1) {
    finish(400, false);
}
$auth = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
if (!preg_match('/\ABearer ([A-Za-z0-9_-]{32,256})\z/', $auth, $match)) {
    finish(401, false);
}
// Deployment supplies only a pointer here. Actual config/data MUST be private.
$pointer = __DIR__ . '/status-config-path.php';
if (!is_file($pointer)) {
    finish(503, false);
}
$configPath = require $pointer;
$documentRoot = realpath($_SERVER['DOCUMENT_ROOT'] ?? '');
$configReal = is_string($configPath) ? realpath($configPath) : false;
if (!$configReal || !$documentRoot || str_starts_with($configReal, $documentRoot . DIRECTORY_SEPARATOR)) {
    finish(503, false);
}
$config = require $configReal;
$expected = $config['devices'][$id] ?? null;
if (!is_string($expected) || !preg_match('/\A[a-f0-9]{64}\z/', $expected)
    || !hash_equals($expected, hash('sha256', $match[1]))) {
    finish(401, false);
}
$storage = realpath($config['storage_dir'] ?? '');
if (!$storage || $storage === $documentRoot || str_starts_with($storage, $documentRoot . DIRECTORY_SEPARATOR)
    || !is_writable($storage)) {
    finish(503, false);
}
// Server receipt time is authoritative for "last contact".
$record = json_encode(['received_at' => gmdate('c'), 'status' => $payload], JSON_THROW_ON_ERROR);
$target = $storage . '/' . $id . '.json';
$lock = fopen($storage . '/' . $id . '.lock', 'c');
if (!$lock || !flock($lock, LOCK_EX)) {
    finish(503, false);
}
$temporary = $target . '.new';
$written = file_put_contents($temporary, $record);
$ok = $written === strlen($record) && chmod($temporary, 0600) && rename($temporary, $target);
flock($lock, LOCK_UN);
fclose($lock);
finish($ok ? 200 : 503, $ok);
