/**
 * Arquivo .html autocontido do relatório executivo (RF-17, história 014): o conteúdo da folha (incluindo a versão
 * editada) com a marca e os estilos essenciais dentro do próprio arquivo, em cores claras fixas, sem depender do
 * aplicativo nem de internet. Os estilos usam só marcas HTML, porque as classes do aplicativo são geradas.
 */
const ESTILOS = `
*{box-sizing:border-box}
body{margin:0;padding:24px 12px;background:#eef3f6;color:#0e2433;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
article{max-width:860px;margin:0 auto;padding:32px;background:#fff;border-top:6px solid #0f4c75;border-radius:8px;display:grid;gap:20px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;color:#0f4c75}
[role=img]{display:inline-flex;align-items:center;gap:8px;font-size:24px;font-weight:300;white-space:nowrap}
[role=img] svg{width:44px;height:44px;flex:none}
h2{margin:0;font-size:1.5rem}
h3{margin:0 0 8px;font-size:1.0625rem;color:#0f4c75}
p{margin:0 0 8px}
ul{margin:0;padding-left:20px}
table{width:100%;border-collapse:collapse}
th,td{padding:8px;border-bottom:1px solid #cfdbe3;text-align:left;vertical-align:top}
thead th{font-size:.875rem;color:#41596a}
dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0}
dd{margin:0;font-weight:700}
small{display:block;color:#41596a}
.so-leitor{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media print{body{background:#fff;padding:0}article{box-shadow:none}}
`;

const escapar = (t: string) =>
  t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function documentoHtml(numero: string, conteudoDaFolha: string): string {
  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapar(`Relatório executivo ${numero} — ClimaSense`)}</title>
<style>${ESTILOS}</style>
</head>
<body>
<article aria-label="Relatório executivo — Secretaria de Saúde">
${conteudoDaFolha}
</article>
</body>
</html>
`;
}
