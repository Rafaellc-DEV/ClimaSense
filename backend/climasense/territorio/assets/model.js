/* Pure data operations shared by the browser and focused tests. */
(function (root) {
  const colors = ['#e2edba', '#b5d48a', '#7caf68', '#448450', '#205c3b'];
  const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  function makeScale(values) {
    const numbers = values.filter(Number.isFinite);
    if (!numbers.length) return {min: 0, max: 0, bins: []};
    const min = Math.min(...numbers), max = Math.max(...numbers);
    const count = min === max ? 1 : colors.length;
    return {min, max, bins: Array.from({length: count}, (_, i) => ({
      low: min + (max - min) * i / count,
      high: min + (max - min) * (i + 1) / count,
      color: colors[i]
    }))};
  }
  function classIndex(value, scale) {
    if (!Number.isFinite(value) || !scale.bins.length) return -1;
    if (scale.min === scale.max) return 0;
    // Use the same exact bounds displayed by the legend, avoiding float division near edges.
    const index = scale.bins.findIndex((bin, i) => value < bin.high || i === scale.bins.length - 1);
    return Math.max(0, index);
  }
  function matches(properties, query) {
    const needle = normalize(query);
    return [properties.nome_distrito, ...properties.bairros].some(value => normalize(value).includes(needle));
  }
  function csvCell(value) {
    let text = String(value);
    if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  const api = {colors, makeScale, classIndex, matches, csvCell};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AtlasModel = api;
})(typeof window === 'undefined' ? globalThis : window);
