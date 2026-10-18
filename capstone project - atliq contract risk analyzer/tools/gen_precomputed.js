// Regenerates public/data/precomputed.json (the stored results for the built-in samples).
// Run it after any change to the rules, prompts or models that would change a sample's result.
// 1. Start the app with real models:  RATE_LIMIT_PER_5MIN=5000 python dev_server.py   (open http://localhost:8765/, clear site data)
// 2. Start a receiver that saves the POST body to public/data/precomputed.json (a few lines of Python http.server with CORS on port 8766).
// 3. Paste this whole file into the browser console. It runs every sample through the real screens (about 10 minutes), then posts the cache.
// Only complete reviews are cached by the app, so a sample that ends partial is missing from the output: run again.
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (const s of SAMPLES.filter(x => !x.kind)) {
    go('#/new'); await sleep(400); await pickSample(s.file); await startReview();
    for (let k = 0; k < 60 && !document.getElementById('f_cp'); k++) await sleep(500);
    document.querySelector('input[name=out][value=no]').checked = true;
    await runReview();
  }
  for (const s of SAMPLES.filter(x => x.kind === 'signed')) {            // signed contracts: extraction only (import flow)
    const ta = document.createElement('textarea'); ta.value = await (await fetch(s.file)).text();
    const text = ta.value.trim(), key = 'ex' + await hash(text);
    if (!S.cache[key]) { S.cache[key] = await api({ action: 'extract', text }, 3); save(); }
  }
  const out = {};
  for (const k of Object.keys(S.cache)) {
    if (k.startsWith('ex')) { const { details, clauses, quality } = S.cache[k]; out[k] = { details, clauses, quality }; }
    else if (k.startsWith('rv')) out[k] = S.cache[k];
  }
  await fetch('http://localhost:8766/save', { method: 'POST', body: JSON.stringify(out) });
  console.log('saved', Object.keys(out).length, 'entries');
})();
