(function (root) {
  'use strict';
  const intervals = [1, 3, 7, 14, 30, 60];
  function eligible(plant, mode) {
    return mode === 'image' ? Boolean(plant.image) : Boolean(plant.latin && plant.estonian);
  }
  function key(plant, mode) { return JSON.stringify([plant.id, mode]); }
  function schedule(previous, known, now) {
    const level = known ? Math.min((previous?.level || 0) + 1, intervals.length) : 0;
    return { level, due: now + (known ? intervals[level - 1] * 86400000 : 600000),
      updated: now, reviews: (previous?.reviews || 0) + 1 };
  }
  function select(plants, progress, mode, group, now, practice = false, random = Math.random) {
    return plants.filter(p => eligible(p, mode) && (!group || p.group === group))
      .map(p => ({ plant: p, state: progress[key(p, mode)], tie: random() }))
      .filter(p => practice || !p.state || p.state.due <= now)
      .sort((a, b) => Number(!a.state) - Number(!b.state) || a.tie - b.tie)
      .slice(0, 20).map(p => p.plant);
  }
  function validateBackup(value, validKeys) {
    if (!value || value.version !== 1 || !value.progress || typeof value.progress !== 'object' || Array.isArray(value.progress)) {
      throw new Error('See fail ei ole Aedniku taimenimede õpiedu varukoopia.');
    }
    const result = {};
    for (const [id, state] of Object.entries(value.progress)) {
      if (!validKeys.has(id)) continue;
      if (!state || !Number.isInteger(state.level) || state.level < 0 || state.level > intervals.length ||
          !Number.isFinite(state.due) || state.due < 0 || !Number.isFinite(state.updated) || state.updated < 0 ||
          !Number.isInteger(state.reviews) || state.reviews < 0) throw new Error('Varukoopia õpiedu andmed ei ole korrektsed.');
      result[id] = { level: state.level, due: state.due, updated: state.updated, reviews: state.reviews };
    }
    return result;
  }
  const api = { eligible, key, schedule, select, validateBackup };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Study = api;
})(typeof window !== 'undefined' ? window : globalThis);
