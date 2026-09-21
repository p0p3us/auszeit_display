<?php
declare(strict_types=1);
header('Content-Type: text/html; charset=UTF-8');

require_once __DIR__ . '/includes/bootstrap.php';

require_once __DIR__ . '/menu-layout.php';
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/storage.php';

const MENU_DIR = __DIR__ . '/data/menus';
const MENU_INDEX_FILE = MENU_DIR . '/index.json';

function h(string $v): string { return htmlspecialchars($v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function clean($v): string { return trim((string)$v); }
function safe_name(string $name): string {
    $name = preg_replace('/\.json$/i', '', trim($name)) ?? '';
    $name = preg_replace('/[^a-zA-Z0-9_-]+/', '-', $name) ?? '';
    return trim($name, '-_');
}
function empty_data(): array {
    return [
        'updated_at' => '', 'valid_from' => '', 'valid_to' => '', 'service_time' => '11:00 - 14:00',
        'weekdays' => [
            'dienstag' => ['soup'=>'Tagessuppe','title'=>'','side'=>'','price'=>''],
            'mittwoch' => ['soup'=>'Tagessuppe','title'=>'','side'=>'','price'=>''],
            'donnerstag' => ['soup'=>'Tagessuppe','title'=>'','side'=>'','price'=>''],
            'freitag' => [
                'menu_1' => ['soup'=>'Tagessuppe','title'=>'','side'=>'','price'=>''],
                'menu_2' => ['enabled'=>false,'soup'=>'','title'=>'','side'=>'','price'=>''],
            ],
        ],
        'weekly_special' => ['enabled'=>false,'title'=>'','side'=>'','price'=>''],
        'info_blocks' => [
            ['enabled'=>false,'heading'=>'Wochenendevent','text'=>'','vertical_align'=>'center'],
            ['enabled'=>false,'heading'=>'Allgemeine Information','text'=>'','vertical_align'=>'center'],
            ['enabled'=>false,'heading'=>'Weiterer Hinweis','text'=>'','vertical_align'=>'center'],
        ],
    ];
}
function ensure_dir(): void {
    if (!is_dir(MENU_DIR) && !mkdir(MENU_DIR, 0775, true) && !is_dir(MENU_DIR)) {
        throw new RuntimeException('Der Ordner data/menus konnte nicht erstellt werden.');
    }
}
function list_files(): array {
    ensure_dir();
    $files = array_values(array_filter(
        glob(MENU_DIR . '/*.json') ?: [],
        static fn(string $path): bool => basename($path) !== 'index.json'
    ));
    usort($files, fn($a,$b) => filemtime($b) <=> filemtime($a));
    return array_map(fn($p) => basename($p, '.json'), $files);
}

function rebuild_menu_index(): array {
    ensure_dir();
    $entries = [];
    foreach (glob(MENU_DIR . '/*.json') ?: [] as $path) {
        if (basename($path) === 'index.json') continue;
        $decoded = json_decode((string)file_get_contents($path), true);
        if (!is_array($decoded)) continue;
        $validFrom = clean($decoded['valid_from'] ?? '');
        $validUntil = clean($decoded['valid_to'] ?? $decoded['valid_until'] ?? '');
        if ($validFrom === '' || $validUntil === '') continue;
        $entries[] = [
            'file' => basename($path),
            'valid_from' => $validFrom,
            'valid_until' => $validUntil,
        ];
    }
    usort($entries, static function(array $a, array $b): int {
        $byStart = strcmp((string)$a['valid_from'], (string)$b['valid_from']);
        return $byStart !== 0 ? $byStart : strcmp((string)$a['file'], (string)$b['file']);
    });
    $payload = [
        'generated_at' => date(DATE_ATOM),
        'menus' => $entries,
    ];
    auszeit_write_json_atomic(MENU_INDEX_FILE, $payload);
    return $payload;
}

function load_file(string $name): array {
    $path = MENU_DIR . '/' . safe_name($name) . '.json';
    if (!is_file($path)) return empty_data();
    $decoded = json_decode((string)file_get_contents($path), true);
    return is_array($decoded) ? array_replace_recursive(empty_data(), $decoded) : empty_data();
}
function post_data(): array {
    return [
        'updated_at' => date('c'),
        'valid_from' => clean($_POST['valid_from'] ?? ''),
        'valid_to' => clean($_POST['valid_to'] ?? ''),
        'service_time' => clean($_POST['service_time'] ?? '11:00 - 14:00'),
        'weekdays' => [
            'dienstag' => ['soup'=>clean($_POST['di_soup']??''),'title'=>clean($_POST['di_title']??''),'side'=>clean($_POST['di_side']??''),'price'=>clean($_POST['di_price']??'')],
            'mittwoch' => ['soup'=>clean($_POST['mi_soup']??''),'title'=>clean($_POST['mi_title']??''),'side'=>clean($_POST['mi_side']??''),'price'=>clean($_POST['mi_price']??'')],
            'donnerstag' => ['soup'=>clean($_POST['do_soup']??''),'title'=>clean($_POST['do_title']??''),'side'=>clean($_POST['do_side']??''),'price'=>clean($_POST['do_price']??'')],
            'freitag' => [
                'menu_1'=>['soup'=>clean($_POST['fr1_soup']??''),'title'=>clean($_POST['fr1_title']??''),'side'=>clean($_POST['fr1_side']??''),'price'=>clean($_POST['fr1_price']??'')],
                'menu_2'=>['enabled'=>isset($_POST['fr2_enabled']),'soup'=>clean($_POST['fr2_soup']??''),'title'=>clean($_POST['fr2_title']??''),'side'=>clean($_POST['fr2_side']??''),'price'=>clean($_POST['fr2_price']??'')],
            ],
        ],
        'weekly_special' => ['enabled'=>isset($_POST['weekly_enabled']),'title'=>clean($_POST['weekly_title']??''),'side'=>clean($_POST['weekly_side']??''),'price'=>clean($_POST['weekly_price']??'')],
        'info_blocks' => [
            ['enabled'=>isset($_POST['info1_enabled']),'heading'=>clean($_POST['info1_heading']??''),'text'=>menu_sanitize_rich_text((string)($_POST['info1_text']??'')),'vertical_align'=>menu_vertical_align($_POST['info1_vertical']??'center')],
            ['enabled'=>isset($_POST['info2_enabled']),'heading'=>clean($_POST['info2_heading']??''),'text'=>menu_sanitize_rich_text((string)($_POST['info2_text']??'')),'vertical_align'=>menu_vertical_align($_POST['info2_vertical']??'center')],
            ['enabled'=>isset($_POST['info3_enabled']),'heading'=>clean($_POST['info3_heading']??''),'text'=>menu_sanitize_rich_text((string)($_POST['info3_text']??'')),'vertical_align'=>menu_vertical_align($_POST['info3_vertical']??'center')],
        ],
    ];
}


function active_background_file(): string {
    foreach (['png','jpg','jpeg','webp'] as $ext) {
        $path = __DIR__ . '/assets/menu-background.' . $ext;
        if (is_file($path)) return $path;
    }
    return '';
}
function remove_custom_background(): void {
    foreach (['png','jpg','jpeg','webp'] as $ext) {
        $path = __DIR__ . '/assets/menu-background.' . $ext;
        if (is_file($path)) @unlink($path);
    }
}
function save_uploaded_background(array $file): string {
    if (($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
        throw new RuntimeException('Bitte zuerst eine PNG-, JPG- oder WebP-Grafik auswählen.');
    }
    if ((int)($file['size'] ?? 0) > 20 * 1024 * 1024) {
        throw new RuntimeException('Die Grafik ist größer als 20 MB.');
    }
    $tmp = (string)($file['tmp_name'] ?? '');
    $imageInfo = @getimagesize($tmp);
    if ($imageInfo === false) {
        throw new RuntimeException('Die hochgeladene Datei ist keine gültige Grafik.');
    }
    $mime = (string)($imageInfo['mime'] ?? '');
    $extensions = ['image/png'=>'png','image/jpeg'=>'jpg','image/webp'=>'webp'];
    if (!isset($extensions[$mime])) {
        throw new RuntimeException('Erlaubt sind PNG, JPG und WebP.');
    }
    $assetsDir = __DIR__ . '/assets';
    if (!is_dir($assetsDir) && !mkdir($assetsDir, 0775, true) && !is_dir($assetsDir)) {
        throw new RuntimeException('Der assets-Ordner konnte nicht erstellt werden.');
    }
    remove_custom_background();
    $target = $assetsDir . '/menu-background.' . $extensions[$mime];
    if (!move_uploaded_file($tmp, $target)) {
        throw new RuntimeException('Die Grafik konnte nicht gespeichert werden.');
    }
    return basename($target);
}

try {
    $appConfig = auszeit_load_config();
} catch (Throwable $configError) {
    http_response_code(503);
    exit('Webinterface nicht konfiguriert.');
}

if (!auszeit_is_authenticated()) {
    $error='';
    $loginStatus = auszeit_login_status(auszeit_login_client_key(), $appConfig);
    if ($_SERVER['REQUEST_METHOD']==='POST' && isset($_POST['password'])) {
        if ($loginStatus['locked']) {
            $error='Zu viele Fehlversuche. Die Anmeldung ist 15 Minuten gesperrt.';
        } elseif (auszeit_login((string)$_POST['password'], $appConfig)) {
            header('Location: ' . $_SERVER['REQUEST_URI']); exit;
        } else {
            $loginStatus = auszeit_login_status(auszeit_login_client_key(), $appConfig);
            $error = $loginStatus['locked']
                ? '10 Fehlversuche erreicht. Die Anmeldung ist 15 Minuten gesperrt.'
                : 'Falsches Passwort. Verbleibende Versuche: ' . $loginStatus['remaining_attempts'] . '.';
        }
    }
    ?><!doctype html><html lang="de"><meta charset="utf-8"><title>Auszeit Menüverwaltung</title><style>body{font-family:Arial;background:#5d0b11;display:grid;place-items:center;min-height:100vh;margin:0}.box{background:#fff;padding:30px;border-radius:12px;width:360px}input,button{width:100%;padding:12px;margin-top:10px;box-sizing:border-box}</style><div class="box"><h1>Anmeldung</h1><?php if($error):?><p><?=h($error)?></p><?php endif;?><form method="post"><input type="password" name="password" autofocus required><button>Anmelden</button></form></div></html><?php exit;
}

ensure_dir();
$message=''; $error='';
$selected = safe_name((string)($_POST['selected_file'] ?? $_GET['file'] ?? ''));
$data = $selected !== '' ? load_file($selected) : empty_data();

if ($_SERVER['REQUEST_METHOD']==='POST') {
    try {
        auszeit_verify_csrf();
        if (isset($_POST['logout'])) { auszeit_logout(); header('Location: menu_admin.php'); exit; }
        elseif (isset($_POST['new'])) { $selected=''; $data=empty_data(); }
        elseif (isset($_POST['load'])) { $selected=safe_name((string)($_POST['selected_file']??'')); $data=load_file($selected); $message='Menü geladen.'; }
        elseif (isset($_POST['upload_background'])) {
            $data=post_data();
            $savedFile = save_uploaded_background($_FILES['background_image'] ?? []);
            $message='Neue Hintergrundgrafik wurde gespeichert: ' . $savedFile;
        }
        elseif (isset($_POST['reset_background'])) {
            $data=post_data();
            remove_custom_background();
            $message='Der Standard-Goldstoff ist wieder aktiv.';
        }
        elseif (isset($_POST['save'])) {
            $data=post_data();
            $name=safe_name((string)($_POST['file_name']??''));
            if ($name==='') throw new RuntimeException('Bitte eine Dateibezeichnung eingeben.');
            $selected=$name;
            $jsonPath=MENU_DIR.'/'.$name.'.json';
            auszeit_write_json_atomic($jsonPath, $data);
            rebuild_menu_index();
            $message='JSON und index.json gespeichert.';
        }
    } catch (Throwable $e) { $error=$e->getMessage(); }
}
try { rebuild_menu_index(); } catch (Throwable $indexError) { if ($error === '') $error = $indexError->getMessage(); }
$files=list_files();
function val(array $a, string $path): string { foreach(explode('.',$path) as $k){ $a=$a[$k]??''; } return is_scalar($a)?(string)$a:''; }
function is_checked(array $a, string $path): bool { foreach(explode('.',$path) as $k){ if (!is_array($a) || !array_key_exists($k,$a)) return false; $a=$a[$k]; } return (bool)$a; }
?>
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auszeit Menüverwaltung</title>
<link href="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.snow.css" rel="stylesheet">
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#ebe6de;color:#2c211d}header{background:#5d0b11;color:#fff;padding:18px 24px;display:flex;justify-content:space-between}header nav{display:flex;gap:18px;align-items:center;flex-wrap:wrap}header a{color:#fff;text-decoration:none;font-weight:bold}header a.active{color:#f1d37b;border-bottom:2px solid #f1d37b;padding-bottom:4px}.wrap{display:grid;grid-template-columns:minmax(560px,1fr) minmax(420px,.82fr);gap:18px;padding:18px;align-items:start}.panel{background:#fff;border:1px solid #d8cec2;border-radius:12px;padding:18px}.toolbar{display:grid;grid-template-columns:1fr 1fr;gap:10px}.toolbar .wide{grid-column:1/-1}.section{border-top:2px solid #b58b36;margin-top:18px;padding-top:14px}.section h2{color:#71131d;margin:0 0 12px;font-family:Georgia,serif}.optional-switch{display:flex;align-items:center;gap:8px;margin:0 0 12px;padding:9px 11px;background:#f7f0df;border:1px solid #d4b66a;border-radius:7px;font-weight:bold;color:#5d0b11}.optional-switch input{width:auto;margin:0;transform:scale(1.2)}.grid4{display:grid;grid-template-columns:1fr 2fr 2fr .8fr;gap:9px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}label{display:block;font-size:12px;font-weight:bold;margin-bottom:4px}input,textarea,select,button{width:100%;padding:9px;border:1px solid #b9aea5;border-radius:6px;font:inherit}textarea{min-height:70px;resize:vertical}button{background:#71131d;color:#fff;border:0;font-weight:bold;cursor:pointer}.secondary{background:#7d746d}.gold{background:#a07828}.msg{padding:10px;border-radius:7px;margin-bottom:10px;background:#e0f0df}.err{background:#f4d8dc;color:#7d111b}.preview-panel{position:sticky;top:12px}.preview-head{display:flex;gap:8px;align-items:center;margin-bottom:10px}.preview-head button{width:auto;padding:8px 14px}.preview-wrap{height:calc(100vh - 110px);min-height:650px;background:#3a3a3a;overflow:auto;padding:10px}.preview-wrap iframe{width:100%;height:100%;border:0;background:#333}@media(max-width:1100px){.wrap{grid-template-columns:1fr}.preview-panel{position:static}.preview-wrap{height:760px}}.rich-editor{min-height:95px;background:#fff}.ql-toolbar.ql-snow{border-color:#b9aea5;border-radius:6px 6px 0 0}.ql-container.ql-snow{border-color:#b9aea5;border-radius:0 0 6px 6px;font-family:Arial,sans-serif;font-size:15px}.ql-editor{min-height:95px}.ql-editor p{margin:0}
@media(max-width:700px){.grid4,.grid2,.toolbar{grid-template-columns:1fr}.toolbar .wide{grid-column:auto}}
</style></head><body>
<header><h1>Auszeit Verwaltung</h1><nav><a class="active" href="menu_admin.php">Menüverwaltung</a><a href="termine-admin.php">Terminverwaltung</a><form method="post" style="margin:0"><?=auszeit_csrf_input()?><button name="logout" style="width:auto;padding:0;background:none">Abmelden</button></form></nav></header>
<div class="wrap"><div class="panel">
<?php if($message):?><div class="msg"><?=h($message)?></div><?php endif;?><?php if($error):?><div class="msg err"><?=h($error)?></div><?php endif;?>
<form method="post" id="menuForm" enctype="multipart/form-data">
<?=auszeit_csrf_input()?>
<div class="toolbar">
<div><label>Gespeichertes Menü</label><select name="selected_file"><option value="">- Datei auswählen -</option><?php foreach($files as $f):?><option value="<?=h($f)?>" <?=$f===$selected?'selected':''?>><?=h($f)?></option><?php endforeach;?></select></div>
<div><label>Dateibezeichnung</label><input name="file_name" value="<?=h($selected)?>" placeholder="z. B. menue-2026-08-04"></div>
<button name="load">Ausgewählte Datei laden</button><button class="secondary" name="new">Neues leeres Menü</button>
<button name="save">JSON speichern</button><button class="gold" type="button" id="downloadPng">Grafik – Plakat / Facebook</button><button class="gold wide" type="button" id="downloadFlyer">Druckbogen – 2 × A5 auf A4 quer</button>
<div class="wide"><label>Eigene Hintergrundgrafik statt Goldstoff</label><input type="file" name="background_image" accept="image/png,image/jpeg,image/webp"></div>
<button name="upload_background">Grafik hochladen</button><button class="secondary" name="reset_background" formnovalidate>Standard-Goldstoff verwenden</button>
</div>
<p style="margin:10px 0 0;font-size:13px;color:#665a52">Aktiver Hintergrund: <?= h(active_background_file() !== '' ? basename(active_background_file()) : 'gold.jpg (Standard)') ?></p>
<div class="section"><h2>Kopfbereich</h2><div class="grid2"><div><label>Gültig von</label><input type="date" name="valid_from" value="<?=h(val($data,'valid_from'))?>"></div><div><label>Gültig bis</label><input type="date" name="valid_to" value="<?=h(val($data,'valid_to'))?>"></div><div><label>Ausgabezeit</label><input name="service_time" value="<?=h(val($data,'service_time'))?>"></div></div></div>
<?php $days=['di'=>'Dienstag','mi'=>'Mittwoch','do'=>'Donnerstag']; foreach($days as $p=>$label): $key=['di'=>'dienstag','mi'=>'mittwoch','do'=>'donnerstag'][$p]; ?>
<div class="section"><h2><?=$label?></h2><div class="grid4"><div><label>Suppe</label><input name="<?=$p?>_soup" value="<?=h(val($data,"weekdays.$key.soup"))?>"></div><div><label>Speise</label><input name="<?=$p?>_title" value="<?=h(val($data,"weekdays.$key.title"))?>"></div><div><label>Beilage</label><input name="<?=$p?>_side" value="<?=h(val($data,"weekdays.$key.side"))?>"></div><div><label>Preis</label><input name="<?=$p?>_price" value="<?=h(val($data,"weekdays.$key.price"))?>"></div></div></div>
<?php endforeach; ?>
<div class="section"><h2>Freitag - Menü 1</h2><div class="grid4"><div><label>Suppe</label><input name="fr1_soup" value="<?=h(val($data,'weekdays.freitag.menu_1.soup'))?>"></div><div><label>Speise</label><input name="fr1_title" value="<?=h(val($data,'weekdays.freitag.menu_1.title'))?>"></div><div><label>Beilage</label><input name="fr1_side" value="<?=h(val($data,'weekdays.freitag.menu_1.side'))?>"></div><div><label>Preis</label><input name="fr1_price" value="<?=h(val($data,'weekdays.freitag.menu_1.price'))?>"></div></div></div>
<div class="section"><h2>Freitag - Menü 2 (optional)</h2><label class="optional-switch"><input type="checkbox" name="fr2_enabled" value="1" <?=is_checked($data,'weekdays.freitag.menu_2.enabled')?'checked':''?>> In Vorschau und Grafik anzeigen</label><div class="grid4"><div><label>Suppe</label><input name="fr2_soup" value="<?=h(val($data,'weekdays.freitag.menu_2.soup'))?>"></div><div><label>Speise</label><input name="fr2_title" value="<?=h(val($data,'weekdays.freitag.menu_2.title'))?>"></div><div><label>Beilage</label><input name="fr2_side" value="<?=h(val($data,'weekdays.freitag.menu_2.side'))?>"></div><div><label>Preis</label><input name="fr2_price" value="<?=h(val($data,'weekdays.freitag.menu_2.price'))?>"></div></div></div>
<div class="section"><h2>Wochenschmankerl (optional)</h2><label class="optional-switch"><input type="checkbox" name="weekly_enabled" value="1" <?=is_checked($data,'weekly_special.enabled')?'checked':''?>> In Vorschau, Druckausgabe und Bildschirmfolie anzeigen</label><div class="grid4"><div><label>Bezeichnung</label><input value="Wochenschmankerl" disabled></div><div><label>Hauptspeise</label><input name="weekly_title" value="<?=h(val($data,'weekly_special.title'))?>" placeholder="z. B. Zander vom Grill"></div><div><label>Beilage</label><input name="weekly_side" value="<?=h(val($data,'weekly_special.side'))?>" placeholder="z. B. Petersilienerdäpfel und grüner Salat"></div><div><label>Preis</label><input name="weekly_price" value="<?=h(val($data,'weekly_special.price'))?>" placeholder="16,90"></div></div><p style="font-size:13px;color:#665a52">Ein bisheriger Hinweis zum Wochenschmankerl bleibt gespeichert. Deaktiviere ihn nach dem Übertragen, damit das Angebot nicht doppelt erscheint.</p></div>
<?php for($i=1;$i<=3;$i++): $idx=$i-1; $richValue=menu_sanitize_rich_text(val($data,'info_blocks.'.$idx.'.text')); $vertical=menu_vertical_align(val($data,'info_blocks.'.$idx.'.vertical_align')); ?><div class="section"><h2>Hinweis / Event <?=$i?> (optional)</h2><label class="optional-switch"><input type="checkbox" name="info<?=$i?>_enabled" value="1" <?=is_checked($data,'info_blocks.'.$idx.'.enabled')?'checked':''?>> In Vorschau und Grafik anzeigen</label><div class="grid2"><div><label>Überschrift</label><input name="info<?=$i?>_heading" value="<?=h(val($data,'info_blocks.'.$idx.'.heading'))?>"><label style="margin-top:10px">Vertikale Ausrichtung</label><select name="info<?=$i?>_vertical"><option value="top" <?=$vertical==='top'?'selected':''?>>Oben</option><option value="center" <?=$vertical==='center'?'selected':''?>>Mittig</option><option value="bottom" <?=$vertical==='bottom'?'selected':''?>>Unten</option></select></div><div><label>Formatierter Text</label><input type="hidden" name="info<?=$i?>_text" id="info<?=$i?>_text" value="<?=h($richValue)?>"><div class="rich-editor" id="info<?=$i?>_editor"></div></div></div></div><?php endfor;?>
</form></div>
<div class="panel preview-panel"><div class="preview-head"><strong>Live-Vorschau</strong><button type="button" id="refreshPreview">Jetzt aktualisieren</button></div><div class="preview-wrap"><iframe id="previewFrame" title="Menüvorschau"></iframe></div></div>
</div><iframe id="flyerFrame" title="Druckbogen" style="position:fixed;left:-10000px;top:0;width:1123px;height:794px;border:0;visibility:hidden"></iframe>
<script src="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script>
const quillEditors={};
for(let i=1;i<=3;i++){
  const hidden=document.getElementById(`info${i}_text`);
  const editorElement=document.getElementById(`info${i}_editor`);
  const quill=new Quill(editorElement,{theme:'snow',modules:{toolbar:[
    [{size:['small',false,'large']}],
    ['bold','italic','underline'],
    [{align:['','center','right']}],
    [{color:[]},{background:[]}],
    ['clean']
  ]}});
  quill.clipboard.dangerouslyPasteHTML(hidden.value||'');
  quill.on('text-change',()=>{hidden.value=quill.getSemanticHTML();scheduleRefresh();});
  quillEditors[i]=quill;
}
function syncRichEditors(){for(const [i,q] of Object.entries(quillEditors)){document.getElementById(`info${i}_text`).value=q.getSemanticHTML();}}
const form=document.getElementById('menuForm'); const frame=document.getElementById('previewFrame'); let timer;
function dataFromForm(){syncRichEditors();const fd=new FormData(form);return {
valid_from:fd.get('valid_from')||'',valid_to:fd.get('valid_to')||'',service_time:fd.get('service_time')||'',
weekdays:{dienstag:{soup:fd.get('di_soup')||'',title:fd.get('di_title')||'',side:fd.get('di_side')||'',price:fd.get('di_price')||''},mittwoch:{soup:fd.get('mi_soup')||'',title:fd.get('mi_title')||'',side:fd.get('mi_side')||'',price:fd.get('mi_price')||''},donnerstag:{soup:fd.get('do_soup')||'',title:fd.get('do_title')||'',side:fd.get('do_side')||'',price:fd.get('do_price')||''},freitag:{menu_1:{soup:fd.get('fr1_soup')||'',title:fd.get('fr1_title')||'',side:fd.get('fr1_side')||'',price:fd.get('fr1_price')||''},menu_2:{enabled:fd.has('fr2_enabled'),soup:fd.get('fr2_soup')||'',title:fd.get('fr2_title')||'',side:fd.get('fr2_side')||'',price:fd.get('fr2_price')||''}}},
weekly_special:{enabled:fd.has('weekly_enabled'),title:fd.get('weekly_title')||'',side:fd.get('weekly_side')||'',price:fd.get('weekly_price')||''},
info_blocks:[1,2,3].map(i=>({enabled:fd.has('info'+i+'_enabled'),heading:fd.get('info'+i+'_heading')||'',text:fd.get('info'+i+'_text')||'',vertical_align:fd.get('info'+i+'_vertical')||'center'}))};}
async function refresh(){const r=await fetch('preview-menu.php',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dataFromForm())});const html=await r.text();await new Promise(resolve=>{let done=false;const finish=()=>{if(done)return;done=true;resolve();};frame.onload=finish;frame.srcdoc=html;setTimeout(finish,1400);});}
function scheduleRefresh(){clearTimeout(timer);timer=setTimeout(refresh,350)}
form.addEventListener('input',scheduleRefresh);form.addEventListener('change',scheduleRefresh);document.getElementById('refreshPreview').addEventListener('click',refresh);refresh();
form.addEventListener('submit',syncRichEditors);
document.getElementById('downloadPng').addEventListener('click', async ()=>{
  await refresh();
  await new Promise(resolve=>setTimeout(resolve,250));
  const doc=frame.contentDocument || frame.contentWindow.document;
  if(doc.fonts && doc.fonts.ready){await doc.fonts.ready;}
  await new Promise(resolve=>setTimeout(resolve,300));
  const page=doc.querySelector('.menu-page');
  if(!page){alert('Die Vorschau konnte nicht gelesen werden.');return;}
  const button=document.getElementById('downloadPng');
  const oldText=button.textContent;
  button.disabled=true;button.textContent='Grafik wird erstellt …';
  try{
    const canvas=await html2canvas(page,{scale:2,useCORS:true,allowTaint:false,backgroundColor:null,logging:false,width:page.scrollWidth,height:page.scrollHeight,windowWidth:page.scrollWidth,windowHeight:page.scrollHeight});
    const filename=((form.elements['file_name'].value||'auszeit-menue').trim().replace(/[^a-zA-Z0-9_-]+/g,'-')||'auszeit-menue')+'.png';
    const link=document.createElement('a');link.download=filename;link.href=canvas.toDataURL('image/png');document.body.appendChild(link);link.click();link.remove();
  }catch(error){console.error(error);alert('Die Grafik konnte nicht erstellt werden. Bitte Vorschau neu laden und nochmals versuchen.');}
  finally{button.disabled=false;button.textContent=oldText;}
});

document.getElementById('downloadFlyer').addEventListener('click', async ()=>{
  syncRichEditors();
  const flyerFrame=document.getElementById('flyerFrame');
  const button=document.getElementById('downloadFlyer');
  const oldText=button.textContent;
  button.disabled=true;button.textContent='Druckbogen wird erstellt …';
  try{
    const r=await fetch('preview-menu.php?mode=flyer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dataFromForm())});
    const html=await r.text();
    await new Promise(resolve=>{let done=false;const finish=()=>{if(done)return;done=true;resolve();};flyerFrame.onload=finish;flyerFrame.srcdoc=html;setTimeout(finish,1600);});
    const doc=flyerFrame.contentDocument||flyerFrame.contentWindow.document;
    if(doc.fonts&&doc.fonts.ready){await doc.fonts.ready;}
    await new Promise(resolve=>setTimeout(resolve,250));
    const sheet=doc.querySelector('.flyer-sheet');
    if(!sheet)throw new Error('Druckbogen nicht gefunden');
    const targetWidth=3508;
    const scale=targetWidth/sheet.getBoundingClientRect().width;
    const canvas=await html2canvas(sheet,{scale:scale,useCORS:true,allowTaint:false,backgroundColor:'#ffffff',logging:false,width:sheet.scrollWidth,height:sheet.scrollHeight,windowWidth:sheet.scrollWidth,windowHeight:sheet.scrollHeight});
    const base=((form.elements['file_name'].value||'auszeit-menue').trim().replace(/[^a-zA-Z0-9_-]+/g,'-')||'auszeit-menue');
    const link=document.createElement('a');link.download=base+'-druckbogen-2xA5.png';link.href=canvas.toDataURL('image/png');document.body.appendChild(link);link.click();link.remove();
  }catch(error){console.error(error);alert('Der Druckbogen konnte nicht erstellt werden. Bitte Vorschau neu laden und nochmals versuchen.');}
  finally{button.disabled=false;button.textContent=oldText;}
});
</script></body></html>
