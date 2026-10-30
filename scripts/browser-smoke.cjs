// Optional live smoke test. Requires Playwright and an installed Chromium.
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.APP_URL||'http://127.0.0.1:8000';
 for(const width of [390,1280]){
  await page.setViewportSize({width,height:900});
  const response=await page.goto(base+'/');
  if(response.status()!==200)throw Error('Home status '+response.status());
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow at '+width);
  if(await page.locator('h1').innerText()!=='Find Your People.\nGrow in Faith.')throw Error('Missing home heading');
  console.log('Home and layout passed at '+width+'px');
 }
 const username='smoke-'+Date.now();
 await page.goto(base+'/register/');
 for(const [field,value] of Object.entries({username,full_name:'Browser verification',email:username+'@example.invalid',password1:'Browser-secure-test-password-71',password2:'Browser-secure-test-password-71'}))await page.locator('#id_'+field).fill(value);
 await page.locator('#id_adult').check();
 await Promise.all([page.waitForURL('**/profile/'),page.locator('button[type=submit]').click()]);
 await page.locator('#id_display_name').fill('Browser participant');await page.locator('#id_gender').selectOption('men');await page.locator('#id_timezone').selectOption('America/Edmonton');
 await Promise.all([page.waitForURL(base+'/'),page.locator('button[type=submit]').click()]);
 console.log('Account registration and profile persistence passed');
 await page.goto(base+'/start/');
 await page.locator('#id_name').fill('Browser smoke band');await page.locator('#id_day').selectOption('2');await page.locator('#id_time').fill('19:00');await page.locator('#id_description').fill('Temporary browser verification band.');
 await Promise.all([page.waitForURL(/\/bands\/\d+\/$/),page.locator('button[type=submit]').click()]);
 await page.getByText('Your workspace opens when the band has three approved members and an active lifecycle.').waitFor();
 console.log('Band creation and forming workspace lock passed');
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Directory overflow');
 await page.screenshot({path:'/tmp/discipleship-mobile.png',fullPage:true});
 // Delete only the account created by this run, including its otherwise empty band.
 await page.goto(base+'/account/delete/');await page.locator('input[name=password]').fill('Browser-secure-test-password-71');
 await Promise.all([page.waitForURL(base+'/'),page.getByRole('button',{name:'Delete my account permanently'}).click()]);
 if(errors.length)throw Error(errors.join(';'));
 console.log('Account deletion passed; temporary browser data removed');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
