/* Actual product API/UI, local only; no external navigation or target-user claims. */
const {chromium}=require('/Users/kyle/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.VIP_TEST_BASE||'http://127.0.0.1:8766';
const evidence=path.join(root,'local-data/verification');fs.mkdirSync(evidence,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const context=await browser.newContext({viewport:{width:1440,height:900}});const page=await context.newPage();page.setDefaultTimeout(8000);
 const errors=[],results=[];page.on('pageerror',e=>errors.push(e.message));
 await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
 async function check(id,fn){try{await fn();results.push({id,status:'passed'})}catch(e){results.push({id,status:'failed',error:e.message});throw e}}
 async function nav(name){await page.getByRole('button',{name,exact:true}).click();await page.getByRole('status').filter({hasText:'正在读取或保存'}).waitFor({state:'hidden'});}
 async function role(login){const box=page.locator('details.identity');if(!await box.evaluate(e=>e.open))await box.locator('summary').click();await page.getByLabel('身份',{exact:true}).selectOption(login);await page.getByRole('button',{name:'切换身份',exact:true}).click();await page.getByRole('status').filter({hasText:'正在读取或保存'}).waitFor({state:'hidden'});}
 try{
 await page.goto(base);await page.getByRole('button',{name:'阅读摘要与来源'}).first().waitFor();
 await check('F05-reading-real-profile',async()=>{
  const item=page.locator('article').filter({hasText:'比亚迪股份有限公司｜真实公司资料'});await item.getByRole('button',{name:'阅读摘要与来源'}).click();
  await page.locator('.body-text').waitFor();assert((await page.locator('.body-text').innerText()).length>1000);
  assert((await page.locator('main').innerText()).includes('CC-BY-SA-4.0'));await page.getByRole('button',{name:'返回资料列表'}).click();
 });
 await check('F05-company-A-H-score-and-watch',async()=>{
  await nav('公司研究');const company=page.locator('article').filter({has:page.getByRole('heading',{name:'合成甲制造',exact:true})});
  assert((await company.innerText()).includes('PE 12.0'));assert((await company.innerText()).includes('PE 14.5'));
  await company.getByRole('button',{name:'关注 600001.SH',exact:true}).click();await page.getByRole('status').filter({hasText:'已加入对应证券自选'}).waitFor();
 });
 await check('F05-human-impact-override',async()=>{
  await nav('判断与覆盖');const card=page.locator('article').filter({has:page.getByLabel('新影响',{exact:true})}).first();
  await card.getByLabel('新影响',{exact:true}).fill('-0.2');await card.getByRole('button',{name:'保存人工覆盖',exact:true}).click();
  await page.getByRole('status').filter({hasText:'本次修改已生效'}).waitFor();await card.getByText('当前有效值 -0.2',{exact:false}).waitFor();
 });
 await check('F05-rubric-grade-override',async()=>{
  const card=page.locator('article').filter({has:page.getByLabel('新档位',{exact:true})}).first();await card.getByLabel('新档位',{exact:true}).fill('1');
  await card.getByRole('button',{name:'保存人工覆盖',exact:true}).click();await page.getByRole('status').filter({hasText:'本次修改已生效'}).waitFor();
  await card.getByText('当前有效值 1',{exact:false}).waitFor();
 });
 await check('F05-notes-and-watchlist',async()=>{
  await nav('我的研究');assert((await page.locator('main').innerText()).includes('600001.SH'));
  await page.getByLabel('笔记内容',{exact:true}).fill('自动化验收：A/H独立估值，原文与判断分开。');await page.getByRole('button',{name:'保存笔记',exact:true}).click();
  await page.getByRole('status').filter({hasText:'笔记已保存'}).waitFor();assert((await page.locator('main').innerText()).includes('自动化验收：A/H独立估值'));
 });
 await check('F05-strategy-preview-publish',async()=>{
  await role('strat@demo');await nav('策略与变化');await page.getByLabel('经营分门槛',{exact:true}).fill('75');await page.getByRole('button',{name:'模拟草稿',exact:true}).click();
  await page.getByRole('heading',{name:'本次模拟',exact:true}).waitFor();await page.getByRole('button',{name:'发布新版本',exact:true}).click();
  await page.getByRole('status').filter({hasText:'新版本已发布'}).waitFor();assert((await page.locator('main').innerText()).includes('入选经营分门槛 75'));
 });
 await check('F05-template-preview-publish',async()=>{
  await nav('公司研究');const company=page.locator('article').filter({has:page.getByRole('heading',{name:'合成甲制造',exact:true})});
  await company.getByText('进阶：查看与维护评分模板',{exact:true}).click();await company.getByRole('button',{name:'预览模板差异',exact:true}).click();
  await company.getByRole('button',{name:'发布模板',exact:true}).waitFor();await company.getByRole('button',{name:'发布模板',exact:true}).click();
  await page.getByRole('status').filter({hasText:'新模板已发布'}).waitFor();
 });
 await check('F05-viewer-permission',async()=>{await role('viewer@demo');await nav('判断与覆盖');assert.equal(await page.getByRole('button',{name:'保存人工覆盖',exact:true}).count(),0);await nav('策略与变化');assert.equal(await page.getByRole('button',{name:'发布新版本',exact:true}).count(),0)});
 await check('F05-viewports-keyboard',async()=>{
  await nav('公司研究');await page.locator('details.identity').evaluate(e=>e.open=false);for(const [width,height]of [[1440,900],[1280,800],[390,844],[430,932]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
   assert.equal(await page.locator('header').count(),1);
   await page.evaluate(()=>scrollTo(0,0));
   await page.screenshot({path:path.join(evidence,`product-${width}.png`),fullPage:false});
  }
  await page.getByRole('button',{name:'新闻与资料',exact:true}).focus();await page.keyboard.press('Enter');await page.getByRole('button',{name:'阅读摘要与来源'}).first().waitFor();
  assert.equal(await page.evaluate(()=>document.activeElement.tagName),'BUTTON');
 });
 assert.deepEqual(errors,[]);
 }catch(e){console.error(e.message);process.exitCode=1}
 finally{fs.writeFileSync(path.join(evidence,'browser-results.json'),JSON.stringify({base,executed_at:new Date().toISOString(),target_user_test:false,results,page_errors:errors},null,2));console.log(JSON.stringify({results,page_errors:errors}));await browser.close()}
})();
