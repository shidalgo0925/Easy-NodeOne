/* Presentación de números/moneda según window.EN1_REGIONAL (org). No cambia valores. */
(function (w) {
  const DEF = {
    number_format: '1,234.56',
    money_decimals: 2,
    qty_decimals: 2,
    currency_symbol: '$',
    symbol_position: 'before',
  };

  function cfg() {
    const src = w.EN1_REGIONAL && typeof w.EN1_REGIONAL === 'object' ? w.EN1_REGIONAL : {};
    return Object.assign({}, DEF, src);
  }

  function formatNumber(n, decimals) {
    const c = cfg();
    let d = decimals != null ? Number(decimals) : Number(c.money_decimals);
    if (!Number.isFinite(d) || d < 0) d = 2;
    d = Math.min(6, Math.floor(d));
    const x = Number(n);
    const v = Number.isFinite(x) ? x : 0;
    const neg = v < 0;
    const parts = Math.abs(v).toFixed(d).split('.');
    let ip = parts[0];
    const fp = parts[1] || '';
    const nf = String(c.number_format || '1,234.56');
    const tSep = nf === '1.234,56' ? '.' : ',';
    const dSep = nf === '1.234,56' ? ',' : '.';
    ip = ip.replace(/\B(?=(\d{3})+(?!\d))/g, tSep);
    const body = d ? ip + dSep + fp : ip;
    return (neg ? '-' : '') + body;
  }

  function money(n) {
    const c = cfg();
    const num = formatNumber(n, c.money_decimals);
    const sy = String(c.currency_symbol || '$');
    if (String(c.symbol_position || 'before') === 'after') return num + ' ' + sy;
    return sy + ' ' + num;
  }

  function qty(n) {
    return formatNumber(n, cfg().qty_decimals);
  }

  w.EN1Format = {
    cfg: cfg,
    number: formatNumber,
    money: money,
    qty: qty,
  };
})(window);
