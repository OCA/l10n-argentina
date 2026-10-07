* Campo 11 (Percepción a no categorizados) e Campo 13 (Percepções/pagos a
  conta de impostos nacionais) do layout ``REGDIGITAL_CV_CBTE`` (compras)
  saem sempre zerados (``TODO`` no código, não implementado).
* Campos 23, 24 e 25 (CUIT/Denominação/IVA do Corredor, aplicável só a
  comprovantes com tipo 033/058/059/060/063) não implementados.
* Prorrateio de Crédito Fiscal por comprovante não implementado: o caminho
  suportado é prorratear fora do Odoo (mensagem de orientação no erro).
* Nenhum dos desenhos de registro foi validado contra o validador oficial
  da ARCA.
