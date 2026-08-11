<?php
declare(strict_types=1);
header('Content-Type: text/html; charset=UTF-8');

require_once __DIR__ . '/includes/bootstrap.php';

require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/storage.php';

const EVENT_DIR = __DIR__ . '/data/termine';
const EVENT_FILE = EVENT_DIR . '/termine.json';
const TEMPLATE_FILE = EVENT_DIR . '/vorlagen.json';
const CURRENT_FILE = EVENT_DIR . '/aktuell.json';
const EVENT_INDEX_FILE = EVENT_DIR . '/index.json';
const EVENT_UPLOAD_DIR = __DIR__ . '/uploads/events';

function h(string $v): string { return htmlspecialchars($v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function clean($v): string { return trim((string)$v); }
function sanitize_rich_text(string $html): string {
    $html = trim($html);
    if ($html === '') return '';
    $html = preg_replace('~<(script|style|iframe|object|embed|svg|math)[^>]*>.*?</\\1>~is', '', $html) ?? '';
    $html = preg_replace('/<!--.*?-->/s', '', $html) ?? '';
    if (!class_exists('DOMDocument')) {
        return strip_tags($html, '<p><div><br><strong><b><em><i><u><span>');
    }
    $doc = new DOMDocument('1.0', 'UTF-8');
    libxml_use_internal_errors(true);
    $doc->loadHTML('<?xml encoding="UTF-8"><div id="rich-root">'.$html.'</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
    libxml_clear_errors();
    $allowedTags = ['div','p','br','strong','b','em','i','u','span'];
    $allowedClasses = ['ql-align-center','ql-align-right','ql-align-justify','ql-size-small','ql-size-large'];
    $walker = function(DOMNode $node) use (&$walker,$allowedTags,$allowedClasses): void {
        for($child=$node->firstChild;$child!==null;){
            $next=$child->nextSibling;
            if($child instanceof DOMElement){
                $tag=strtolower($child->tagName);
                if(!in_array($tag,$allowedTags,true)){
                    while($child->firstChild) $node->insertBefore($child->firstChild,$child);
                    $node->removeChild($child); $child=$next; continue;
                }
                $classes=array_values(array_intersect(preg_split('/\\s+/',trim((string)$child->getAttribute('class')))?:[],$allowedClasses));
                $safe=[];
                foreach(explode(';',(string)$child->getAttribute('style')) as $rule){
                    if(!str_contains($rule,':')) continue;
                    [$prop,$value]=array_map('trim',explode(':',$rule,2)); $prop=strtolower($prop);
                    if($prop==='text-align' && in_array(strtolower($value),['left','center','right','justify'],true)) $safe[]='text-align:'.strtolower($value);
                    elseif(in_array($prop,['color','background-color'],true) && preg_match('/^(#[0-9a-f]{3,8}|rgb\\([0-9, .%]+\\)|rgba\\([0-9, .%]+\\)|[a-z]{3,20})$/i',$value)) $safe[]=$prop.':'.$value;
                }
                while($child->attributes->length>0) $child->removeAttributeNode($child->attributes->item(0));
                if($classes) $child->setAttribute('class',implode(' ',$classes));
                if($safe) $child->setAttribute('style',implode(';',$safe));
                $walker($child);
            }
            $child=$next;
        }
    };
    $root=$doc->getElementById('rich-root'); if(!$root) return '';
    $walker($root); $out=''; foreach($root->childNodes as $child) $out.=$doc->saveHTML($child);
    return trim($out);
}
function ensure_event_dirs(): void {
    foreach ([EVENT_DIR, EVENT_UPLOAD_DIR.'/single', EVENT_UPLOAD_DIR.'/templates'] as $dir) {
        if (!is_dir($dir) && !mkdir($dir, 0775, true) && !is_dir($dir)) {
            throw new RuntimeException('Ordner konnte nicht erstellt werden: '.$dir);
        }
    }
}
function load_json_list(string $file): array {
    if (!is_file($file)) return [];
    $data = json_decode((string)file_get_contents($file), true);
    return is_array($data) ? array_values($data) : [];
}
function save_json(string $file, array $data): void {
    auszeit_write_json_atomic($file, $data);
}
function save_json_list(string $file, array $items): void { save_json($file, array_values($items)); }
function new_id(string $prefix): string { return $prefix.'-'.date('Ymd-His').'-'.bin2hex(random_bytes(3)); }
function upload_event_image(array $file, string $subdir, string $old=''): string {
    if (($file['error']??UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) return $old;
    if (($file['error']??UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) throw new RuntimeException('Bild-Upload fehlgeschlagen.');
    if ((int)($file['size']??0) > 20*1024*1024) throw new RuntimeException('Das Bild ist größer als 20 MB.');
    $tmp=(string)($file['tmp_name']??''); $info=@getimagesize($tmp);
    if ($info===false) throw new RuntimeException('Die Datei ist keine gültige Grafik.');
    $map=['image/png'=>'png','image/jpeg'=>'jpg','image/webp'=>'webp']; $mime=(string)($info['mime']??'');
    if (!isset($map[$mime])) throw new RuntimeException('Erlaubt sind PNG, JPG und WebP.');
    $name=new_id('event').'.'.$map[$mime]; $target=EVENT_UPLOAD_DIR.'/'.$subdir.'/'.$name;
    if (!move_uploaded_file($tmp,$target)) throw new RuntimeException('Das Bild konnte nicht gespeichert werden.');
    return 'uploads/events/'.$subdir.'/'.$name;
}
function find_by_id(array $items,string $id): ?array { foreach($items as $item) if(($item['id']??'')===$id) return $item; return null; }
function sort_events(array &$events): void { usort($events,fn($a,$b)=>strcmp(($a['date']??'').' '.($a['time']??''),($b['date']??'').' '.($b['time']??''))); }
function normalize_dates(array $dates): array {
    $out=[];
    foreach($dates as $date){
        $date=clean($date);
        if($date!=='' && preg_match('/^\d{4}-\d{2}-\d{2}$/',$date)) $out[$date]=$date;
    }
    ksort($out);
    return array_values($out);
}
function next_date(array $dates, ?string $today=null): string {
    $today=$today??date('Y-m-d');
    foreach(normalize_dates($dates) as $date){ if($date >= $today) return $date; }
    return '';
}
function format_date_de(string $d): string { $ts=strtotime($d); return $ts?date('d.m.Y',$ts):$d; }
function rebuild_current_file(array $events,array $templates): array {
    $today=date('Y-m-d'); $items=[];
    foreach($events as $event){
        if(!($event['active']??true)) continue;
        $date=clean($event['date']??'');
        if($date==='' || $date<$today) continue;
        $items[]=[
            'source'=>'single','id'=>(string)($event['id']??''),'date'=>$date,
            'time'=>(string)($event['time']??''),'title'=>(string)($event['title']??''),
            'description'=>(string)($event['description']??''),'price'=>(string)($event['price']??''),
            'reservation'=>(string)($event['reservation']??''),'image'=>(string)($event['image']??'')
        ];
    }
    foreach($templates as $template){
        if(!($template['active']??true)) continue;
        $date=next_date((array)($template['dates']??[]),$today);
        if($date==='') continue;
        $items[]=[
            'source'=>'template','template_id'=>(string)($template['id']??''),'date'=>$date,
            'time'=>(string)($template['time']??''),'title'=>(string)($template['title']??''),
            'description'=>(string)($template['description']??''),'price'=>(string)($template['price']??''),
            'reservation'=>(string)($template['reservation']??''),'image'=>(string)($template['image']??'')
        ];
    }
    usort($items,fn($a,$b)=>strcmp(($a['date']??'').' '.($a['time']??''),($b['date']??'').' '.($b['time']??'')));
    $payload=['generated_at'=>date(DATE_ATOM),'today'=>$today,'next_events'=>$items];
    save_json(CURRENT_FILE,$payload);
    return $payload;
}


function rebuild_event_index(array $current): array {
    $entries = [];
    foreach ((array)($current['next_events'] ?? []) as $item) {
        $date = clean($item['date'] ?? '');
        if ($date === '') continue;
        $entry = [
            'file' => 'aktuell.json',
            'source' => (string)($item['source'] ?? ''),
            'title' => (string)($item['title'] ?? ''),
            'valid_from' => $date,
            'valid_until' => $date,
        ];
        if (($item['source'] ?? '') === 'template') {
            $entry['template_id'] = (string)($item['template_id'] ?? '');
        } else {
            $entry['id'] = (string)($item['id'] ?? '');
        }
        if ((string)($item['time'] ?? '') !== '') $entry['time'] = (string)$item['time'];
        $entries[] = $entry;
    }
    $payload = [
        'generated_at' => date(DATE_ATOM),
        'events' => $entries,
    ];
    save_json(EVENT_INDEX_FILE, $payload);
    return $payload;
}

try {
    $appConfig = auszeit_load_config();
} catch (Throwable $configError) {
    http_response_code(503);
    exit('Webinterface nicht konfiguriert.');
}

if(!auszeit_is_authenticated()){
    $error='';
    $loginStatus=auszeit_login_status(auszeit_login_client_key(),$appConfig);
    if($_SERVER['REQUEST_METHOD']==='POST'&&isset($_POST['password'])){
        if($loginStatus['locked']){
            $error='Zu viele Fehlversuche. Die Anmeldung ist 15 Minuten gesperrt.';
        } elseif(auszeit_login((string)$_POST['password'],$appConfig)){header('Location: termine-admin.php');exit;
        } else {
            $loginStatus=auszeit_login_status(auszeit_login_client_key(),$appConfig);
            $error=$loginStatus['locked']
                ? '10 Fehlversuche erreicht. Die Anmeldung ist 15 Minuten gesperrt.'
                : 'Falsches Passwort. Verbleibende Versuche: '.$loginStatus['remaining_attempts'].'.';
        }
    }
    ?><!doctype html><html lang="de"><meta charset="utf-8"><title>Auszeit Terminverwaltung</title><style>body{font-family:Arial;background:#5d0b11;display:grid;place-items:center;min-height:100vh;margin:0}.box{background:#fff;padding:30px;border-radius:12px;width:360px}input,button{width:100%;padding:12px;margin-top:10px;box-sizing:border-box}</style><div class="box"><h1>Anmeldung</h1><?php if($error):?><p><?=h($error)?></p><?php endif;?><form method="post"><input type="password" name="password" autofocus required><button>Anmelden</button></form></div></html><?php exit;
}

ensure_event_dirs();
$events=load_json_list(EVENT_FILE); $templates=load_json_list(TEMPLATE_FILE); $message=''; $error='';
$mode=clean($_GET['mode']??$_POST['mode']??'event');
$editId=clean($_GET['edit']??$_POST['edit_id']??'');
$event=['id'=>'','date'=>'','time'=>'','title'=>'','description'=>'','price'=>'','reservation'=>'','image'=>'','active'=>true];
$template=['id'=>'','title'=>'','description'=>'','time'=>'','price'=>'','reservation'=>'','image'=>'','active'=>true,'dates'=>[]];
if($editId!==''){
    if($mode==='template') $template=find_by_id($templates,$editId)??$template;
    else $event=find_by_id($events,$editId)??$event;
}

if($_SERVER['REQUEST_METHOD']==='POST'){
    try{
        auszeit_verify_csrf();
        if(isset($_POST['logout'])){auszeit_logout();header('Location: termine-admin.php');exit;}
        elseif(isset($_POST['save_template'])){
            $id=clean($_POST['edit_id']??'')?:new_id('template');
            $old=find_by_id($templates,$id);
            $image=upload_event_image($_FILES['image']??[],'templates',(string)($old['image']??''));
            $datesRaw=$_POST['dates']??[];
            $dates=is_array($datesRaw)?normalize_dates($datesRaw):[];
            $newDate=clean($_POST['new_date']??'');
            if($newDate!=='') $dates=normalize_dates(array_merge($dates,[$newDate]));
            $item=['id'=>$id,'title'=>clean($_POST['title']??''),'description'=>sanitize_rich_text((string)($_POST['description']??'')),'time'=>clean($_POST['time']??''),'price'=>clean($_POST['price']??''),'reservation'=>clean($_POST['reservation']??''),'image'=>$image,'active'=>isset($_POST['active']),'dates'=>$dates];
            if($item['title']==='') throw new RuntimeException('Bitte einen Vorlagentitel eingeben.');
            $found=false; foreach($templates as $k=>$v){if(($v['id']??'')===$id){$templates[$k]=$item;$found=true;break;}} if(!$found)$templates[]=$item;
            save_json_list(TEMPLATE_FILE,$templates); $template=$item; $editId=$id; $mode='template'; $message='Vorlage und Terminliste gespeichert.';
        } elseif(isset($_POST['delete_template'])){
            $id=clean($_POST['edit_id']??'');
            $templates=array_values(array_filter($templates,fn($x)=>($x['id']??'')!==$id));
            save_json_list(TEMPLATE_FILE,$templates); $template=['id'=>'','title'=>'','description'=>'','time'=>'','price'=>'','reservation'=>'','image'=>'','active'=>true,'dates'=>[]]; $editId=''; $mode='template'; $message='Vorlage gelöscht.';
        } elseif(isset($_POST['save_event'])){
            $id=clean($_POST['edit_id']??'')?:new_id('event'); $old=find_by_id($events,$id);
            $image=upload_event_image($_FILES['image']??[],'single',(string)($old['image']??''));
            $item=['id'=>$id,'date'=>clean($_POST['date']??''),'time'=>clean($_POST['time']??''),'title'=>clean($_POST['title']??''),'description'=>sanitize_rich_text((string)($_POST['description']??'')),'price'=>clean($_POST['price']??''),'reservation'=>clean($_POST['reservation']??''),'image'=>$image,'active'=>isset($_POST['active'])];
            if($item['date']===''||$item['title']==='') throw new RuntimeException('Datum und Titel sind Pflichtfelder.');
            $found=false; foreach($events as $k=>$v){if(($v['id']??'')===$id){$events[$k]=$item;$found=true;break;}} if(!$found)$events[]=$item;
            sort_events($events); save_json_list(EVENT_FILE,$events); $event=$item; $editId=$id; $mode='event'; $message='Einzeltermin gespeichert.';
        } elseif(isset($_POST['delete_event'])){
            $id=clean($_POST['edit_id']??'');
            $events=array_values(array_filter($events,fn($x)=>($x['id']??'')!==$id));
            save_json_list(EVENT_FILE,$events); $event=['id'=>'','date'=>'','time'=>'','title'=>'','description'=>'','price'=>'','reservation'=>'','image'=>'','active'=>true]; $editId=''; $mode='event'; $message='Einzeltermin gelöscht.';
        }
    }catch(Throwable $e){$error=$e->getMessage();}
}
try{
    $current=rebuild_current_file($events,$templates);
    rebuild_event_index($current);
}catch(Throwable $e){
    $current=['next_events'=>[]];
    if($error==='')$error=$e->getMessage();
}
?>
<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auszeit Terminverwaltung</title>
<link href="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.snow.css" rel="stylesheet">
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#ebe6de;color:#2c211d}header{background:#5d0b11;color:#fff;padding:18px 24px;display:flex;justify-content:space-between;align-items:center;gap:20px}header h1{margin:0}header nav{display:flex;gap:18px;align-items:center;flex-wrap:wrap}header a{color:#fff;text-decoration:none;font-weight:bold}header a.active{color:#f1d37b;border-bottom:2px solid #f1d37b;padding-bottom:4px}.wrap{display:grid;grid-template-columns:minmax(600px,1fr) minmax(360px,.55fr);gap:18px;padding:18px;align-items:start}.panel{background:#fff;border:1px solid #d8cec2;border-radius:12px;padding:18px}.tabs{display:flex;gap:8px;margin-bottom:18px}.tabs a{padding:10px 16px;border-radius:7px;background:#7d746d;color:#fff;text-decoration:none;font-weight:bold}.tabs a.active{background:#71131d}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}.wide{grid-column:1/-1}label{display:block;font-size:12px;font-weight:bold;margin:0 0 4px}input,textarea,select,button{width:100%;padding:10px;border:1px solid #b9aea5;border-radius:6px;font:inherit}textarea{min-height:110px;resize:vertical}button{background:#71131d;color:#fff;border:0;font-weight:bold;cursor:pointer}.danger{background:#952331}.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.msg{padding:10px;border-radius:7px;margin-bottom:10px;background:#e0f0df}.err{background:#f4d8dc;color:#7d111b}.list{margin-top:20px}.row{display:grid;grid-template-columns:110px 80px 1fr auto;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #ded6cc}.row a{color:#71131d;font-weight:bold}.inactive{opacity:.5}.thumb{max-width:220px;max-height:150px;object-fit:contain;background:#eee;border:1px solid #ddd;margin-top:8px}.date-list{display:grid;gap:7px;margin-top:8px}.date-item{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;background:#f4f0eb;border:1px solid #ddd2c7;border-radius:7px;padding:7px 9px}.date-item.past{opacity:.55}.date-item input{width:auto;margin:0}.next-badge{display:inline-block;background:#e8d28d;color:#4d3310;padding:3px 7px;border-radius:999px;font-size:11px;font-weight:bold;margin-left:6px}.current-list{display:grid;gap:10px}.current-card{border-left:5px solid #b38a32;background:#f8f5ef;padding:12px 14px;border-radius:6px}.current-card .date{color:#71131d;font-weight:bold}.current-card .source{font-size:11px;text-transform:uppercase;color:#756a61;margin-top:4px}.editor-wrap{border:1px solid #b9aea5;border-radius:6px;overflow:hidden;background:#fff}.editor-wrap .ql-toolbar{border:0;border-bottom:1px solid #d9d0c8}.editor-wrap .ql-container{border:0;font-size:16px}.editor-wrap .ql-editor{min-height:130px}.new-series{display:inline-block;margin:0 0 16px;padding:10px 14px;border-radius:7px;background:#b38a32;color:#2c211d;text-decoration:none;font-weight:bold}.series-note{font-size:13px;color:#655b54;margin:-8px 0 14px}.json-note{font-size:13px;color:#655b54;background:#f4f0eb;padding:10px;border-radius:7px;margin-top:16px;word-break:break-word}@media(max-width:1050px){.wrap{grid-template-columns:1fr}}@media(max-width:700px){.grid2,.actions{grid-template-columns:1fr}.row{grid-template-columns:1fr}.wide{grid-column:auto}}
</style></head><body>
<header><h1>Auszeit Verwaltung</h1><nav><a href="menu_admin.php">Menüverwaltung</a><a class="active" href="termine-admin.php">Terminverwaltung</a><form method="post" style="margin:0"><?=auszeit_csrf_input()?><button name="logout" style="width:auto;padding:0;background:none">Abmelden</button></form></nav></header>
<div class="wrap"><section class="panel"><div class="tabs"><a class="<?=$mode==='event'?'active':''?>" href="?mode=event">Einzeltermine</a><a class="<?=$mode==='template'?'active':''?>" href="?mode=template">Regelmäßige Events</a></div>
<?php if($message):?><div class="msg"><?=h($message)?></div><?php endif;?><?php if($error):?><div class="msg err"><?=h($error)?></div><?php endif;?>
<?php if($mode==='template'): ?>
<a class="new-series" href="?mode=template">+ Neue regelmäßige Serie anlegen</a>
<p class="series-note">Jede Serie – etwa Bingo, Pubquiz oder Frühstücksbuffet – wird separat gespeichert und kann eine eigene Terminliste sowie ein eigenes Bild haben.</p>
<form method="post" enctype="multipart/form-data"><?=auszeit_csrf_input()?><input type="hidden" name="mode" value="template"><input type="hidden" name="edit_id" value="<?=h((string)$template['id'])?>"><div class="grid2">
<div class="wide"><label>Vorlagenname / Titel</label><input name="title" required value="<?=h((string)$template['title'])?>"></div>
<div><label>Standard-Uhrzeit</label><input type="time" name="time" value="<?=h((string)$template['time'])?>"></div><div><label>Preis / Eintritt</label><input name="price" value="<?=h((string)$template['price'])?>"></div>
<div class="wide"><label>Beschreibung</label><input type="hidden" name="description" id="template-description" value="<?=h((string)$template['description'])?>"><div class="editor-wrap"><div id="template-editor"><?=((string)$template['description'])?></div></div></div><div class="wide"><label>Reservierungshinweis</label><input name="reservation" value="<?=h((string)$template['reservation'])?>"></div>
<div class="wide"><label>Eckmotiv hochladen (PNG, JPG, WebP)</label><input type="file" name="image" accept="image/png,image/jpeg,image/webp"><?php if(($template['image']??'')!==''):?><img class="thumb" src="<?=h((string)$template['image'])?>" alt="Aktuelles Bild"><?php endif;?></div>
<div class="wide"><label>Kommende Termine</label><div class="date-list">
<?php $today=date('Y-m-d'); $next=next_date((array)($template['dates']??[]),$today); foreach(normalize_dates((array)($template['dates']??[])) as $date):?><label class="date-item <?=$date<$today?'past':''?>"><span><?=h(format_date_de($date))?><?php if($date===$next):?><span class="next-badge">nächster Termin</span><?php endif;?></span><span><input type="checkbox" name="dates[]" value="<?=h($date)?>" checked> behalten</span></label><?php endforeach;?>
<?php if(empty($template['dates'])):?><div>Noch keine Termine eingetragen.</div><?php endif;?></div></div>
<div class="wide"><label>Weiteres Datum hinzufügen</label><input type="date" name="new_date"><small>Zum Entfernen bei einem vorhandenen Datum „behalten“ abwählen und speichern.</small></div>
<div class="wide"><label><input style="width:auto" type="checkbox" name="active" <?=($template['active']??true)?'checked':''?>> Vorlage aktiv</label></div></div>
<div class="actions"><button name="save_template">Vorlage und Termine speichern</button><?php if(($template['id']??'')!==''):?><button class="danger" name="delete_template" onclick="return confirm('Vorlage wirklich löschen?')">Vorlage löschen</button><?php endif;?></div></form>
<div class="list"><h2>Vorhandene Vorlagen</h2><?php foreach($templates as $t): $n=next_date((array)($t['dates']??[]));?><div class="row <?=($t['active']??true)?'':'inactive'?>"><span><?=h($n!==''?format_date_de($n):'–')?></span><span><?=h((string)($t['time']??''))?></span><strong><?=h((string)($t['title']??''))?></strong><a href="?mode=template&edit=<?=urlencode((string)$t['id'])?>">Bearbeiten</a></div><?php endforeach;?></div>
<?php else: ?>
<form method="post" enctype="multipart/form-data"><?=auszeit_csrf_input()?><input type="hidden" name="mode" value="event"><input type="hidden" name="edit_id" value="<?=h((string)$event['id'])?>"><div class="grid2">
<div><label>Datum</label><input type="date" name="date" required value="<?=h((string)$event['date'])?>"></div><div><label>Uhrzeit</label><input type="time" name="time" value="<?=h((string)$event['time'])?>"></div>
<div class="wide"><label>Titel</label><input name="title" required value="<?=h((string)$event['title'])?>"></div><div class="wide"><label>Beschreibung</label><input type="hidden" name="description" id="event-description" value="<?=h((string)$event['description'])?>"><div class="editor-wrap"><div id="event-editor"><?=((string)$event['description'])?></div></div></div>
<div><label>Preis / Eintritt</label><input name="price" value="<?=h((string)$event['price'])?>"></div><div><label>Reservierungshinweis</label><input name="reservation" value="<?=h((string)$event['reservation'])?>"></div>
<div class="wide"><label>Eckmotiv hochladen (PNG, JPG, WebP)</label><input type="file" name="image" accept="image/png,image/jpeg,image/webp"><?php if(($event['image']??'')!==''):?><img class="thumb" src="<?=h((string)$event['image'])?>" alt="Aktuelles Bild"><?php endif;?></div>
<div class="wide"><label><input style="width:auto" type="checkbox" name="active" <?=($event['active']??true)?'checked':''?>> Termin aktiv</label></div></div>
<div class="actions"><button name="save_event">Einzeltermin speichern</button><?php if(($event['id']??'')!==''):?><button class="danger" name="delete_event" onclick="return confirm('Termin wirklich löschen?')">Termin löschen</button><?php endif;?></div></form>
<div class="list"><h2>Gespeicherte Einzeltermine</h2><?php foreach($events as $e):?><div class="row <?=($e['active']??true)?'':'inactive'?>"><span><?=h(format_date_de((string)($e['date']??'')))?></span><span><?=h((string)($e['time']??''))?></span><strong><?=h((string)($e['title']??''))?></strong><a href="?mode=event&edit=<?=urlencode((string)$e['id'])?>">Bearbeiten</a></div><?php endforeach;?></div>
<?php endif;?></section>
<aside class="panel"><h2>Automatisch ausgewählte Termine</h2><p>Diese Liste wird bei jedem Speichern neu erstellt. Für jedes regelmäßige Event wird nur das nächste noch nicht vergangene Datum übernommen.</p><div class="current-list">
<?php foreach(($current['next_events']??[]) as $item):?><div class="current-card"><div class="date"><?=h(format_date_de((string)$item['date']))?><?=($item['time']??'')!==''?' · '.h((string)$item['time']):''?></div><strong><?=h((string)$item['title'])?></strong><div class="source"><?=($item['source']??'')==='template'?'regelmäßiges Event':'Einzeltermin'?></div></div><?php endforeach;?>
<?php if(empty($current['next_events'])):?><div>Noch keine zukünftigen aktiven Termine vorhanden.</div><?php endif;?></div><div class="json-note"><strong>Dateien für die Foliengenerierung:</strong><br>data/termine/index.json<br>data/termine/aktuell.json</div></aside></div>
<script src="https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/quill.js"></script>
<script>
(function(){
    const toolbar = [
        ['bold','italic','underline'],
        [{size:['small',false,'large']}],
        [{align:[] }],
        [{color:[]},{background:[]}],
        ['clean']
    ];
    function init(editorId,inputId){
        const el=document.getElementById(editorId), input=document.getElementById(inputId);
        if(!el || !input || typeof Quill==='undefined') return;
        const q=new Quill(el,{theme:'snow',modules:{toolbar:toolbar}});
        const form=el.closest('form');
        if(form) form.addEventListener('submit',function(){
            input.value=typeof q.getSemanticHTML==='function' ? q.getSemanticHTML() : q.root.innerHTML;
        });
    }
    init('template-editor','template-description');
    init('event-editor','event-description');
})();
</script>
</body></html>
