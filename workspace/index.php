<?php
function adminer_object() {
    class AdminerDev extends \Adminer\Adminer {
        function login($login, $password) { return true; }
    }
    return new AdminerDev;
}
include "./adminer-core.php";
