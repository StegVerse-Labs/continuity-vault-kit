// Node test for skap/loader/kv-skap-loader.html.
// Extracts the single inline <script>, evaluates it in a vm sandbox with stubs (no DOM,
// no network), and checks it against the shared Python vectors and the pinned TVC
// POLICY_ADMISSION vectors. All key material here is published TEST VECTORS.
// Usage: node tests/loader/kv_skap_loader.test.mjs   (exit 0 = all passed)
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import assert from "node:assert/strict";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const read = (p) => readFileSync(path.join(ROOT, p));
const HTML = read("skap/loader/kv-skap-loader.html").toString("utf8");
const ENV_VECTORS = JSON.parse(read("fixtures/skap/portable-envelope-v2.vectors.json"));
const TVC_VECTORS = JSON.parse(read("fixtures/tvc/test-lane-provider-use.v1.vectors.json"));
const TVC_POLICY = JSON.parse(read("fixtures/tvc/test-lane-provider-use.v1.json"));
const PINNED = JSON.parse(read("fixtures/tvc/PINNED.json"));

if (!globalThis.crypto || !globalThis.crypto.subtle) {
  console.log("SKIP: globalThis.crypto.subtle unavailable in this node");
  process.exit(77);
}

const scripts = [...HTML.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)];
const SCRIPT = scripts.length === 1 ? scripts[0][2] : null;

let passed = 0;
const failures = [];
async function check(name, fn) {
  try { await fn(); passed += 1; }
  catch (e) { failures.push(`${name}: ${e && e.message ? e.message : e}`); }
}

function loadSandbox() {
  const context = vm.createContext({ crypto: globalThis.crypto, setTimeout, Uint8Array, ArrayBuffer });
  vm.runInContext(SCRIPT, context, { filename: "kv-skap-loader.inline.js" });
  return context.KVSKAP;
}
const hex = (s) => new Uint8Array(Buffer.from(s, "hex"));
const plain = (o) => JSON.parse(JSON.stringify(o));
async function expectCode(promiseOrFn, code) {
  let err = null;
  try { await (typeof promiseOrFn === "function" ? promiseOrFn() : promiseOrFn); } catch (e) { err = e; }
  assert.ok(err, `expected error ${code}, got success`);
  assert.equal(err.code, code, `expected ${code}, got ${err.code} (${err.message})`);
}

// ---------------- (d) structure and CSP ----------------
await check("exactly one inline script, no src", () => {
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0][1].trim(), "");
});
await check("CSP meta present and strict", () => {
  const m = HTML.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)">/);
  assert.ok(m, "CSP meta missing");
  const directives = Object.fromEntries(m[1].split(";").map((d) => d.trim().split(/\s+/)).map(([k, ...v]) => [k, v]));
  assert.deepEqual(directives["default-src"], ["'none'"]);
  assert.deepEqual(directives["connect-src"].slice().sort(), ["https://api.anthropic.com", "https://api.openai.com"]);
  const scriptHash = "'sha256-" + createHash("sha256").update(SCRIPT, "utf8").digest("base64") + "'";
  assert.deepEqual(directives["script-src"], [scriptHash], "script-src must be exactly the inline script hash");
  const style = HTML.match(/<style>([\s\S]*?)<\/style>/)[1];
  const styleHash = "'sha256-" + createHash("sha256").update(style, "utf8").digest("base64") + "'";
  assert.deepEqual(directives["style-src"], [styleHash]);
  for (const d of ["base-uri", "form-action", "object-src", "frame-src", "img-src"]) assert.deepEqual(directives[d], ["'none'"], d);
  assert.ok(HTML.indexOf("Content-Security-Policy") < HTML.indexOf("<script"), "CSP must precede the script");
});
await check("file is ASCII", () => { assert.ok(/^[\x00-\x7f]*$/.test(HTML)); });

// ---------------- (c) forbidden constructs ----------------
await check("no forbidden constructs", () => {
  const forbidden = [
    [/\beval\s*\(/, "eval("], [/\bFunction\s*\(/, "Function("], [/\bimport\s*\(/, "import("], [/^\s*import\s/m, "static import"],
    [/<script[^>]*\bsrc\s*=/i, "script src="], [/\bsrc\s*=\s*["']?(https?:|\/\/|data:)/i, "external src="],
    [/<link\b/i, "<link>"], [/<iframe\b/i, "<iframe>"], [/\bon[a-z]+\s*=\s*["']/i, "inline event handler"],
    [/\bstyle\s*=\s*["']/i, "inline style attribute"],
    [/localStorage|sessionStorage|indexedDB|document\.cookie|caches\./, "browser storage"],
    [/\bconsole\./, "console logging"], [/\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|sendBeacon/, "other network API"],
    [/\bnew\s+Worker\b|importScripts/, "workers"], [/\binnerHTML\b|outerHTML|insertAdjacentHTML|document\.write/, "HTML injection sink"],
    [/setTimeout\s*\(\s*["'`]/, "string setTimeout"],
  ];
  for (const [re, label] of forbidden) assert.ok(!re.test(HTML), `forbidden construct present: ${label}`);
  const urls = HTML.match(/https?:\/\/[^\s"'<>);]+/g) || [];
  const allowed = new Set(["https://api.openai.com", "https://api.anthropic.com", "https://api.openai.com/v1/responses", "https://api.anthropic.com/v1/messages"]);
  for (const u of urls) assert.ok(allowed.has(u), `unexpected URL ${u}`);
  assert.ok(!/\bfetch\s*\(/.test(SCRIPT.replace(/globalThis\.fetch\s*\(|deps\.fetch\s*\(/g, "")), "only injected/global fetch call sites are allowed");
});

const K = loadSandbox();
await check("sandbox exposes KVSKAP", () => { assert.equal(typeof K.wrapRootKey, "function"); });

// ---------------- (a) envelope + crypto_boundary vectors ----------------
await check("canonical JSON vectors", async () => {
  for (const c of ENV_VECTORS.canonical_json) {
    const input = vm.runInNewContext("(" + JSON.stringify(c.input) + ")");
    if (c.expected_error) {
      await expectCode(() => K.canonicalString(c.input), c.expected_error);
    } else {
      assert.equal(K.canonicalString(c.input), c.expected, c.name);
      assert.equal(await K.digest(c.input), c.expected_sha256_digest, c.name);
      assert.equal(K.canonicalString(input), c.expected, c.name + " (cross-realm)");
    }
  }
});
await check("policy hash", async () => {
  assert.equal(await K.digest(ENV_VECTORS.policy_object), ENV_VECTORS.policy_hash);
  assert.equal(await K.digest(TVC_POLICY), K.EXPECTED_POLICY_HASH);
  assert.equal(K.canonicalString(plain(K.POLICY)), K.canonicalString(TVC_POLICY), "embedded policy must equal pinned TVC policy");
  assert.equal(PINNED.files[0].policy_hash, K.EXPECTED_POLICY_HASH);
});
await check("recovery secret parse vectors", async () => {
  for (const c of ENV_VECTORS.recovery_secret_parse) {
    if (c.expected_error) await expectCode(() => K.parseRecoverySecret(c.text), c.expected_error);
    else assert.equal(K.hexEncode(K.parseRecoverySecret(c.text)), c.expected_hex, c.name);
  }
});
await check("root_key_id vectors", async () => {
  for (const c of ENV_VECTORS.root_key_id) assert.equal(await K.rootKeyId(hex(c.root_key_hex)), c.expected_root_key_id);
});
await check("envelope wrap reproduces Python vector byte-identically", async () => {
  for (const c of ENV_VECTORS.envelope_wrap) {
    assert.equal(c.iterations, 600000);
    assert.equal(K.formatRecoverySecret(hex(c.recovery_secret_hex)), c.recovery_secret_text);
    const env = await K.wrapRootKey(hex(c.root_key_hex), hex(c.recovery_secret_hex), c.kv_identity, c.policy_hash, c.iterations,
      { testVectorSalt: hex(c.salt_hex), testVectorNonce: hex(c.nonce_hex) });
    assert.equal(K.canonicalString(env), K.canonicalString(c.expected_envelope));
    assert.equal(await K.digest(env), c.expected_envelope_digest);
    const aad = K.envelopeAad(env.kv_identity, env.root_key_id, env.kdf, env.policy_hash);
    assert.equal(Buffer.from(aad).toString("ascii"), c.expected_aad_ascii);
  }
});
await check("envelope unwrap of Python vector", async () => {
  const c = ENV_VECTORS.envelope_wrap[0];
  let seen = null, held = null;
  await K.unwrapRootKeyTransiently(c.expected_envelope, K.parseRecoverySecret(c.recovery_secret_text), (key) => { seen = K.hexEncode(key); held = key; return true; }, { kvIdentity: c.kv_identity, policyHash: c.policy_hash });
  assert.equal(seen, c.root_key_hex);
  assert.ok(held.every((b) => b === 0), "root key buffer must be wiped after the callback");
});
await check("envelope wrap negatives", async () => {
  for (const c of ENV_VECTORS.envelope_wrap_negative) {
    await expectCode(K.wrapRootKey(hex(c.root_key_hex), hex(c.recovery_secret_hex), c.kv_identity, c.policy_hash, c.iterations,
      { testVectorSalt: hex(c.salt_hex), testVectorNonce: hex(c.nonce_hex) }), c.expected_error);
  }
});
await check("envelope unwrap negatives", async () => {
  for (const c of ENV_VECTORS.envelope_unwrap_negative) {
    let called = false;
    await expectCode(K.unwrapRootKeyTransiently(c.envelope, K.parseRecoverySecret(c.recovery_secret_text), () => { called = true; }), c.expected_error);
    assert.equal(called, false, c.name);
  }
});
await check("crypto_boundary-compatible seal reproduces Python vectors and opens", async () => {
  for (const c of ENV_VECTORS.sealed_objects) {
    const sealed = await K.sealObject(new Uint8Array(Buffer.from(c.plaintext_ascii, "ascii")), hex(c.root_key_hex), c.bindings,
      { testVectorSalt: hex(c.kdf_salt_hex), testVectorNonce: hex(c.nonce_hex) });
    assert.equal(K.canonicalString(sealed), K.canonicalString(c.expected_sealed), c.name);
    assert.equal(await K.sealedMaterialHash(sealed), c.expected_sealed_material_hash, c.name);
    let got = null;
    await K.openObjectTransiently(c.expected_sealed, hex(c.root_key_hex), c.bindings, (pt) => { got = Buffer.from(pt).toString("ascii"); });
    assert.equal(got, c.plaintext_ascii);
  }
});
await check("crypto_boundary-compatible open negatives", async () => {
  for (const c of ENV_VECTORS.sealed_open_negative) {
    await expectCode(K.openObjectTransiently(c.sealed, hex(c.root_key_hex), c.bindings, () => {}), c.expected_error);
  }
});
await check("module bindings match vector bindings", async () => {
  const [cred, anchor] = ENV_VECTORS.sealed_objects;
  const rkid = ENV_VECTORS.root_key_id[0].expected_root_key_id;
  assert.deepEqual(plain(K.providerCredentialBindings("anthropic", ENV_VECTORS.policy_hash, rkid, 1)), cred.bindings);
  assert.deepEqual(plain(K.bootstrapAnchorBindings(ENV_VECTORS.policy_hash, rkid)), anchor.bindings);
  const a = JSON.parse(anchor.plaintext_ascii);
  const rebuilt = K.buildBootstrapAnchor({ loader_sha256: a.loader_sha256, repository: a.loader_source.repository, commit: a.loader_source.commit, path: a.loader_source.path, policy_hash: a.policy_hash, kv_identity: a.kv_identity, genesis_manifest_digest: a.genesis_manifest_digest, predecessor_state: a.predecessor_state });
  assert.equal(Buffer.from(rebuilt).toString("ascii"), anchor.plaintext_ascii);
});

// ---------------- (b) POLICY_ADMISSION vectors ----------------
await check("TVC vector file digest matches PINNED.json", () => {
  const got = createHash("sha256").update(read("fixtures/tvc/test-lane-provider-use.v1.vectors.json")).digest("hex");
  assert.equal(got, PINNED.files[1].file_sha256);
  assert.equal(TVC_VECTORS.length, PINNED.files[1].vector_count);
  const pol = createHash("sha256").update(read("fixtures/tvc/test-lane-provider-use.v1.json")).digest("hex");
  assert.equal(pol, PINNED.files[0].file_sha256);
});
for (const v of TVC_VECTORS) {
  await check(`POLICY_ADMISSION vector ${v.name}`, async () => {
    const receipt = plain(await K.evaluatePolicyAdmission(v.request));
    assert.equal(receipt.receipt_sha256, v.expected_receipt.receipt_sha256);
    assert.equal(K.canonicalString(receipt), K.canonicalString(v.expected_receipt));
  });
}
await check("POLICY_ADMISSION covers ALLOW and all six predicates", () => {
  const seen = new Set(TVC_VECTORS.map((v) => v.expected_receipt.failed_predicate));
  for (const p of [null, "POLICY_ADMISSION_REQUEST_SCHEMA_VALID", "PROVIDER_CAPABILITY_ADMITTED", "LEASE_DURATION_WITHIN_POLICY", "REQUIRED_FALSE_FLAGS_FALSE", "SDK_MANIFEST_BINDING_EQUAL", "ATTEMPT_NOT_REPLAYED"]) assert.ok(seen.has(p), String(p));
});

// ---------------- GENESIS / ENROLL / USE orchestration (stubs only) ----------------
const RULE = "StegVerse-Labs/.github@" + "a".repeat(40) + ":resident-runtime/organization_manifest_ingress.py";
const NON_ALLOW_FIELDS = ["disposition", "evidence_refs", "failed_predicate", "failure_code", "next_attempt", "owning_existing_goal", "required_evidence_or_repair", "retry_entrypoint"];
function assertNonAllow(rec, code) {
  assert.deepEqual(Object.keys(rec).sort(), NON_ALLOW_FIELDS);
  assert.equal(rec.failure_code, code);
  assert.ok(Array.isArray(rec.evidence_refs) && rec.evidence_refs.length > 0);
  for (const f of NON_ALLOW_FIELDS) assert.ok(rec[f] !== undefined && rec[f] !== null && rec[f] !== "", f);
}
const genesisInput = (over) => Object.assign({ existing_text: "", owner_attests_absent: true, kv_identity: "kv://test/genesis", genesis_manifest_digest: "sha256:" + "1".repeat(64), org_receipt_id: "org-receipt-test-0001", org_receipt_sha256: "2".repeat(64), recomputation_rule_ref: RULE, loader_sha256: "3".repeat(64), loader_commit: "4".repeat(40), now_epoch_seconds: 1760000000 }, over || {});

await check("genesis denied on initialized KV", async () => {
  const r = await K.runGenesis(genesisInput({ existing_text: JSON.stringify(ENV_VECTORS.envelope_wrap[0].expected_envelope) }));
  assert.equal(r.ok, false); assertNonAllow(r.record, "KV_SKAP_TRUST_GENESIS_ON_INITIALIZED_KV"); assert.equal(r.record.disposition, "DENY");
});
await check("genesis fails closed when state is ambiguous", async () => {
  for (const over of [{ owner_attests_absent: false }, { existing_text: "{not json" }, { existing_text: "{\"schema\":\"other\"}" }]) {
    const r = await K.runGenesis(genesisInput(over));
    assert.equal(r.ok, false); assertNonAllow(r.record, "KV_SKAP_GENESIS_STATE_UNVERIFIED"); assert.equal(r.record.disposition, "FAIL_CLOSED");
  }
});
await check("genesis stage-2 inputs verified before any secret is generated", async () => {
  let calls = 0;
  const realGet = globalThis.crypto.getRandomValues.bind(globalThis.crypto);
  const ctx = vm.createContext({ crypto: { subtle: globalThis.crypto.subtle, getRandomValues: (b) => { calls += 1; return realGet(b); } }, setTimeout, Uint8Array, ArrayBuffer });
  vm.runInContext(SCRIPT, ctx);
  for (const over of [{ recomputation_rule_ref: "StegVerse-Labs/.github@main:resident-runtime/organization_manifest_ingress.py" }, { genesis_manifest_digest: "abc" }, { org_receipt_id: "" }, { loader_commit: "x" }]) {
    const r = await ctx.KVSKAP.runGenesis(genesisInput(over));
    assert.equal(r.ok, false); assertNonAllow(r.record, "KV_SKAP_GENESIS_ADMISSION_INPUT_INVALID");
  }
  assert.equal(calls, 0, "no randomness (secret generation) may happen before stage 2 passes");
});
let G = null;
await check("genesis produces envelope, sealed anchor and non-secret receipt", async () => {
  G = await K.runGenesis(genesisInput());
  assert.equal(G.ok, true);
  assert.match(G.recovery_secret_text, /^([A-Z2-7]{4}-){7}[A-Z2-7]{4}$/);
  assert.equal(G.envelope.kdf.iterations, 600000);
  assert.equal(G.anchor_sealed.purpose, "kv-skap-bootstrap-anchor");
  assert.equal(G.receipt.ledger_fence_satisfied, false);
  assert.equal(G.receipt.organization_admission_receipt.recomputation_rule_ref, RULE);
  const receiptText = JSON.stringify(G.receipt) + JSON.stringify(G.envelope) + JSON.stringify(G.anchor_sealed);
  const secretCompact = G.recovery_secret_text.replace(/-/g, "");
  assert.ok(!receiptText.includes(secretCompact) && !receiptText.includes(G.recovery_secret_text), "recovery secret must not appear in any download");
  let anchor = null;
  await K.unwrapRootKeyTransiently(G.envelope, K.parseRecoverySecret(G.recovery_secret_text), (rk) =>
    K.openObjectTransiently(G.anchor_sealed, rk, K.bootstrapAnchorBindings(G.envelope.policy_hash, G.envelope.root_key_id), (pt) => { anchor = JSON.parse(Buffer.from(pt).toString("ascii")); }));
  assert.equal(anchor.loader_sha256, "3".repeat(64));
  assert.equal(anchor.predecessor_state, "KV_SKAP_ROOT_ABSENT_OWNER_ATTESTED");
});
const TEST_KEY = "TEST-VECTOR-ONLY-NOT-A-PROVIDER-CREDENTIAL-LOADER";
let E = null;
await check("enroll seals provider credential without exposing it", async () => {
  E = await K.runEnroll({ envelope: G.envelope, recovery_secret_text: G.recovery_secret_text, provider: "anthropic", api_key: TEST_KEY, now_epoch_seconds: 1760000001 });
  assert.equal(E.sealed.purpose, "provider-credential");
  assert.equal(E.sealed.object_id, "skap://provider/anthropic/api-key");
  assert.ok(!JSON.stringify(E).includes(TEST_KEY));
  await expectCode(K.runEnroll({ envelope: G.envelope, recovery_secret_text: K.formatRecoverySecret(new Uint8Array(20)), provider: "anthropic", api_key: TEST_KEY }), "ENVELOPE_AUTH_FAILED");
});
const binding = TVC_VECTORS[0].request.sdk_manifest_binding;
const useInput = (over) => Object.assign({ manifest_digest: "sha256:" + "1".repeat(64), org_receipt_id: "org-receipt-test-0001", org_receipt_sha256: "2".repeat(64), recomputation_rule_ref: RULE, attempt_id: "attempt-loader-test-0001", requested_seconds: 120, sdk_manifest_binding: binding, lease_sdk_manifest_binding: plain(binding), consumed_attempt_ids: [], provider: "anthropic", model: "claude-opus-5-5", envelope: G.envelope, sealed: E.sealed, recovery_secret_text: G.recovery_secret_text }, over || {});
function stubFetch(record) {
  return async (url, init) => {
    record.calls.push({ url, headers: Object.assign({}, init.headers), body: init.body, method: init.method, credentials: init.credentials });
    return { status: 200, headers: { get: (h) => (h === "request-id" ? "req_test_0001" : null) }, arrayBuffer: async () => new TextEncoder().encode("{\"ok\":true}").buffer };
  };
}
let clockT = 1760000000000;
const now = () => (clockT += 5);
await check("USE: ALLOW makes exactly one bounded Anthropic request; receipt is non-secret", async () => {
  const rec = { calls: [] };
  const r = await K.runUseAttempt(useInput(), { fetch: stubFetch(rec), now });
  assert.equal(r.ok, true);
  assert.equal(rec.calls.length, 1);
  const c = rec.calls[0];
  assert.equal(c.url, "https://api.anthropic.com/v1/messages");
  assert.equal(c.method, "POST"); assert.equal(c.credentials, "omit");
  assert.equal(c.headers["x-api-key"], TEST_KEY);
  assert.equal(c.headers["anthropic-version"], "2023-06-01");
  assert.equal(c.headers["anthropic-dangerous-direct-browser-access"], "true");
  assert.ok(JSON.parse(c.body).max_tokens <= 64);
  const receipt = plain(r.receipt);
  assert.ok(!JSON.stringify(receipt).includes(TEST_KEY), "attempt receipt must never contain the key");
  assert.ok(!JSON.stringify(receipt).includes(G.recovery_secret_text.replace(/-/g, "")));
  assert.equal(receipt.provider_http_status, 200);
  assert.equal(receipt.provider_request_id, "req_test_0001");
  assert.equal(receipt.response_sha256, "sha256:" + createHash("sha256").update("{\"ok\":true}").digest("hex"));
  assert.equal(receipt.policy_admission_receipt.decision, "ALLOW_CAPABILITY_LEASE");
  assert.equal(receipt.credential_exported, false);
  const { receipt_sha256, ...rest } = receipt;
  assert.equal(await K.digest(rest), receipt_sha256);
});
await check("USE: OpenAI request uses Bearer auth on /v1/responses", async () => {
  const rec = { calls: [] };
  const sealedOpenAI = (await K.runEnroll({ envelope: G.envelope, recovery_secret_text: G.recovery_secret_text, provider: "openai", api_key: TEST_KEY, now_epoch_seconds: 1 })).sealed;
  const r = await K.runUseAttempt(useInput({ provider: "openai", model: "test-model", sealed: sealedOpenAI, attempt_id: "attempt-loader-test-0002" }), { fetch: stubFetch(rec), now });
  assert.equal(r.ok, true);
  assert.equal(rec.calls[0].url, "https://api.openai.com/v1/responses");
  assert.equal(rec.calls[0].headers.authorization, "Bearer " + TEST_KEY);
  assert.ok(!("x-api-key" in rec.calls[0].headers));
});
await check("USE: DENY (replay) makes no request and emits non-ALLOW record", async () => {
  const rec = { calls: [] };
  const r = await K.runUseAttempt(useInput({ consumed_attempt_ids: ["attempt-loader-test-0001"] }), { fetch: stubFetch(rec), now });
  assert.equal(r.ok, false); assert.equal(rec.calls.length, 0);
  assert.equal(r.admission.failed_predicate, "ATTEMPT_NOT_REPLAYED");
  assertNonAllow(r.record, "POLICY_ADMISSION_DENIED");
});
await check("USE: missing manifest/Organization receipt fields fail closed before admission", async () => {
  const rec = { calls: [] };
  for (const over of [{ manifest_digest: "" }, { org_receipt_id: "" }, { recomputation_rule_ref: "" }, { org_receipt_sha256: "nope" }]) {
    const r = await K.runUseAttempt(useInput(over), { fetch: stubFetch(rec), now });
    assert.equal(r.ok, false); assertNonAllow(r.record, "KV_SKAP_USE_ADMISSION_EVIDENCE_MISSING");
  }
  assert.equal(rec.calls.length, 0);
});
await check("USE: malformed SDK binding denied", async () => {
  const rec = { calls: [] };
  const bad = Object.assign(plain(binding), { route_id: "" });
  const r = await K.runUseAttempt(useInput({ sdk_manifest_binding: bad, lease_sdk_manifest_binding: plain(bad) }), { fetch: stubFetch(rec), now });
  assert.equal(r.admission.failed_predicate, "SDK_MANIFEST_BINDING_EQUAL"); assert.equal(rec.calls.length, 0);
});
await check("USE: wrong recovery secret makes no request", async () => {
  const rec = { calls: [] };
  await expectCode(K.runUseAttempt(useInput({ recovery_secret_text: K.formatRecoverySecret(new Uint8Array(20)) }), { fetch: stubFetch(rec), now }), "ENVELOPE_AUTH_FAILED");
  assert.equal(rec.calls.length, 0);
});

const total = passed + failures.length;
for (const f of failures) console.log("FAIL " + f);
console.log(`kv-skap-loader node tests: ${passed}/${total} passed`);
process.exit(failures.length ? 1 : 0);
