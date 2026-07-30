* Implementar otros campos fiscales del padrón.
* ``update_from_padron`` busca vários registros por ``name``, que é campo
  traduzível: o tipo de identificação (``"CUIT"``), a responsabilidade frente
  ao IVA (mapa ``RESP_IVA_MAPPING``), o país (``"Argentina"``) e a província.
  Numa base em espanhol esses ``search`` não encontram o registro esperado.
  O correto é usar ``l10n_ar_afip_code`` (tipo de identificação), ``code``
  (responsabilidade) e ``env.ref("base.ar")`` (país). Mantido como está nesta
  migração para o porte ser fiel; correção em PR separado.
* A busca de província usa ``like``, que é sensível a maiúsculas, então
  nomes acentuados do padrón não casam com ``res.country.state``.
* ``street`` e ``city`` recebem ``.capitalize()``, que rebaixa o resto do
  texto ("AV SIEMPRE VIVA" vira "Av siempre viva").
