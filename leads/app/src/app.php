<?php
// Weap Leads: funções comuns (conexão, login, busca)
declare(strict_types=1);

const POR_PAGINA = 50;
const LIMITE_PLANILHA = 3000;

function env(string $k, string $padrao = ''): string
{
    $v = getenv($k);
    return ($v === false || $v === '') ? $padrao : $v;
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO(
            sprintf('pgsql:host=%s;port=%s;dbname=%s', env('DB_HOST', 'db'), env('DB_PORT', '5432'), env('DB_NAME', 'leads')),
            env('DB_USER', 'leads'),
            env('DB_PASSWORD'),
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, PDO::ATTR_EMULATE_PREPARES => true]
        );
    }
    return $pdo;
}

// Banco do agente (weap_sdr, no servidor do n8n). Opcional: sem ele, só não marca "já no disparo".
function db_agente(): ?PDO
{
    static $pdo = false;
    if ($pdo === false) {
        $pdo = null;
        if (env('AGENTE_DB_HOST') !== '') {
            try {
                $pdo = new PDO(
                    sprintf('pgsql:host=%s;port=%s;dbname=%s;connect_timeout=3', env('AGENTE_DB_HOST'), env('AGENTE_DB_PORT', '5432'), env('AGENTE_DB_NAME', 'weap_sdr')),
                    env('AGENTE_DB_USER'),
                    env('AGENTE_DB_PASSWORD'),
                    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, PDO::ATTR_EMULATE_PREPARES => true]
                );
            } catch (Throwable $e) {
                error_log('Banco do agente indisponível: ' . $e->getMessage());
            }
        }
    }
    return $pdo;
}

function h(?string $s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8');
}

function iniciar_sessao(): void
{
    session_set_cookie_params(['httponly' => true, 'secure' => env('APP_HTTPS', '1') === '1', 'samesite' => 'Lax']);
    session_name('weapleads');
    session_start();
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    }
}

function usuario(): ?string
{
    return $_SESSION['usuario'] ?? null;
}

function checa_csrf(): void
{
    if (!hash_equals($_SESSION['csrf'] ?? '', (string) ($_POST['csrf'] ?? ''))) {
        http_response_code(400);
        exit('Sessão expirada. Volte e tente de novo.');
    }
}

function login(string $u, string $s): bool
{
    $st = db()->prepare('SELECT senha_hash FROM public.app_usuarios WHERE usuario = ?');
    $st->execute([mb_strtolower(trim($u))]);
    $hash = $st->fetchColumn();
    if ($hash && password_verify($s, $hash)) {
        session_regenerate_id(true);
        $_SESSION['usuario'] = mb_strtolower(trim($u));
        return true;
    }
    usleep(800000); // freia tentativa de adivinhar senha
    return false;
}

// Mesma regra do sdr_chave() do agente: 55 + DDD + 8 últimos dígitos
function chave(?string $t): ?string
{
    $x = preg_replace('/\D/', '', (string) $t);
    $d = (strlen($x) >= 12 && str_starts_with($x, '55')) ? substr($x, 2) : ltrim($x, '0');
    return strlen($d) < 10 ? null : '55' . substr($d, 0, 2) . substr($d, -8);
}

function celular(?string $t): bool
{
    return (bool) preg_match('/^[1-9][0-9]9[0-9]{8}$/', (string) $t);
}

function fone_bonito(?string $t): string
{
    $t = (string) $t;
    if (strlen($t) === 11) return sprintf('(%s) %s-%s', substr($t, 0, 2), substr($t, 2, 5), substr($t, 7));
    if (strlen($t) === 10) return sprintf('(%s) %s-%s', substr($t, 0, 2), substr($t, 2, 4), substr($t, 6));
    return $t;
}

function whatsapp_do(array $r): string
{
    foreach (['telefone1', 'telefone2'] as $c) {
        if (celular($r[$c] ?? '')) return $r[$c];
    }
    return '';
}

const PORTES = ['01' => 'Microempresa', '03' => 'Pequeno porte', '05' => 'Demais', '00' => 'Não informado'];

function filtros(array $q): array
{
    return [
        'nicho'      => trim((string) ($q['nicho'] ?? '')),
        'secundario' => !empty($q['secundario']),
        'cidade'     => trim((string) ($q['cidade'] ?? '')),
        'bairro'     => trim((string) ($q['bairro'] ?? '')),
        'nome'       => trim((string) ($q['nome'] ?? '')),
        'porte'      => array_values(array_intersect(array_keys(PORTES), (array) ($q['porte'] ?? []))),
        'anos_min'   => ($q['anos_min'] ?? '') === '' ? null : max(0, (int) $q['anos_min']),
        'anos_max'   => ($q['anos_max'] ?? '') === '' ? null : max(0, (int) $q['anos_max']),
        'celular'    => !isset($q['buscou']) || !empty($q['celular']),   // padrão: ligado
        'email'      => !empty($q['email']),
        'socio'      => !empty($q['socio']),
        'esconder'   => !empty($q['esconder']),
    ];
}

// Monta o WHERE da busca. Devolve [sql, parametros].
function where(array $f): array
{
    $w = [];
    $p = [];
    if ($f['nicho'] !== '') {
        $st = db()->prepare('SELECT cnae FROM receita.nicho_cnaes WHERE nicho = ?');
        $st->execute([$f['nicho']]);
        $p['cnaes'] = '{' . implode(',', $st->fetchAll(PDO::FETCH_COLUMN) ?: ['0']) . '}';
        $w[] = $f['secundario']
            ? '(e.cnae_principal = ANY(CAST(:cnaes AS text[])) OR e.cnaes_secundarios && CAST(:cnaes AS text[]))'
            : 'e.cnae_principal = ANY(CAST(:cnaes AS text[]))';
    }
    if ($f['cidade'] !== '') {
        $w[] = 'e.municipio = :cidade';
        $p['cidade'] = $f['cidade'];
    }
    if ($f['bairro'] !== '') {
        $w[] = 'unaccent(e.bairro) ILIKE unaccent(:bairro)';
        $p['bairro'] = '%' . $f['bairro'] . '%';
    }
    if ($f['nome'] !== '') {
        $w[] = '(unaccent(e.nome_fantasia) ILIKE unaccent(:nome) OR unaccent(emp.razao_social) ILIKE unaccent(:nome))';
        $p['nome'] = '%' . $f['nome'] . '%';
    }
    if ($f['porte']) {
        $in = [];
        foreach ($f['porte'] as $i => $v) {
            $in[] = ":porte$i";
            $p["porte$i"] = $v;
        }
        $w[] = 'emp.porte IN (' . implode(',', $in) . ')';
    }
    if ($f['anos_min'] !== null) {
        $w[] = "e.data_abertura <= current_date - make_interval(years => :amin)";
        $p['amin'] = $f['anos_min'];
    }
    if ($f['anos_max'] !== null) {
        $w[] = "e.data_abertura >= current_date - make_interval(years => :amax)";
        $p['amax'] = $f['anos_max'];
    }
    if ($f['celular']) $w[] = '(receita.celular(e.telefone1) OR receita.celular(e.telefone2))';
    if ($f['email']) $w[] = "e.email LIKE '%@%'";
    if ($f['socio']) $w[] = "EXISTS (SELECT 1 FROM receita.socios s WHERE s.cnpj_basico = e.cnpj_basico AND s.tipo = '2')";
    return [$w ? 'WHERE ' . implode(' AND ', $w) : '', $p];
}

const SELECT_LEADS = "
  SELECT e.cnpj, e.cnpj_basico,
         coalesce(nullif(e.nome_fantasia, ''), emp.razao_social) AS nome,
         emp.razao_social, emp.porte, e.data_abertura, e.cnae_principal,
         c.descricao AS atividade, e.logradouro, e.numero, e.complemento, e.bairro, e.cep,
         cid.nome AS cidade, e.uf, e.telefone1, e.telefone2, e.email,
         (SELECT s.nome FROM receita.socios s
           WHERE s.cnpj_basico = e.cnpj_basico AND s.tipo = '2'
           ORDER BY (s.qualificacao IN ('49','05','16')) DESC, s.data_entrada LIMIT 1) AS decisor
    FROM receita.estabelecimentos e
    JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
    LEFT JOIN receita.cnaes c ON c.codigo = e.cnae_principal
    LEFT JOIN receita.cidades cid ON cid.municipio = e.municipio";

function buscar(array $f, int $pagina): array
{
    [$w, $p] = where($f);
    $st = db()->prepare(SELECT_LEADS . " $w ORDER BY e.data_abertura DESC NULLS LAST, e.cnpj LIMIT " . POR_PAGINA . ' OFFSET ' . (($pagina - 1) * POR_PAGINA));
    $st->execute($p);
    $linhas = marca_no_disparo($st->fetchAll());
    if ($f['esconder']) $linhas = array_values(array_filter($linhas, fn($r) => !$r['no_disparo']));
    return $linhas;
}

function contar(array $f): int
{
    [$w, $p] = where($f);
    $st = db()->prepare("SELECT count(*) FROM receita.estabelecimentos e JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico $w");
    $st->execute($p);
    return (int) $st->fetchColumn();
}

function para_planilha(array $f, array $cnpjs = []): array
{
    [$w, $p] = where($f);
    if ($cnpjs) {
        $in = [];
        foreach (array_values($cnpjs) as $i => $c) {
            $in[] = ":c$i";
            $p["c$i"] = strtoupper(preg_replace('/[^0-9A-Za-z]/', '', $c));
        }
        $w = ($w ? "$w AND " : 'WHERE ') . 'e.cnpj IN (' . implode(',', $in) . ')';
    }
    $st = db()->prepare(SELECT_LEADS . " $w ORDER BY e.data_abertura DESC NULLS LAST LIMIT " . LIMITE_PLANILHA);
    $st->execute($p);
    return marca_no_disparo($st->fetchAll());
}

// Marca quem já está no banco do agente (pela chave do telefone)
function marca_no_disparo(array $linhas): array
{
    $chaves = [];
    foreach ($linhas as $r) {
        foreach (['telefone1', 'telefone2'] as $c) {
            if ($k = chave($r[$c])) $chaves[$k] = true;
        }
    }
    $existe = [];
    $ag = db_agente();
    if ($ag && $chaves) {
        $st = $ag->prepare('SELECT chave FROM sdr_leads WHERE chave = ANY(?::text[])');
        $st->execute(['{' . implode(',', array_keys($chaves)) . '}']);
        $existe = array_flip($st->fetchAll(PDO::FETCH_COLUMN));
    }
    foreach ($linhas as &$r) {
        $r['no_disparo'] = isset($existe[chave($r['telefone1']) ?? '-']) || isset($existe[chave($r['telefone2']) ?? '-']);
    }
    return $linhas;
}

function endereco(array $r): string
{
    $rua = trim(nome_bonito($r['logradouro']) . ($r['numero'] ? ', ' . $r['numero'] : ''));
    $cep = $r['cep'] ? substr($r['cep'], 0, 5) . '-' . substr($r['cep'], 5) : '';
    return trim(implode(' - ', array_filter([$rua, nome_bonito($r['bairro']), nome_bonito($r['cidade']) . ' - ' . $r['uf']])) . ($cep ? ", $cep" : ''));
}

function anos(?string $data): string
{
    if (!$data) return '';
    $a = (new DateTime($data))->diff(new DateTime('today'))->y;
    return $a < 1 ? 'menos de 1 ano' : ($a === 1 ? '1 ano' : "$a anos");
}

const NICHOS_NOME = ['saude' => 'Saúde', 'construcao' => 'Construção', 'estetica' => 'Estética', 'imobiliaria' => 'Imobiliária',
    'veterinaria' => 'Veterinária', 'nutricao' => 'Nutrição', 'farmacia' => 'Farmácia', 'otica' => 'Ótica',
    'salao de beleza' => 'Salão de beleza', 'materiais de construcao' => 'Materiais de construção', 'moveis planejados' => 'Móveis planejados'];

function nome_nicho(string $n): string
{
    return NICHOS_NOME[$n] ?? mb_strtoupper(mb_substr($n, 0, 1)) . mb_substr($n, 1);
}

function nome_bonito(?string $s): string
{
    $s = mb_convert_case(mb_strtolower((string) $s), MB_CASE_TITLE, 'UTF-8');
    return preg_replace_callback('/\b(Da|De|Do|Das|Dos|E|Ltda|Me|Epp|S\/A|Sa)\b/u', fn($m) => in_array($m[1], ['Ltda', 'Me', 'Epp', 'S/A', 'Sa']) ? mb_strtoupper($m[1]) : mb_strtolower($m[1]), $s);
}
