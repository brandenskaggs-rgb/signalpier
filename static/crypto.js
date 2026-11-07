/* Browser-native authenticated encryption; no custom cryptographic primitive. */
(function (root) {
  'use strict';
  const encoder = new TextEncoder();
  const aad = encoder.encode('field-radio-workbench:v1');
  const encode = bytes => btoa(String.fromCharCode(...bytes));
  function decode(text) {
    if (typeof text !== 'string' || text.length > 100000) throw new Error('Invalid Base64 value.');
    return Uint8Array.from(atob(text), char => char.charCodeAt(0));
  }
  async function keyFrom(text) {
    const bytes = decode(text.trim());
    if (bytes.length !== 32) throw new Error('Use a generated 32-byte key, encoded as Base64.');
    return crypto.subtle.importKey('raw', bytes, 'AES-GCM', false, ['encrypt', 'decrypt']);
  }
  const api = {
    generateKey() { return encode(crypto.getRandomValues(new Uint8Array(32))); },
    async encrypt(text, keyText) {
      const plain = encoder.encode(text);
      if (!plain.length || plain.length > 32000) throw new Error('Enter a message between 1 and 32,000 UTF-8 bytes.');
      const key = await keyFrom(keyText);
      const nonce = crypto.getRandomValues(new Uint8Array(12));
      const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce, additionalData: aad, tagLength: 128 }, key, plain);
      return { version: 1, algorithm: 'AES-256-GCM', nonce: encode(nonce), ciphertext: encode(new Uint8Array(encrypted)) };
    },
    async decrypt(envelope, keyText) {
      if (!envelope || envelope.version !== 1 || envelope.algorithm !== 'AES-256-GCM') throw new Error('Unsupported envelope version or algorithm.');
      const nonce = decode(envelope.nonce);
      const encrypted = decode(envelope.ciphertext);
      if (nonce.length !== 12 || encrypted.length < 16 || encrypted.length > 32016) throw new Error('Invalid envelope length.');
      const key = await keyFrom(keyText);
      try {
        const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce, additionalData: aad, tagLength: 128 }, key, encrypted);
        return new TextDecoder('utf-8', { fatal: true }).decode(plain);
      } catch { throw new Error('Verification failed: wrong key or altered envelope.'); }
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RadioCrypto = api;
})(globalThis);
