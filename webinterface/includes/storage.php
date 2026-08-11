<?php
declare(strict_types=1);

function auszeit_write_json_atomic(string $file, array $data): void
{
    $json = json_encode(
        $data,
        JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
    );
    if ($json === false) {
        throw new RuntimeException('JSON-Daten konnten nicht kodiert werden.');
    }

    $directory = dirname($file);
    if (!is_dir($directory)) {
        throw new RuntimeException('Zielordner für JSON-Datei fehlt.');
    }

    $temporaryFile = tempnam($directory, '.auszeit-json-');
    if ($temporaryFile === false) {
        throw new RuntimeException('Temporäre JSON-Datei konnte nicht angelegt werden.');
    }

    try {
        if (file_put_contents($temporaryFile, $json . PHP_EOL, LOCK_EX) === false) {
            throw new RuntimeException('JSON-Datei konnte nicht geschrieben werden.');
        }

        $permissions = is_file($file) ? (fileperms($file) & 0777) : 0664;
        if (!chmod($temporaryFile, $permissions)) {
            throw new RuntimeException('Dateirechte der JSON-Datei konnten nicht gesetzt werden.');
        }

        if (!rename($temporaryFile, $file)) {
            throw new RuntimeException('JSON-Datei konnte nicht atomar ersetzt werden.');
        }
    } finally {
        if (is_file($temporaryFile)) {
            unlink($temporaryFile);
        }
    }
}
