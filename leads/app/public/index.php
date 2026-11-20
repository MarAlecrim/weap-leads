<?php
declare(strict_types=1);
require __DIR__ . '/../src/app.php';

iniciar_sessao();
$pag = $_GET['p'] ?? 'busca';

// ---------- Login / sair ----------
if ($pag === 'sair') {
    $_SESSION = [];
    session_destroy();
    header('Location: ./');
    exit;
}
if (!usuario()) {
    $erro = '';
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        checa_csrf();
        if (login((string) ($_POST['usuario'] ?? ''), (string) ($_POST['senha'] ?? ''))) {
            header('Location: ./');
            exit;
        }
        $erro = 'Usuário ou senha incorretos.';
    }
    topo('Entrar');
    ?>
    <main class="login">
      <form method="post" class="cartao">
        <img src="logo.svg" alt="" class="logo-login" onerror="this.remove()">
        <h1>Weap Leads</h1>
        <?php if ($erro): ?><p class="erro"><?= h($erro) ?></p><?php endif ?>
        <label>Usuário<input name="usuario" autocomplete="username" required autofocus></label>
        <label>Senha<input name="senha" type="password" autocomplete="current-password" required></label>
        <input type="hidden" name="csrf" value="<?= h($_SESSION['csrf']) ?>">
        <button>Entrar</button>
      </form>
    </main>
    <?php
    rodape();
    exit;
}

// ---------- Planilha (CSV no mesmo formato da planilha do disparo) ----------
if ($pag === 'planilha' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    checa_csrf();
    parse_str((string) ($_POST['filtros'] ?? ''), $q);
    $f = filtros($q);
    $sel = array_filter((array) ($_POST['sel'] ?? []));
    if (($_POST['quais'] ?? '') === 'selecionados' && !$sel) {
        header('Location: ./?' . (string) ($_POST['filtros'] ?? '') . '&nada=1');
        exit;
    }
    $linhas = para_planilha($f, ($_POST['quais'] ?? '') === 'selecionados' ? $sel : []);
    if (!empty($_POST['pular_disparo'])) $linhas = array_filter($linhas, fn($r) => !$r['no_disparo']);
    $linhas = array_filter($linhas, fn($r) => whatsapp_do($r) !== '');

    $nome = 'leads-' . ($f['nicho'] ?: 'busca') . '-' . date('Y-m-d-Hi') . '.csv';
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $nome . '"');
    $out = fopen('php://output', 'w');
    fwrite($out, "\xEF\xBB\xBF"); // acentos certos no Excel e no Google Planilhas
    fputcsv($out, ['nome_empresa', 'telefone', 'endereco', 'website', 'rating', 'reviews', 'especialidades', 'mensagem', 'disparo', 'decisor', 'email', 'cnpj']);
    foreach ($linhas as $r) {
        fputcsv($out, [
            nome_bonito($r['nome']),
            '55' . whatsapp_do($r) . '@s.whatsapp.net',
            endereco($r),
            '', '', '',
            $r['atividade'],
            '', '',
            nome_bonito($r['decisor']),
            $r['email'],
            $r['cnpj'],
        ]);
    }
    fclose($out);
    exit;
}

// ---------- Ficha da empresa ----------
if ($pag === 'empresa') {
    $cnpj = strtoupper(preg_replace('/[^0-9A-Za-z]/', '', (string) ($_GET['cnpj'] ?? '')));
    $st = db()->prepare(SELECT_LEADS . ' WHERE e.cnpj = ?');
    $st->execute([$cnpj]);
    $r = $st->fetch();
    if (!$r) {
        http_response_code(404);
        topo('Não encontrada');
        echo '<main><p>Empresa não encontrada. <a href="./">Voltar</a></p></main>';
        rodape();
        exit;
    }
    $r = marca_no_disparo([$r])[0];
    $st = db()->prepare("SELECT s.nome, s.tipo, s.data_entrada, s.faixa_etaria, coalesce(q.descricao, s.qualificacao) AS qualificacao
                           FROM receita.socios s LEFT JOIN receita.qualificacoes q ON q.codigo = s.qualificacao
                          WHERE s.cnpj_basico = ? ORDER BY (s.qualificacao IN ('49','05','16')) DESC, s.data_entrada");
    $st->execute([$r['cnpj_basico']]);
    $socios = $st->fetchAll();
    $sec = db()->prepare("SELECT c.codigo, c.descricao FROM receita.estabelecimentos e, unnest(e.cnaes_secundarios) x(codigo)
                           JOIN receita.cnaes c ON c.codigo = x.codigo WHERE e.cnpj = ?");
    $sec->execute([$cnpj]);
    $secundarias = $sec->fetchAll();
    $faixas = ['1' => 'até 12 anos', '2' => '13 a 20', '3' => '21 a 30', '4' => '31 a 40', '5' => '41 a 50', '6' => '51 a 60', '7' => '61 a 70', '8' => '71 a 80', '9' => 'mais de 80'];
    $mapa = 'https://www.google.com/maps/search/?api=1&query=' . rawurlencode(nome_bonito($r['nome']) . ' ' . endereco($r));
    topo(nome_bonito($r['nome']));
    ?>
    <main>
      <p><a href="javascript:history.back()">&larr; Voltar para a busca</a></p>
      <div class="cartao ficha">
        <h1><?= h(nome_bonito($r['nome'])) ?> <?php if ($r['no_disparo']): ?><span class="selo">já no disparo</span><?php endif ?></h1>
        <p class="sub"><?= h($r['razao_social']) ?> · CNPJ <?= h(vsprintf('%s.%s.%s/%s-%s', [substr($cnpj, 0, 2), substr($cnpj, 2, 3), substr($cnpj, 5, 3), substr($cnpj, 8, 4), substr($cnpj, 12)])) ?></p>
        <dl>
          <dt>Atividade</dt><dd><?= h($r['atividade']) ?></dd>
          <?php if ($secundarias): ?><dt>Outras atividades</dt><dd><?= h(implode(' · ', array_column($secundarias, 'descricao'))) ?></dd><?php endif ?>
          <dt>Endereço</dt><dd><?= h(endereco($r)) ?> · <a href="<?= h($mapa) ?>" target="_blank" rel="noopener">ver no Google Maps</a></dd>
          <dt>Telefones</dt><dd>
            <?php foreach (['telefone1', 'telefone2'] as $c): if (!$r[$c]) continue; ?>
              <?= h(fone_bonito($r[$c])) ?>
              <?php if (celular($r[$c])): ?><a href="https://wa.me/55<?= h($r[$c]) ?>" target="_blank" rel="noopener">WhatsApp</a><?php else: ?><span class="fraco">(fixo)</span><?php endif ?><br>
            <?php endforeach ?>
          </dd>
          <?php if ($r['email']): ?><dt>E-mail</dt><dd><?= h($r['email']) ?></dd><?php endif ?>
          <dt>Aberta há</dt><dd><?= h(anos($r['data_abertura'])) ?> (<?= h($r['data_abertura'] ? date('d/m/Y', strtotime($r['data_abertura'])) : '') ?>)</dd>
          <dt>Porte</dt><dd><?= h(PORTES[$r['porte']] ?? '') ?></dd>
        </dl>
        <h2>Sócios</h2>
        <?php if (!$socios): ?><p class="fraco">A Receita não lista sócios para esta empresa (comum em MEI e empresário individual: o decisor é o próprio titular).</p><?php endif ?>
        <table>
          <?php foreach ($socios as $s): ?>
            <tr><td><strong><?= h(nome_bonito($s['nome'])) ?></strong></td><td><?= h($s['qualificacao']) ?></td>
                <td class="fraco"><?= $s['tipo'] === '1' ? 'empresa' : h($faixas[$s['faixa_etaria']] ?? '') ?></td>
                <td class="fraco"><?= $s['data_entrada'] ? 'desde ' . h(date('Y', strtotime($s['data_entrada']))) : '' ?></td>
                <td><a href="https://www.linkedin.com/search/results/people/?keywords=<?= h(rawurlencode(nome_bonito($s['nome']) . ' ' . nome_bonito($r['nome']))) ?>" target="_blank" rel="noopener">procurar no LinkedIn</a></td></tr>
          <?php endforeach ?>
        </table>
        <p class="fraco">Dados públicos da Receita Federal. O telefone pode estar desatualizado ou ser do contador.</p>
      </div>
    </main>
    <?php
    rodape();
    exit;
}

// ---------- Busca ----------
$f = filtros($_GET);
$buscou = isset($_GET['buscou']);
$pagina = max(1, (int) ($_GET['pg'] ?? 1));
$nichos = db()->query("SELECT nicho, string_agg(rotulo, ', ' ORDER BY rotulo) AS rotulos FROM receita.nicho_cnaes GROUP BY nicho ORDER BY nicho")->fetchAll();
$cidades = db()->query('SELECT municipio, nome, uf, empresas FROM receita.cidades ORDER BY uf, nome')->fetchAll();
$total = $buscou ? contar($f) : 0;
$linhas = $buscou ? buscar($f, $pagina) : [];
$qs = $_GET;
unset($qs['pg'], $qs['p']);
$filtros_qs = http_build_query($qs);
$base = db()->query("SELECT max(atualizado_em) FROM receita.estabelecimentos")->fetchColumn();

topo('Buscar leads');
?>
<main>
  <form method="get" class="cartao filtros">
    <input type="hidden" name="buscou" value="1">
    <label>Nicho
      <select name="nicho">
        <option value="">Todos</option>
        <?php foreach ($nichos as $n): ?>
          <option value="<?= h($n['nicho']) ?>" title="<?= h($n['rotulos']) ?>" <?= $f['nicho'] === $n['nicho'] ? 'selected' : '' ?>><?= h(nome_nicho($n['nicho'])) ?></option>
        <?php endforeach ?>
      </select>
    </label>
    <label>Cidade
      <select name="cidade">
        <option value="">Todas</option>
        <?php foreach ($cidades as $c): ?>
          <option value="<?= h($c['municipio']) ?>" <?= $f['cidade'] === $c['municipio'] ? 'selected' : '' ?>><?= h(nome_bonito($c['nome'])) ?> - <?= h($c['uf']) ?></option>
        <?php endforeach ?>
      </select>
    </label>
    <label>Bairro<input name="bairro" value="<?= h($f['bairro']) ?>" placeholder="ex.: Gleba Palhano"></label>
    <label>Nome da empresa<input name="nome" value="<?= h($f['nome']) ?>" placeholder="opcional"></label>
    <label>Tempo de empresa
      <span class="par"><input name="anos_min" type="number" min="0" value="<?= h((string) $f['anos_min']) ?>" placeholder="de"> a
      <input name="anos_max" type="number" min="0" value="<?= h((string) $f['anos_max']) ?>" placeholder="até"> anos</span>
    </label>
    <fieldset><legend>Porte</legend>
      <?php foreach (PORTES as $k => $v): ?>
        <label class="check"><input type="checkbox" name="porte[]" value="<?= $k ?>" <?= in_array($k, $f['porte'], true) ? 'checked' : '' ?>> <?= h($v) ?></label>
      <?php endforeach ?>
    </fieldset>
    <fieldset><legend>Só quem</legend>
      <label class="check"><input type="checkbox" name="celular" value="1" <?= $f['celular'] ? 'checked' : '' ?>> tem celular (WhatsApp)</label>
      <label class="check"><input type="checkbox" name="socio" value="1" <?= $f['socio'] ? 'checked' : '' ?>> tem sócio pessoa física</label>
      <label class="check"><input type="checkbox" name="email" value="1" <?= $f['email'] ? 'checked' : '' ?>> tem e-mail</label>
      <label class="check"><input type="checkbox" name="secundario" value="1" <?= $f['secundario'] ? 'checked' : '' ?>> incluir atividade secundária</label>
      <label class="check"><input type="checkbox" name="esconder" value="1" <?= $f['esconder'] ? 'checked' : '' ?>> esconder quem já está no disparo</label>
    </fieldset>
    <button>Buscar</button>
  </form>

  <?php if ($buscou): ?>
    <form method="post" action="?p=planilha" class="resultado">
      <input type="hidden" name="csrf" value="<?= h($_SESSION['csrf']) ?>">
      <input type="hidden" name="filtros" value="<?= h($filtros_qs) ?>">
      <div class="barra">
        <strong><?= number_format($total, 0, ',', '.') ?> empresas</strong>
        <span class="acoes">
          <label class="check"><input type="checkbox" name="pular_disparo" value="1" checked> pular quem já está no disparo</label>
          <button name="quais" value="selecionados">Baixar planilha dos marcados</button>
          <button name="quais" value="todos" class="sec">Baixar planilha de todos (até <?= number_format(LIMITE_PLANILHA, 0, ',', '.') ?>)</button>
        </span>
      </div>
      <?php if (isset($_GET['nada'])): ?><p class="erro">Marque pelo menos uma empresa, ou use "Baixar planilha de todos".</p><?php endif ?>
      <?php if (!$linhas): ?>
        <p class="cartao">Nada encontrado com esses filtros.</p>
      <?php else: ?>
        <div class="tabela">
        <table>
          <thead><tr><th><input type="checkbox" onclick="document.querySelectorAll('.sel').forEach(c => c.checked = this.checked)" aria-label="Marcar todos"></th>
            <th>Empresa</th><th>Decisor</th><th>WhatsApp</th><th>Bairro</th><th>Tempo</th></tr></thead>
          <tbody>
          <?php foreach ($linhas as $r): $wa = whatsapp_do($r); ?>
            <tr class="<?= $r['no_disparo'] ? 'apagado' : '' ?>">
              <td><input type="checkbox" class="sel" name="sel[]" value="<?= h($r['cnpj']) ?>" aria-label="Marcar"></td>
              <td><a href="?p=empresa&amp;cnpj=<?= h($r['cnpj']) ?>"><?= h(nome_bonito($r['nome'])) ?></a>
                  <?php if ($r['no_disparo']): ?><span class="selo">já no disparo</span><?php endif ?>
                  <div class="fraco"><?= h($r['atividade']) ?></div></td>
              <td><?= h(nome_bonito($r['decisor'])) ?></td>
              <td><?= $wa ? h(fone_bonito($wa)) : '<span class="fraco">só fixo</span>' ?></td>
              <td><?= h(nome_bonito($r['bairro'])) ?><div class="fraco"><?= h(nome_bonito($r['cidade'])) ?></div></td>
              <td><?= h(anos($r['data_abertura'])) ?></td>
            </tr>
          <?php endforeach ?>
          </tbody>
        </table>
        </div>
        <nav class="paginas">
          <?php if ($pagina > 1): ?><a href="?<?= h($filtros_qs) ?>&amp;pg=<?= $pagina - 1 ?>">&larr; Anterior</a><?php endif ?>
          <span>Página <?= $pagina ?> de <?= max(1, (int) ceil($total / POR_PAGINA)) ?></span>
          <?php if ($pagina * POR_PAGINA < $total): ?><a href="?<?= h($filtros_qs) ?>&amp;pg=<?= $pagina + 1 ?>">Próxima &rarr;</a><?php endif ?>
        </nav>
      <?php endif ?>
    </form>
  <?php else: ?>
    <p class="cartao fraco">Escolha o nicho e a cidade e clique em Buscar. Base da Receita de <?= h($base ? date('m/Y', strtotime($base)) : '—') ?><?= db_agente() ? '' : ' · banco do agente não conectado (não marca quem já está no disparo)' ?>.</p>
  <?php endif ?>
</main>
<?php
rodape();

// ---------- Layout ----------
function topo(string $titulo): void
{
    ?><!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title><?= h($titulo) ?> · Weap Leads</title>
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<?php if (usuario()): ?>
<header><a href="./" class="marca">Weap Leads</a><span><?= h(usuario()) ?> · <a href="?p=sair">sair</a></span></header>
<?php endif;
}

function rodape(): void
{
    echo "\n</body>\n</html>\n";
}
