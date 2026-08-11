<?php
declare(strict_types=1);
require_once __DIR__ . '/menu-layout.php';

$raw = file_get_contents('php://input');
$data = json_decode($raw ?: '{}', true);
if (!is_array($data)) {
    $data = [];
}
header('Content-Type: text/html; charset=UTF-8');
echo (($_GET['mode'] ?? '') === 'flyer') ? render_menu_flyer_sheet($data, true) : render_menu_document($data, true);
