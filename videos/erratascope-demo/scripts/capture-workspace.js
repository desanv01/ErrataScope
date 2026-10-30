async (page) => {
  await page.waitForTimeout(2200);
  await page.getByRole('region', {name:'Provenance',exact:true}).hover();
  await page.waitForTimeout(4500);
  await page.getByRole('button',{name:'2.2.5 Incorrect DBGMCU_IDCODE register value',exact:true}).click();
  await page.waitForTimeout(4500);
  await page.getByRole('button',{name:'2.2.18 Incorrect reset behavior when using NRST pin',exact:true}).click();
  await page.waitForTimeout(5000);
}
