<?php
// Install outside the web root. Store SHA-256 hashes, never device tokens here.
return [
    'storage_dir' => '/ABSOLUTE/PRIVATE/PATH/auszeit-status',
    'devices' => [
        'DEVICE_ID_FROM_PLAYER_CONFIG' => 'REPLACE_WITH_SHA256_OF_DEVICE_TOKEN',
    ],
];
