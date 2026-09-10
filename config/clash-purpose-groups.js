// Purpose groups v1.0.0 — derives exclusively from this subscription's current nodes.
// Never embeds credentials, fetches subscriptions or changes ports/mode/TUN.
function main(config) {
  if (!config || !Array.isArray(config.proxies)) return config;
  const jpName = '🇯🇵 日本｜日常高速';
  const usName = '🇺🇸 美国｜反重力候选';
  const metadata = /剩余流量|套餐到期|到期时间|官网|不可用请|公告|流量重置|traffic|expire/i;
  const legacy = ['🇯🇵 日本-故障转移','🇯🇵 日本-自动优选','🇯🇵 ChatGPT-Japan-Auto',jpName,usName];
  const proxies = config.proxies.filter(p=>p && p.name && !metadata.test(p.name));
  config.proxies = proxies;
  const names = proxies.map(p=>p.name);
  const jp = names.filter(n=>/日本|🇯🇵|Japan|Tokyo|Osaka|东京|大阪|\bJP\b/i.test(n));
  const us = names.filter(n=>/美国|美國|🇺🇸|United States|Los Angeles|洛杉矶|纽约|\bUS\b|\bUSA\b/i.test(n));
  const groups = (config['proxy-groups'] || []).filter(g=>!legacy.includes(g.name));
  const oldNames = groups.map(g=>g.name);
  const generated = [];
  const health = {url:'https://www.gstatic.com/generate_204',interval:180,timeout:8000,lazy:false};
  if (jp.length) {
    generated.push(Object.assign({name:jpName,type:'url-test',tolerance:80,proxies:jp},health));
    // Keep old rule/selection references valid without retaining old node definitions.
    for (const name of legacy.slice(0,3)) generated.push({name,type:'select',hidden:true,proxies:[jpName]});
  }
  if (us.length) generated.push(Object.assign({name:usName,type:'fallback',proxies:us},health));
  const allowed = names.concat(oldNames,generated.map(g=>g.name),['DIRECT','REJECT','REJECT-DROP','PASS','COMPATIBLE']);
  for (const g of groups) {
    if (Array.isArray(g.proxies)) {
      g.proxies = g.proxies.filter(n=>allowed.includes(n) && !metadata.test(n) && n!==g.name);
      if(g.type==='select') {
        g.proxies = g.proxies.filter(n=>!legacy.includes(n));
        if(us.length) g.proxies.unshift(usName);
        if(jp.length) g.proxies.unshift(jpName);
      }
      // An empty group must remain syntactically valid, but must never silently go DIRECT.
      if(!g.proxies.length && !(g.use || g['include-all'])) g.proxies=['REJECT'];
    }
    if(g.type==='fallback' || g.type==='url-test') Object.assign(g,health);
  }
  config['proxy-groups'] = generated.concat(groups);
  const direct = [
    'PROCESS-NAME,DY提取作品.exe,DIRECT','PROCESS-NAME,江湖工具箱.exe,DIRECT',
    'DOMAIN-KEYWORD,douyin,DIRECT','DOMAIN-SUFFIX,douyin.com,DIRECT',
    'DOMAIN-SUFFIX,douyincdn.com,DIRECT','DOMAIN-SUFFIX,amemv.com,DIRECT',
    'DOMAIN-SUFFIX,snssdk.com,DIRECT','DOMAIN-SUFFIX,bytedance.com,DIRECT',
    'DOMAIN-SUFFIX,pstatp.com,DIRECT','DOMAIN-SUFFIX,volces.com,DIRECT',
    'DOMAIN-SUFFIX,zijieapi.com,DIRECT','DOMAIN-SUFFIX,feishu.cn,DIRECT'
  ];
  const chat = jp.length ? [
    'PROCESS-NAME,ChatGPT.exe,🇯🇵 ChatGPT-Japan-Auto','PROCESS-NAME,codex.exe,🇯🇵 ChatGPT-Japan-Auto',
    'DOMAIN-SUFFIX,chatgpt.com,🇯🇵 ChatGPT-Japan-Auto','DOMAIN-SUFFIX,openai.com,🇯🇵 ChatGPT-Japan-Auto',
    'DOMAIN-SUFFIX,oaistatic.com,🇯🇵 ChatGPT-Japan-Auto','DOMAIN-SUFFIX,oaiusercontent.com,🇯🇵 ChatGPT-Japan-Auto'
  ] : [];
  const prepend=direct.concat(chat);
  config.rules=prepend.concat((config.rules||[]).filter(r=>!prepend.some(n=>r.split(',').slice(0,2).join(',')===n.split(',').slice(0,2).join(','))));
  return config;
}
