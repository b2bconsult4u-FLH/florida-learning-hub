// Runs in GitHub Actions. Credentials remain in environment variables and Worker secrets.
import {readFile, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
const names=['CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID','FLH_DISPATCH_TOKEN','HC_CLOCK_URL','HC_WATCHDOG_URL','NTFY_TOPIC','STATUS_TOKEN'];
const missing=names.filter(n=>!process.env[n]);
if(missing.length) throw new Error('Missing repository secrets: '+missing.join(', '));
const base=`https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}`;
async function api(path,method='GET',body){
 const r=await fetch(base+path,{method,headers:{Authorization:`Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000)});
 const d=await r.json(); if(!r.ok||!d.success) throw new Error(`Cloudflare ${method} ${path}: HTTP ${r.status}`);return d;
}
let ns; let page=1;
do{const d=await api(`/storage/kv/namespaces?page=${page}&per_page=100`);ns=d.result.find(x=>x.title==='flh-publication-state');if(ns||d.result.length<100)break;page++;}while(true);
if(!ns)ns=(await api('/storage/kv/namespaces','POST',{title:'flh-publication-state'})).result;
function run(args,cwd,input){const r=spawnSync('npx',['--no-install','wrangler',...args],{cwd,env:process.env,input,encoding:'utf8',stdio:input?['pipe','inherit','inherit']:'inherit'});if(r.status!==0)throw new Error('Wrangler operation failed');}
for(const [name,secrets] of [['clock',['GITHUB_TOKEN','HC_CLOCK_URL']],['watchdog',['GITHUB_TOKEN','HC_WATCHDOG_URL','NTFY_TOPIC','STATUS_TOKEN']]]){
 const cwd=`ops/cloudflare/${name}`;const path=cwd+'/wrangler.toml';
 const config=(await readFile(path,'utf8')).replace('REPLACE_WITH_KV_NAMESPACE_ID',ns.id);
 await writeFile(path,config);
 // Deploy without schedules first; enable cron only after all required secrets exist.
 await writeFile(path,config.replace(/crons = \[[^\n]+\]/,'crons = []'));
 run(['deploy'],cwd);
 const values=Object.fromEntries(secrets.map(n=>[n,n==='GITHUB_TOKEN'?process.env.FLH_DISPATCH_TOKEN:process.env[n]]));
 run(['secret','bulk'],cwd,JSON.stringify(values));
 await writeFile(path,config);run(['deploy'],cwd);
 const deployed=await api(`/workers/scripts/flh-publish-${name}/schedules`);
 console.log(`${name}: ${deployed.result.schedules?.length ?? deployed.result.length ?? 'configured'} schedule(s)`);
}
