const test = require('node:test');
const assert = require('node:assert/strict');
const radio = require('../static/crypto.js');

test('Unicode message round trip and independent random nonces', async () => {
  const key=radio.generateKey(), text='Station 3 → ready 📻';
  const first=await radio.encrypt(text,key), second=await radio.encrypt(text,key);
  assert.equal(await radio.decrypt(first,key),text);
  assert.notEqual(first.nonce,second.nonce);
  assert.notEqual(first.ciphertext,second.ciphertext);
  assert.equal(Object.hasOwn(first,'key'),false);
});
test('Wrong key, altered ciphertext, altered nonce and version are rejected',async()=>{
  const key=radio.generateKey(), envelope=await radio.encrypt('Test message',key);
  await assert.rejects(radio.decrypt(envelope,radio.generateKey()),/Verification failed/);
  for(const field of ['nonce','ciphertext']){
    const bytes=Buffer.from(envelope[field],'base64');bytes[0]^=1;
    await assert.rejects(radio.decrypt({...envelope,[field]:bytes.toString('base64')},key),/Verification failed/);
  }
  await assert.rejects(radio.decrypt({...envelope,version:2},key),/Unsupported/);
});
test('Reject malformed keys, envelopes and oversized messages',async()=>{
  await assert.rejects(radio.encrypt('text','AAAA'),/32-byte/);
  await assert.rejects(radio.encrypt('a'.repeat(32001),radio.generateKey()),/32,000/);
  await assert.rejects(radio.decrypt({version:1,algorithm:'AES-256-GCM',nonce:'AA==',ciphertext:'AA=='},radio.generateKey()),/length/);
});
