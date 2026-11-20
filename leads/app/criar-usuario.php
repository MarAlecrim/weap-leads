<?php
// Uso: docker compose exec app php /app/criar-usuario.php nome senha
// Rodar de novo com o mesmo nome troca a senha.
declare(strict_types=1);
require __DIR__ . '/src/app.php';
[$_, $u, $s] = $argv + [null, '', ''];
if ($u === '' || strlen($s) < 8) {
    fwrite(STDERR, "Uso: php criar-usuario.php nome senha (senha com 8 caracteres ou mais)\n");
    exit(1);
}
db()->prepare('INSERT INTO public.app_usuarios (usuario, senha_hash) VALUES (?, ?)
               ON CONFLICT (usuario) DO UPDATE SET senha_hash = EXCLUDED.senha_hash')
    ->execute([mb_strtolower(trim($u)), password_hash($s, PASSWORD_DEFAULT)]);
echo "Usuário $u pronto.\n";
