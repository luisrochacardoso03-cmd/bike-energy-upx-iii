const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/app.js','utf8');
const start = source.indexOf('async function mutate(');
const end = source.indexOf('\nfunction leaveApp',start);
const keys=[];
let refreshCount=0, serial=0;
const context = {pendingKeys:new Map(), crypto:{randomUUID:()=>`operation-${++serial}`},
  api:async(_,data)=>{keys.push(data.request_id);return{id:1};},
  refresh:async()=>{if(++refreshCount===1)throw new Error('offline');}, toast:()=>{}};
vm.createContext(context);
vm.runInContext(source.slice(start,end),context);
(async()=>{
  await assert.rejects(()=>context.mutate('/api/redemptions',{reward_id:1},'ok',true),/offline/);
  await context.mutate('/api/redemptions',{reward_id:1},'ok',true);
  assert.equal(keys[0],keys[1],'Retry precisa usar a mesma chave após POST confirmado e atualização com erro');
  console.log('PASS: retry mantém idempotência após falha na consulta');
})().catch(error=>{console.error(error);process.exitCode=1;});
