<?php
declare(strict_types=1);

function event_h(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function event_format_date(string $date): string {
    if ($date === '') return '';
    $ts = strtotime($date);
    return $ts ? date('d.m.Y', $ts) : $date;
}

function event_render_preview(array $event): string {
    $title = event_h((string)($event['title'] ?? ''));
    $date = event_format_date((string)($event['date'] ?? ''));
    $time = event_h((string)($event['time'] ?? ''));
    $description = nl2br(event_h((string)($event['description'] ?? '')));
    $price = event_h((string)($event['price'] ?? ''));
    $reservation = event_h((string)($event['reservation'] ?? ''));
    $image = (string)($event['image'] ?? '');
    $imageUrl = $image !== '' ? event_h($image) : '';

    ob_start(); ?>
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}body{font-family:Georgia,'Times New Roman',serif;background:#5d0b11;color:#fff}.slide{position:relative;width:100%;height:100%;min-height:720px;background:radial-gradient(circle at 35% 20%,#8a2632 0,#5d0b11 48%,#35060b 100%);overflow:hidden}.goldline{position:absolute;left:4%;right:4%;top:5%;height:2px;background:#d4b05c}.logo{position:absolute;right:5%;top:6%;text-align:center;color:#efd77f;letter-spacing:.08em}.logo strong{font-size:clamp(24px,3vw,52px);line-height:.85;display:block}.logo small{font-family:Arial,sans-serif;font-size:clamp(7px,.7vw,13px)}.content{position:absolute;left:7%;top:16%;width:62%;z-index:3}.eyebrow{font-family:Arial,sans-serif;color:#efd77f;font-size:clamp(17px,1.8vw,30px);font-weight:bold;letter-spacing:.08em;text-transform:uppercase}.title{font-size:clamp(40px,5.6vw,90px);line-height:1.02;margin:1.5% 0 2%;text-shadow:0 3px 8px rgba(0,0,0,.3)}.when{font-family:Arial,sans-serif;font-size:clamp(22px,2.6vw,43px);font-weight:bold;color:#f3df9d;margin-bottom:4%}.description{font-size:clamp(20px,2.2vw,36px);line-height:1.28;max-width:950px}.meta{margin-top:4%;display:flex;gap:5%;flex-wrap:wrap;font-family:Arial,sans-serif}.meta div{border-left:5px solid #d4b05c;padding-left:16px;font-size:clamp(18px,1.8vw,30px)}.corner{position:absolute;right:-2%;bottom:-2%;width:43%;height:58%;object-fit:contain;object-position:right bottom;z-index:2}.fade{position:absolute;right:0;bottom:0;width:52%;height:66%;background:linear-gradient(90deg,#5d0b11 0,rgba(93,11,17,.78) 16%,rgba(93,11,17,0) 55%);z-index:2;pointer-events:none}.footer{position:absolute;left:7%;bottom:5%;font-family:Arial,sans-serif;color:#efd77f;font-size:clamp(13px,1.25vw,22px);font-weight:bold}.empty-image{position:absolute;right:7%;bottom:8%;width:28%;height:35%;border:2px dashed rgba(239,215,127,.45);display:grid;place-items:center;color:rgba(239,215,127,.75);font-family:Arial,sans-serif;text-align:center;padding:20px}
</style>
</head><body><main class="slide"><div class="goldline"></div><div class="logo"><strong>CAFE<br>AUSZEIT</strong><small>CAFE · EVENTBAR · RESTAURANT</small></div><section class="content"><div class="eyebrow">Veranstaltung im Auszeit</div><h1 class="title"><?= $title !== '' ? $title : 'Titel der Veranstaltung' ?></h1><div class="when"><?= event_h($date) ?><?= $date !== '' && $time !== '' ? ' · ' : '' ?><?= $time ?></div><div class="description"><?= $description !== '' ? $description : 'Beschreibung der Veranstaltung' ?></div><div class="meta"><?php if($price!==''):?><div><?= $price ?></div><?php endif;?><?php if($reservation!==''):?><div><?= $reservation ?></div><?php endif;?></div></section><?php if($imageUrl!==''):?><img class="corner" src="<?= $imageUrl ?>" alt="Eckmotiv"><div class="fade"></div><?php else:?><div class="empty-image">Hier erscheint das hochgeladene Eckmotiv</div><?php endif;?><div class="footer">Café Restaurant Auszeit · Waldgasse 10 · 2601 Sollenau – Maria Theresia</div></main></body></html>
<?php return (string)ob_get_clean();
}
