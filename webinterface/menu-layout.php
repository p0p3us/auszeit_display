<?php
declare(strict_types=1);

function menu_h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function menu_asset_data_uri(string $path): string
{
    if (!is_file($path)) {
        return '';
    }
    $mime = function_exists('mime_content_type') ? (mime_content_type($path) ?: 'image/jpeg') : 'image/jpeg';
    $data = file_get_contents($path);
    return $data === false ? '' : 'data:' . $mime . ';base64,' . base64_encode($data);
}



function menu_vertical_align($value): string
{
    $value = strtolower(trim((string)$value));
    return in_array($value, ['top', 'center', 'bottom'], true) ? $value : 'center';
}

function menu_sanitize_rich_text(string $html): string
{
    $html = trim($html);
    if ($html === '') {
        return '';
    }

    // Entfernt Skripte, eingebettete Medien und Kommentare vor der eigentlichen Bereinigung.
    $html = preg_replace('~<(script|style|iframe|object|embed|svg|math)[^>]*>.*?</\1>~is', '', $html) ?? '';
    $html = preg_replace('/<!--.*?-->/s', '', $html) ?? '';

    if (!class_exists('DOMDocument')) {
        return strip_tags($html, '<p><div><br><strong><b><em><i><u><span>');
    }

    $doc = new DOMDocument('1.0', 'UTF-8');
    libxml_use_internal_errors(true);
    $doc->loadHTML('<?xml encoding="UTF-8"><div id="rich-root">' . $html . '</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
    libxml_clear_errors();

    $allowedTags = ['div', 'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'span'];
    $allowedAlignClasses = ['ql-align-center', 'ql-align-right', 'ql-align-justify', 'ql-size-small', 'ql-size-large'];

    $walker = function (DOMNode $node) use (&$walker, $allowedTags, $allowedAlignClasses): void {
        for ($child = $node->firstChild; $child !== null;) {
            $next = $child->nextSibling;
            if ($child instanceof DOMElement) {
                $tag = strtolower($child->tagName);
                if (!in_array($tag, $allowedTags, true)) {
                    while ($child->firstChild) {
                        $node->insertBefore($child->firstChild, $child);
                    }
                    $node->removeChild($child);
                    $child = $next;
                    continue;
                }

                $class = trim((string)$child->getAttribute('class'));
                $classes = array_values(array_intersect(preg_split('/\s+/', $class) ?: [], $allowedAlignClasses));
                $style = (string)$child->getAttribute('style');
                $safeStyles = [];
                foreach (explode(';', $style) as $rule) {
                    if (!str_contains($rule, ':')) continue;
                    [$property, $value] = array_map('trim', explode(':', $rule, 2));
                    $property = strtolower($property);
                    if ($property === 'text-align' && in_array(strtolower($value), ['left','center','right','justify'], true)) {
                        $safeStyles[] = 'text-align:' . strtolower($value);
                    } elseif (in_array($property, ['color','background-color'], true) && preg_match('/^(#[0-9a-f]{3,8}|rgb\([0-9, .%]+\)|rgba\([0-9, .%]+\)|[a-z]{3,20})$/i', $value)) {
                        $safeStyles[] = $property . ':' . $value;
                    }
                }

                while ($child->attributes->length > 0) {
                    $child->removeAttributeNode($child->attributes->item(0));
                }
                if ($classes) $child->setAttribute('class', implode(' ', $classes));
                if ($safeStyles) $child->setAttribute('style', implode(';', $safeStyles));
                $walker($child);
            }
            $child = $next;
        }
    };

    $root = $doc->getElementById('rich-root');
    if (!$root) return '';
    $walker($root);
    $result = '';
    foreach ($root->childNodes as $child) {
        $result .= $doc->saveHTML($child);
    }
    return trim($result);
}

function menu_format_date(string $value, bool $short = false): string
{
    if ($value === '') {
        return '';
    }
    $ts = strtotime($value);
    if ($ts === false) {
        return $value;
    }
    return date($short ? 'd.m.' : 'd.m.Y', $ts);
}

function menu_has_content(array $item, array $keys): bool
{
    foreach ($keys as $key) {
        if (trim((string)($item[$key] ?? '')) !== '') {
            return true;
        }
    }
    return false;
}


function menu_optional_enabled(array $item, array $contentKeys): bool
{
    if (array_key_exists('enabled', $item)) {
        return (bool)$item['enabled'];
    }
    return menu_has_content($item, $contentKeys);
}

function menu_build_rows(array $data): array
{
    $rows = [];
    $days = [
        'dienstag' => 'Dienstag',
        'mittwoch' => 'Mittwoch',
        'donnerstag' => 'Donnerstag',
    ];

    foreach ($days as $key => $label) {
        $m = $data['weekdays'][$key] ?? [];
        $rows[] = [
            'type' => 'menu',
            'label' => $label,
            'soup' => (string)($m['soup'] ?? 'Tagessuppe'),
            'title' => (string)($m['title'] ?? ''),
            'side' => (string)($m['side'] ?? ''),
            'price' => (string)($m['price'] ?? ''),
        ];
    }

    $friday1 = $data['weekdays']['freitag']['menu_1'] ?? [];
    $rows[] = [
        'type' => 'menu',
        'label' => 'Freitag',
        'soup' => (string)($friday1['soup'] ?? 'Tagessuppe'),
        'title' => (string)($friday1['title'] ?? ''),
        'side' => (string)($friday1['side'] ?? ''),
        'price' => (string)($friday1['price'] ?? ''),
    ];

    $friday2 = $data['weekdays']['freitag']['menu_2'] ?? [];
    if (menu_optional_enabled($friday2, ['soup', 'title', 'side', 'price'])) {
        $rows[] = [
            'type' => 'menu',
            'label' => 'Freitag - Menü 2',
            'soup' => (string)($friday2['soup'] ?? ''),
            'title' => (string)($friday2['title'] ?? ''),
            'side' => (string)($friday2['side'] ?? ''),
            'price' => (string)($friday2['price'] ?? ''),
        ];
    }

    $sat = $data['saturday_special'] ?? [];
    if (menu_optional_enabled($sat, ['date', 'soup', 'title', 'side_1', 'side_2', 'price'])) {
        $date = menu_format_date((string)($sat['date'] ?? ''));
        $rows[] = [
            'type' => 'menu',
            'label' => 'Samstag-Schmankerl' . ($date !== '' ? '<br><span class="row-date">' . menu_h($date) . '</span>' : ''),
            'soup' => (string)($sat['soup'] ?? ''),
            'title' => (string)($sat['title'] ?? ''),
            'side' => trim((string)($sat['side_1'] ?? '') . ((string)($sat['side_2'] ?? '') !== '' ? ' · ' . (string)$sat['side_2'] : '')),
            'price' => (string)($sat['price'] ?? ''),
            'label_html' => true,
        ];
    }

    foreach (($data['info_blocks'] ?? []) as $block) {
        if (!menu_optional_enabled((array)$block, ['text'])) {
            continue;
        }
        $rows[] = [
            'type' => 'info',
            'heading' => (string)($block['heading'] ?? ''),
            'text' => menu_sanitize_rich_text((string)($block['text'] ?? '')),
            'vertical_align' => menu_vertical_align($block['vertical_align'] ?? 'center'),
        ];
    }

    return $rows;
}

function render_menu_document(array $data, bool $fullDocument = true, bool $pdfMode = false): string
{
    $rows = menu_build_rows($data);
    $count = max(1, count($rows));

    // Der Inhaltsbereich ist auf A4 millimetergenau festgelegt. Die Tafeln werden
    // absolut positioniert; ihr Inhalt darf ihre feste Höhe nicht mehr vergrößern.
    $contentHeight = 221.0;
    $contentPaddingTop = 3.2;
    $contentPaddingBottom = 3.2;
    $contentInnerHeight = $contentHeight - $contentPaddingTop - $contentPaddingBottom;
    $rowGap = $count >= 9 ? 1.15 : ($count >= 8 ? 1.35 : ($count >= 7 ? 1.55 : 1.85));
    $rowHeight = ($contentInnerHeight - (($count - 1) * $rowGap)) / $count;
    $rowHeight = max(17.2, $rowHeight);
    $densityClass = $count >= 9 ? ' density-9' : ($count >= 8 ? ' density-8' : ($count >= 7 ? ' density-7' : ''));
    $leather = menu_asset_data_uri(__DIR__ . '/assets/leather.jpg');
    $backgroundCandidates = [
        __DIR__ . '/assets/menu-background.png',
        __DIR__ . '/assets/menu-background.jpg',
        __DIR__ . '/assets/menu-background.jpeg',
        __DIR__ . '/assets/menu-background.webp',
        __DIR__ . '/assets/gold.jpg',
    ];
    $backgroundPath = __DIR__ . '/assets/gold.jpg';
    foreach ($backgroundCandidates as $candidate) {
        if (is_file($candidate)) {
            $backgroundPath = $candidate;
            break;
        }
    }
    $gold = menu_asset_data_uri($backgroundPath);

    $from = menu_format_date((string)($data['valid_from'] ?? ''), true);
    $to = menu_format_date((string)($data['valid_to'] ?? ''));
    $range = trim($from . ($from !== '' && $to !== '' ? ' - ' : '') . $to);
    $time = trim((string)($data['service_time'] ?? '11:00 - 14:00'));

    ob_start();
    if ($fullDocument):
?>
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php endif; ?>
<style>
@page { size: A4 portrait; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #363636; }
.menu-page {
    position: relative;
    width: 210mm;
    height: 297mm;
    margin: 0 auto;
    padding: 3.2mm;
    overflow: hidden;
    page-break-after: avoid;
    page-break-inside: avoid;
    background: #4b090d;
    font-family: Georgia, "Times New Roman", serif;
    color: #17100b;
}
.menu-frame {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    border: 0.55mm solid #d8af45;
    background: #5d0b11;
    box-shadow: inset 0 0 0 0.35mm #351006;
}
.header-band, .footer-band {
    background-image: linear-gradient(rgba(82,4,10,.18), rgba(25,0,3,.3)), url('<?= menu_h($leather) ?>');
    background-size: cover;
    color: #f0cf69;
}
.header-band {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 35mm;
    border-bottom: 0.65mm double #d6a940;
    display: table;
    width: 100%;
}
.header-logo, .header-title { display: table-cell; vertical-align: middle; }
.header-logo { width: 39mm; padding-left: 5mm; }
.brand-main {
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 700;
    font-size: 19pt;
    letter-spacing: 1.2pt;
    line-height: .92;
    text-align: center;
    text-shadow: 0 1px 0 #5a2805;
}
.brand-sub { margin-top: 2mm; font-size: 5.8pt; letter-spacing: .5pt; text-align: center; }
.header-title { text-align: center; padding-right: 8mm; }
.header-title h1 {
    margin: 0 0 2.2mm;
    font-size: 21pt;
    letter-spacing: 2pt;
    line-height: 1.05;
    color: #f4d36f;
    text-shadow: 0 1px 0 #542600;
}
.header-meta { font-size: 12pt; font-weight: 700; letter-spacing: 2pt; }
.content-area {
    position: absolute;
    left: 0;
    right: 0;
    top: 35mm;
    bottom: 33mm;
    padding: 3.2mm 3mm;
    overflow: hidden;
    background: #6a0c12;
}
/* Eine einzige Goldstoff-Ebene für den gesamten nutzbaren Inhaltsbereich. */
.gold-layer {
    position: absolute;
    left: 3mm;
    right: 3mm;
    top: 3.2mm;
    height: <?= number_format($contentInnerHeight, 2, '.', '') ?>mm;
    background-image: linear-gradient(rgba(255,250,229,.70), rgba(231,201,129,.42)), url('<?= menu_h($gold) ?>');
    background-size: 100% 100%;
    background-position: center center;
    background-repeat: no-repeat;
    z-index: 1;
}
.menu-card {
    position: absolute;
    left: 3mm;
    right: 3mm;
    height: <?= number_format($rowHeight, 2, '.', '') ?>mm;
    max-height: <?= number_format($rowHeight, 2, '.', '') ?>mm;
    overflow: hidden;
    border: 0.42mm solid #a87718;
    background: rgba(255, 248, 220, .16);
    box-shadow: inset 0 0 0 0.35mm rgba(255,247,204,.88), inset 0 0 2.4mm rgba(114,66,7,.14);
    padding: 1.7mm 3.3mm;
    vertical-align: middle;
    z-index: 3;
}
.separator {
    position: absolute;
    left: 0;
    right: 0;
    height: <?= number_format($rowGap, 2, '.', '') ?>mm;
    background: #6a0c12;
    z-index: 2;
}
.menu-row-table { width: 100%; height: 100%; border-collapse: collapse; table-layout: fixed; }
.day-cell {
    width: 31mm;
    padding-right: 4mm;
    border-right: 0.25mm solid rgba(111,65,8,.65);
    font-size: 13.2pt;
    font-style: italic;
    font-weight: 700;
    vertical-align: top;
}
.dish-cell { padding-left: 4.5mm; vertical-align: middle; }
.price-cell { width: 26mm; text-align: right; vertical-align: top; font-size: 16pt; font-weight: 700; white-space: nowrap; }
.soup { font-size: 11.8pt; font-style: italic; font-weight: 700; line-height: 1.0; }
.dish-title { font-size: 17pt; font-style: italic; font-weight: 700; line-height: 1.05; margin: .7mm 0; }
.side { font-size: 11.7pt; font-style: italic; line-height: 1.12; }
.row-date { font-size: 9pt; font-style: normal; }
.info-card { text-align: left; padding-left: 7mm; padding-right: 7mm; display:flex; flex-direction:column; }
.info-card.vertical-top { justify-content:flex-start; }
.info-card.vertical-center { justify-content:center; }
.info-card.vertical-bottom { justify-content:flex-end; }
.info-card > div { overflow: hidden; flex:0 0 auto; }
.info-heading { font-size: 13.7pt; font-weight: 700; font-style: italic; margin-bottom: 1.2mm; }
.info-text { font-size: 11.8pt; font-style: italic; line-height: 1.18; }
.rich-text p,.rich-text div{margin:0 0 .7mm}.rich-text p:last-child,.rich-text div:last-child{margin-bottom:0}.ql-align-center{text-align:center}.ql-align-right{text-align:right}.ql-align-justify{text-align:justify}.ql-size-small{font-size:.78em}.ql-size-large{font-size:1.28em}

.content-area.density-7 .menu-card { padding-top: 1.35mm; padding-bottom: 1.35mm; }
.content-area.density-8 .menu-card,
.content-area.density-9 .menu-card { padding-top: .95mm; padding-bottom: .95mm; }
.content-area.density-8 .day-cell,
.content-area.density-9 .day-cell { font-size: 11.6pt; }
.content-area.density-8 .dish-title { font-size: 15.2pt; }
.content-area.density-9 .dish-title { font-size: 14.2pt; }
.content-area.density-8 .soup,
.content-area.density-8 .side,
.content-area.density-8 .info-text { font-size: 10.6pt; }
.content-area.density-9 .soup,
.content-area.density-9 .side,
.content-area.density-9 .info-text { font-size: 9.9pt; }
.content-area.density-8 .info-heading { font-size: 12.5pt; margin-bottom: .7mm; }
.content-area.density-9 .info-heading { font-size: 11.7pt; margin-bottom: .5mm; }
.content-area.density-8 .price-cell { font-size: 14.6pt; }
.content-area.density-9 .price-cell { font-size: 13.6pt; }
.footer-band {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 33mm;
    border-top: 0.65mm double #d6a940;
    display: table;
    width: 100%;
    padding: 3.2mm 4.5mm;
}
.footer-left, .footer-center, .footer-logo { display: table-cell; vertical-align: middle; }
.footer-left { width: 43%; font-size: 8.8pt; font-weight: 700; letter-spacing: .55pt; line-height: 1.35; }
.footer-center { width: 34%; text-align: center; font-size: 9.2pt; font-weight: 700; letter-spacing: .55pt; line-height: 1.45; }
.footer-logo { width: 23%; }
.footer-logo .brand-main { font-size: 15pt; }
.footer-logo .brand-sub { font-size: 4.7pt; }
.menu-page.pdf-mode { margin: 0; }
.menu-page.pdf-mode .menu-frame { height: 289.8mm; }
@media screen {
    body { padding: 12px; }
    .menu-page { box-shadow: 0 0 18px rgba(0,0,0,.55); transform-origin: top center; }
}
</style>
<?php if ($fullDocument): ?></head><body><?php endif; ?>
<div class="menu-page<?= $pdfMode ? ' pdf-mode' : '' ?>">
  <div class="menu-frame">
    <div class="header-band">
      <div class="header-logo">
        <div class="brand-main">CAFE<br>AUSZEIT</div>
        <div class="brand-sub">CAFE · EVENTBAR · RESTAURANT</div>
      </div>
      <div class="header-title">
        <h1>Mittagsmenü mit Tagessuppe</h1>
        <div class="header-meta"><?= menu_h($range) ?><?= $range !== '' && $time !== '' ? ' | ' : '' ?><?= menu_h($time) ?></div>
      </div>
    </div>

    <div class="content-area<?= $densityClass ?>">
      <div class="gold-layer"></div>
      <?php foreach ($rows as $rowIndex => $row):
        $cardTop = $contentPaddingTop + ($rowIndex * ($rowHeight + $rowGap));
      ?>
        <div class="menu-card <?= $row['type'] === 'info' ? 'info-card vertical-' . menu_vertical_align($row['vertical_align'] ?? 'center') : '' ?>" style="top:<?= number_format($cardTop, 2, '.', '') ?>mm">
          <?php if ($row['type'] === 'menu'): ?>
            <table class="menu-row-table"><tr>
              <td class="day-cell"><?= !empty($row['label_html']) ? $row['label'] : menu_h((string)$row['label']) ?></td>
              <td class="dish-cell">
                <?php if (trim((string)$row['soup']) !== ''): ?><div class="soup"><?= menu_h((string)$row['soup']) ?></div><?php endif; ?>
                <div class="dish-title"><?= menu_h((string)$row['title']) ?></div>
                <?php if (trim((string)$row['side']) !== ''): ?><div class="side"><?= menu_h((string)$row['side']) ?></div><?php endif; ?>
              </td>
              <td class="price-cell"><?= menu_h((string)$row['price']) ?></td>
            </tr></table>
          <?php else: ?>
            <div class="info-heading"><?= menu_h((string)$row['heading']) ?></div>
            <div class="info-text rich-text"><?= (string)$row['text'] ?></div>
          <?php endif; ?>
        </div>
        <?php if ($rowIndex < $count - 1):
          $separatorTop = $cardTop + $rowHeight;
        ?>
          <div class="separator" style="top:<?= number_format($separatorTop, 2, '.', '') ?>mm"></div>
        <?php endif; ?>
      <?php endforeach; ?>
    </div>

    <div class="footer-band">
      <div class="footer-left">
        Café Restaurant Auszeit<br>
        Waldgasse 10<br>
        2601 Sollenau - Maria Theresia
      </div>
      <div class="footer-center">
        02628 / 62763<br>
        cafe-auszeit@gmx.at<br>
        auszeit-eggendorf.at
      </div>
      <div class="footer-logo">
        <div class="brand-main">CAFE<br>AUSZEIT</div>
        <div class="brand-sub">CAFE · EVENTBAR · RESTAURANT</div>
      </div>
    </div>
  </div>
</div>
<?php if ($fullDocument): ?></body></html><?php endif;
    return (string)ob_get_clean();
}


/**
 * Tintensparende Druckausgabe: A4 quer mit zwei identischen A5-Menüblättern.
 * Die Fläche bleibt überwiegend weiß; Farbe wird nur für Linien, Überschriften
 * und kleine Akzente verwendet.
 */
function render_menu_flyer_sheet(array $data, bool $fullDocument = true): string
{
    $rows = menu_build_rows($data);
    $count = max(1, count($rows));
    $from = menu_format_date((string)($data['valid_from'] ?? ''), true);
    $to = menu_format_date((string)($data['valid_to'] ?? ''));
    $range = trim($from . ($from !== '' && $to !== '' ? ' - ' : '') . $to);
    $time = trim((string)($data['service_time'] ?? '11:00 - 14:00'));
    $compact = $count >= 9 ? ' flyer-density-9' : ($count >= 8 ? ' flyer-density-8' : ($count >= 7 ? ' flyer-density-7' : ''));

    ob_start();
    if ($fullDocument):
?>
<!doctype html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<?php endif; ?>
<style>
@page{size:A4 landscape;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#d8d8d8}
.flyer-sheet{position:relative;width:297mm;height:210mm;margin:0 auto;background:#fff;display:flex;overflow:hidden;font-family:Georgia,"Times New Roman",serif;color:#1d1d1d}
.flyer-copy{position:relative;width:148.5mm;height:210mm;padding:7mm 7.5mm 6mm;background:#fff;overflow:hidden;display:flex;flex-direction:column}
.flyer-copy:first-child{padding-right:8.5mm}.flyer-copy:last-child{padding-left:8.5mm}
.flyer-topline{height:1.1mm;background:#7a1020;margin-bottom:3.2mm}
.flyer-header{display:grid;grid-template-columns:31mm 1fr;gap:4mm;align-items:center;border-bottom:.45mm solid #b38a32;padding:0 0 3.2mm;margin-bottom:2.5mm}
.flyer-brand{color:#7a1020;text-align:center;font-weight:700;line-height:.9;font-size:16pt;letter-spacing:.7pt}.flyer-brand small{display:block;margin-top:2mm;font:700 4.5pt Arial,sans-serif;letter-spacing:.35pt;color:#8b6c2d}
.flyer-title{text-align:center}.flyer-title h1{margin:0 0 1.3mm;color:#7a1020;font-size:17pt;line-height:1.02}.flyer-meta{font:700 8.4pt Arial,sans-serif;color:#4d0b13;letter-spacing:.45pt}
.flyer-rows{display:grid;gap:0;flex:1;min-height:0}
.flyer-row{position:relative;min-height:0;height:100%;padding:2.1mm 1.4mm 2mm 3.2mm;border-bottom:.28mm solid #d8d3ca;display:grid;grid-template-columns:24mm 1fr 18mm;gap:2.6mm;align-items:start;background:#fff}
.flyer-row.menu-row:before,.flyer-row.info-row:before{content:"";position:absolute;left:0;top:2.1mm;bottom:2.1mm;width:1.2mm;background:#7a1020}
.flyer-day{color:#7a1020;font-size:10.4pt;font-weight:700;font-style:italic;line-height:1.05}.flyer-date{font-size:7.3pt;font-style:normal}
.flyer-dish{min-width:0}.flyer-soup{font-size:7.8pt;font-style:italic;color:#5e5148;line-height:1}.flyer-dish-title{font-size:11.7pt;font-weight:700;font-style:italic;color:#1d1d1d;line-height:1.03;margin:.45mm 0}.flyer-side{font-size:8.2pt;font-style:italic;line-height:1.08;color:#342e2b}.flyer-price{text-align:right;color:#4d0b13;font-size:10.8pt;font-weight:700;white-space:nowrap}
.flyer-row.info-row{display:flex;min-height:0;height:100%;padding-left:4.8mm;border:.25mm solid #d8d3ca;border-left:0;margin-top:0;background:#fbf8f0;flex-direction:column;overflow:hidden;align-items:stretch}
.flyer-row.info-row.vertical-top{justify-content:flex-start}.flyer-row.info-row.vertical-center{justify-content:center}.flyer-row.info-row.vertical-bottom{justify-content:flex-end}
.flyer-info-heading{width:100%;color:#7a1020;font-size:10.3pt;font-weight:700;font-style:italic;margin-bottom:.7mm}.flyer-info-text{width:100%;font-size:8.4pt;line-height:1.12;color:#25211f;overflow:hidden}.flyer-info-text p,.flyer-info-text div{width:100%;margin:0 0 .45mm}.flyer-info-text p:last-child,.flyer-info-text div:last-child{margin-bottom:0}.ql-align-center{text-align:center}.ql-align-right{text-align:right}.ql-align-justify{text-align:justify}.ql-size-small{font-size:.8em}.ql-size-large{font-size:1.25em}
.flyer-footer{position:static;margin-top:2.2mm;border-top:.42mm solid #b38a32;padding-top:2.2mm;display:grid;grid-template-columns:1.1fr .9fr;gap:3mm;font:700 6.6pt Arial,sans-serif;color:#5c151d;line-height:1.35}.flyer-footer .right{text-align:right}.flyer-footer strong{font-size:7.5pt}
.flyer-density-7 .flyer-row{min-height:0;height:100%;padding-top:1.7mm;padding-bottom:1.6mm}.flyer-density-7 .flyer-dish-title{font-size:10.9pt}.flyer-density-7 .flyer-side,.flyer-density-7 .flyer-info-text{font-size:7.8pt}
.flyer-density-8 .flyer-row,.flyer-density-9 .flyer-row{min-height:0;height:100%;padding-top:1.35mm;padding-bottom:1.25mm}.flyer-density-8 .flyer-dish-title{font-size:10.2pt}.flyer-density-9 .flyer-dish-title{font-size:9.6pt}.flyer-density-8 .flyer-day,.flyer-density-9 .flyer-day{font-size:9.3pt}.flyer-density-8 .flyer-side,.flyer-density-8 .flyer-info-text{font-size:7.3pt}.flyer-density-9 .flyer-side,.flyer-density-9 .flyer-info-text{font-size:6.9pt}.flyer-density-8 .flyer-row.info-row,.flyer-density-9 .flyer-row.info-row{min-height:0;height:100%;margin-top:0}.flyer-density-8 .flyer-info-heading,.flyer-density-9 .flyer-info-heading{font-size:9.2pt;margin-bottom:.3mm}
@media screen{body{padding:10px}.flyer-sheet{box-shadow:0 0 18px rgba(0,0,0,.35)}}
</style>
<?php if ($fullDocument): ?></head><body><?php endif; ?>
<div class="flyer-sheet">
<?php for ($copy = 0; $copy < 2; $copy++): ?>
<section class="flyer-copy<?= $compact ?>">
  <div class="flyer-topline"></div>
  <header class="flyer-header">
    <div class="flyer-brand">CAFE<br>AUSZEIT<small>CAFE · EVENTBAR · RESTAURANT</small></div>
    <div class="flyer-title"><h1>Mittagsmenü mit Tagessuppe</h1><div class="flyer-meta"><?= menu_h($range) ?><?= $range !== '' && $time !== '' ? ' | ' : '' ?><?= menu_h($time) ?></div></div>
  </header>
  <div class="flyer-rows" style="grid-template-rows:repeat(<?= $count ?>,minmax(0,1fr))">
  <?php foreach ($rows as $row): ?>
    <?php if ($row['type'] === 'menu'): ?>
    <div class="flyer-row menu-row">
      <div class="flyer-day"><?= !empty($row['label_html']) ? $row['label'] : menu_h((string)$row['label']) ?></div>
      <div class="flyer-dish"><?php if (trim((string)$row['soup']) !== ''): ?><div class="flyer-soup"><?= menu_h((string)$row['soup']) ?></div><?php endif; ?><div class="flyer-dish-title"><?= menu_h((string)$row['title']) ?></div><?php if (trim((string)$row['side']) !== ''): ?><div class="flyer-side"><?= menu_h((string)$row['side']) ?></div><?php endif; ?></div>
      <div class="flyer-price"><?= menu_h((string)$row['price']) ?></div>
    </div>
    <?php else: ?>
    <div class="flyer-row info-row vertical-<?= menu_vertical_align($row['vertical_align'] ?? 'center') ?>">
      <div class="flyer-info-heading"><?= menu_h((string)$row['heading']) ?></div>
      <div class="flyer-info-text rich-text"><?= (string)$row['text'] ?></div>
    </div>
    <?php endif; ?>
  <?php endforeach; ?>
  </div>
  <footer class="flyer-footer"><div><strong>Café Restaurant Auszeit</strong><br>Waldgasse 10 · 2601 Sollenau - Maria Theresia</div><div class="right">02628 / 62763<br>cafe-auszeit@gmx.at<br>auszeit-eggendorf.at</div></footer>
</section>
<?php endfor; ?>
</div>
<?php if ($fullDocument): ?></body></html><?php endif; ?>
<?php
    return (string)ob_get_clean();
}


/**
 * Dompdf-sicheres Layout. Absichtlich ohne absolute Positionierung des
 * Seitencontainers: Dompdf verschob die bisherige 297-mm-Fläche auf Seite 2.
 */
function render_menu_pdf_document(array $data): string
{
    $rows = menu_build_rows($data);
    $count = max(1, count($rows));
    $leatherPath = realpath(__DIR__ . '/assets/leather.jpg') ?: (__DIR__ . '/assets/leather.jpg');
    $leather = 'file://' . str_replace(DIRECTORY_SEPARATOR, '/', $leatherPath);
    $backgroundCandidates = [
        __DIR__ . '/assets/menu-background.png',
        __DIR__ . '/assets/menu-background.jpg',
        __DIR__ . '/assets/menu-background.jpeg',
        __DIR__ . '/assets/menu-background.webp',
        __DIR__ . '/assets/gold.jpg',
    ];
    $backgroundPath = __DIR__ . '/assets/gold.jpg';
    foreach ($backgroundCandidates as $candidate) {
        if (is_file($candidate)) { $backgroundPath = $candidate; break; }
    }
    $backgroundReal = realpath($backgroundPath) ?: $backgroundPath;
    $gold = 'file://' . str_replace(DIRECTORY_SEPARATOR, '/', $backgroundReal);
    $from = menu_format_date((string)($data['valid_from'] ?? ''), true);
    $to = menu_format_date((string)($data['valid_to'] ?? ''));
    $range = trim($from . ($from !== '' && $to !== '' ? ' - ' : '') . $to);
    $time = trim((string)($data['service_time'] ?? '11:00 - 14:00'));

    // Innerer A4-Bereich nach 3-mm-Seitenrand: 291 mm. Mit etwas Reserve.
    $headerH = 34.0;
    $footerH = 31.0;
    $contentH = 224.5;
    $gap = $count >= 9 ? 1.0 : ($count >= 8 ? 1.2 : 1.45);
    $rowH = ($contentH - 5.0 - (($count - 1) * $gap)) / $count;
    $rowH = max(17.0, $rowH);
    $fontScale = $count >= 9 ? 0.78 : ($count >= 8 ? 0.84 : ($count >= 7 ? 0.91 : 1.0));

    ob_start();
?>
<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><style>
@page{size:A4 portrait;margin:3mm}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#4b090d;font-family:"DejaVu Serif",serif;color:#17100b}
.pdf-page{width:204mm;height:290mm;border:.55mm solid #d8af45;background:#5d0b11;border-collapse:collapse;table-layout:fixed;page-break-inside:avoid}
.pdf-page td{padding:0}
.pdf-header{height:<?=number_format($headerH,2,'.','')?>mm;background-image:linear-gradient(rgba(82,4,10,.18),rgba(25,0,3,.3)),url('<?=menu_h($leather)?>');background-size:cover;color:#f0cf69;border-bottom:.65mm double #d6a940}
.pdf-header-table,.pdf-footer-table,.pdf-menu-table{width:100%;height:100%;border-collapse:collapse;table-layout:fixed}
.pdf-logo{width:39mm;text-align:center;vertical-align:middle}.pdf-brand{font-size:18pt;font-weight:bold;line-height:.92;letter-spacing:1pt}.pdf-brand-sub{font-size:5.2pt;margin-top:2mm;letter-spacing:.4pt}
.pdf-title{text-align:center;vertical-align:middle;padding-right:7mm}.pdf-title h1{margin:0 0 2mm;font-size:20pt;letter-spacing:1.5pt;color:#f4d36f}.pdf-meta{font-size:11pt;font-weight:bold;letter-spacing:1.5pt}
.pdf-content{height:<?=number_format($contentH,2,'.','')?>mm;padding:2.5mm 3mm;background-image:linear-gradient(rgba(255,250,229,.70),rgba(231,201,129,.42)),url('<?=menu_h($gold)?>');background-size:100% 100%;background-repeat:no-repeat;vertical-align:top}
.pdf-rows{width:100%;height:100%;border-collapse:separate;border-spacing:0 <?=number_format($gap,2,'.','')?>mm;table-layout:fixed}
.pdf-row{height:<?=number_format($rowH,2,'.','')?>mm;background:rgba(255,248,220,.18);border:.42mm solid #a87718;outline:.25mm solid rgba(255,247,204,.8)}
.pdf-row>td{padding:1.2mm 3mm;overflow:hidden;vertical-align:middle;border-top:.35mm solid #a87718;border-bottom:.35mm solid #a87718}
.pdf-row>td:first-child{border-left:.35mm solid #a87718}.pdf-row>td:last-child{border-right:.35mm solid #a87718}
.pdf-day{width:31mm;padding-right:3mm!important;border-right:.25mm solid rgba(111,65,8,.65)!important;font-size:<?=number_format(13.2*$fontScale,1,'.','')?>pt;font-style:italic;font-weight:bold;vertical-align:top!important}
.pdf-dish{padding-left:4mm!important}.pdf-price{width:25mm;text-align:right;vertical-align:top!important;font-size:<?=number_format(16*$fontScale,1,'.','')?>pt;font-weight:bold;white-space:nowrap}
.pdf-soup{font-size:<?=number_format(11.8*$fontScale,1,'.','')?>pt;font-style:italic;font-weight:bold;line-height:1}.pdf-dish-title{font-size:<?=number_format(17*$fontScale,1,'.','')?>pt;font-style:italic;font-weight:bold;line-height:1.03;margin:.5mm 0}.pdf-side{font-size:<?=number_format(11.7*$fontScale,1,'.','')?>pt;font-style:italic;line-height:1.08}.pdf-date{font-size:8.5pt;font-style:normal}
.pdf-info{padding-left:7mm!important;padding-right:7mm!important;vertical-align:middle!important}.pdf-info-heading{font-size:<?=number_format(13.7*$fontScale,1,'.','')?>pt;font-weight:bold;font-style:italic;margin-bottom:.8mm}.rich-text p,.rich-text div{margin:0 0 .55mm}.rich-text p:last-child,.rich-text div:last-child{margin-bottom:0}.ql-align-center{text-align:center}.ql-align-right{text-align:right}.ql-align-justify{text-align:justify}
.pdf-info-text{font-size:<?=number_format(11.5*$fontScale,1,'.','')?>pt;font-style:italic;line-height:1.12}
.pdf-footer{height:<?=number_format($footerH,2,'.','')?>mm;background-image:linear-gradient(rgba(82,4,10,.18),rgba(25,0,3,.3)),url('<?=menu_h($leather)?>');background-size:cover;color:#f0cf69;border-top:.65mm double #d6a940}
.pdf-footer-left{width:43%;padding-left:4mm!important;font-size:8.2pt;font-weight:bold;line-height:1.32;vertical-align:middle}.pdf-footer-center{width:34%;text-align:center;font-size:8.6pt;font-weight:bold;line-height:1.4;vertical-align:middle}.pdf-footer-logo{width:23%;text-align:center;vertical-align:middle}.pdf-footer-logo .pdf-brand{font-size:14pt}.pdf-footer-logo .pdf-brand-sub{font-size:4.3pt}
</style></head><body>
<table class="pdf-page">
<tr><td class="pdf-header"><table class="pdf-header-table"><tr><td class="pdf-logo"><div class="pdf-brand">CAFE<br>AUSZEIT</div><div class="pdf-brand-sub">CAFE · EVENTBAR · RESTAURANT</div></td><td class="pdf-title"><h1>Mittagsmenü mit Tagessuppe</h1><div class="pdf-meta"><?=menu_h($range)?><?=$range!==''&&$time!==''?' | ':''?><?=menu_h($time)?></div></td></tr></table></td></tr>
<tr><td class="pdf-content"><table class="pdf-rows">
<?php foreach($rows as $row): ?>
<tr class="pdf-row">
<?php if($row['type']==='menu'): ?>
<td class="pdf-day"><?=!empty($row['label_html'])?$row['label']:menu_h((string)$row['label'])?></td>
<td class="pdf-dish"><?php if(trim((string)$row['soup'])!==''):?><div class="pdf-soup"><?=menu_h((string)$row['soup'])?></div><?php endif;?><div class="pdf-dish-title"><?=menu_h((string)$row['title'])?></div><?php if(trim((string)$row['side'])!==''):?><div class="pdf-side"><?=menu_h((string)$row['side'])?></div><?php endif;?></td>
<td class="pdf-price"><?=menu_h((string)$row['price'])?></td>
<?php else: ?><td class="pdf-info" colspan="3"><div class="pdf-info-heading"><?=menu_h((string)$row['heading'])?></div><div class="pdf-info-text rich-text"><?=(string)$row['text']?></div></td><?php endif; ?>
</tr>
<?php endforeach; ?>
</table></td></tr>
<tr><td class="pdf-footer"><table class="pdf-footer-table"><tr><td class="pdf-footer-left">Café Restaurant Auszeit<br>Waldgasse 10<br>2601 Sollenau - Maria Theresia</td><td class="pdf-footer-center">02628 / 62763<br>cafe-auszeit@gmx.at<br>auszeit-eggendorf.at</td><td class="pdf-footer-logo"><div class="pdf-brand">CAFE<br>AUSZEIT</div><div class="pdf-brand-sub">CAFE · EVENTBAR · RESTAURANT</div></td></tr></table></td></tr>
</table></body></html>
<?php
    return (string)ob_get_clean();
}
